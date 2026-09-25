#!/usr/bin/env python3
"""Approval-bound AUDIT update; dry-run unless --execute is explicit."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import socket
import urllib.error
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


NEW_SCRIPTS = ROOT / "skills" / "wp-publish-new" / "scripts"
BUNDLE = load_module("wp_audit_bundle", NEW_SCRIPTS / "wp_bundle.py")
NEW = load_module("wp_audit_media", NEW_SCRIPTS / "wp_push_draft.py")
GATE = load_module("wp_audit_html_gate", NEW_SCRIPTS / "wp_gate.py")
WP = load_module("wp_audit_rest", Path(__file__).with_name("wp_lib.py"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def verify_snapshot(post: dict, request: dict) -> None:
    if int(post.get("id", -1)) != int(request["post_id"]):
        raise ValueError("ROUTE-CONFLICT: WordPress post ID differs")
    raw = (post.get("content") or {}).get("raw")
    if not isinstance(raw, str):
        raise ValueError("VERIFY-DIFF: WordPress content.raw is unavailable")
    if (
        post.get("modified") != request.get("wp_modified_at_fetch")
        or sha256_text(raw) != request.get("wp_raw_sha256_at_fetch")
        or post.get("status") != request.get("wp_status_at_fetch")
    ):
        raise ValueError("SOURCE-STALE: WordPress post changed after AUDIT snapshot")
    target = request.get("target_url")
    if target and str(post.get("link", "")).rstrip("/") != str(target).rstrip("/"):
        raise ValueError("ROUTE-CONFLICT: WordPress permalink differs from AUDIT target")


def load_approved_bundle(bundle: Path, approval_hash: str | None) -> tuple[dict, dict, str]:
    BUNDLE.verify_source(bundle)
    BUNDLE.verify_audit_gate(bundle)
    request = NEW.read_json(bundle / "publish-request.json")
    approval = NEW.read_json(bundle / "approval.json")
    current_hash = BUNDLE.bundle_hash(bundle)
    if approval.get("approval_hash") != current_hash or approval.get("files") != list(BUNDLE.approval_files(bundle)):
        raise ValueError("SOURCE-STALE: AUDIT approval no longer matches bundle")
    if approval_hash is not None and approval_hash != current_hash:
        raise ValueError("SOURCE-STALE: --approval-hash mismatch")
    if request.get("task_type") != "AUDIT" or request.get("update_mode") not in {"MINIMAL_DIFF", "REBUILD"}:
        raise ValueError("ROUTE-CONFLICT: explicit AUDIT update_mode is required")
    return request, NEW.read_json(bundle / "image-manifest.json"), current_hash


def build_update_payload(request: dict, final_html: str, media: dict, profile: dict) -> dict:
    payload = {"content": final_html, "title": request["title"]}
    meta = dict(request.get("meta") or {})
    adapter = str(profile.get("seo_meta_adapter") or "").lower()
    if request.get("seo_title") or request.get("meta_description"):
        title = request.get("seo_title") or request["title"]
        if adapter == "yoast":
            meta["_yoast_wpseo_title"] = title
            if request.get("meta_description"):
                meta["_yoast_wpseo_metadesc"] = request["meta_description"]
        elif adapter == "rankmath":
            meta["rank_math_title"] = title
            if request.get("meta_description"):
                meta["rank_math_description"] = request["meta_description"]
        else:
            raise ValueError("BRAND-MISSING: AUDIT SEO meta adapter must be yoast or rankmath")
    if meta:
        payload["meta"] = meta
    featured = request.get("featured_asset_id")
    if featured:
        if str(featured) not in media:
            raise ValueError(f"IMG-MISSING: featured asset {featured}")
        payload["featured_media"] = int(media[str(featured)]["media_id"])
    return payload


def run(args: argparse.Namespace) -> int:
    bundle = Path(args.bundle).resolve()
    request, manifest, current_hash = load_approved_bundle(bundle, args.approval_hash if args.execute else None)
    if args.site_key != request.get("site_key"):
        raise ValueError("ROUTE-CONFLICT: site key differs from approved AUDIT request")
    uploads = [item for item in manifest.get("images", []) if item.get("action") == "prepare-upload"]
    for item in uploads:
        output = Path(str(item.get("output", "")))
        if not output.is_file() or not item.get("output_sha256") or BUNDLE.sha256_file(output) != item["output_sha256"]:
            raise ValueError(f"SOURCE-STALE: approved image bytes changed for {item.get('asset_id')}")
    if not args.execute:
        print(json.dumps({
            "mode": "dry-run", "task_type": "AUDIT", "update_mode": request["update_mode"],
            "post_id": request["post_id"], "approval_hash": current_hash,
            "uploads": [item.get("filename") for item in uploads],
        }, ensure_ascii=False, indent=2))
        return 0
    if args.approval_hash != current_hash:
        raise ValueError("SOURCE-STALE: --approval-hash is required for a write")
    if not args.profile:
        raise ValueError("BRAND-MISSING: --profile")
    context = NEW.read_json(Path(args.profile))
    profile = NEW.select_write_profile(context, request.get("content_type", "blog"), pilot=False)
    endpoint = str(profile.get("endpoint") or "posts").strip("/")
    state_path = bundle / "run-state.json"
    state = NEW.read_json(state_path)
    job_id = request.get("job_id") or (f"sheet:{request['row_id']}" if request.get("row_id") else None)
    state_job_id = state.get("job_id") or (f"sheet:{state['row_id']}" if state.get("row_id") else None)
    if state.get("run_id") != request.get("run_id") or state_job_id != job_id:
        raise ValueError("RESUME-CONFLICT: run-state belongs to another AUDIT job")
    if state.get("state") not in {"APPROVED", "MEDIA_READY"}:
        raise ValueError("RESUME-CONFLICT: AUDIT run-state is not approved for a write")
    base, user, password = WP.load_credential(args.site_key)
    path = f"{endpoint}/{int(request['post_id'])}?context=edit"
    status, current = WP.wp_get(base, user, password, path)
    if status != 200:
        raise RuntimeError(f"WP prewrite fetch HTTP {status}")
    verify_snapshot(current, request)

    media = dict(state.get("media") or {})
    for item in uploads:
        asset_id = str(item["asset_id"])
        if asset_id not in media:
            media[asset_id] = NEW.upload_media(base, user, password, item)
            state["media"] = media
            NEW.atomic_json(state_path, state)
    for item in manifest.get("images", []):
        if item.get("action") == "preserve-existing" and item.get("media_id"):
            media[str(item["asset_id"])] = {
                "media_id": int(item["media_id"]), "source_url": item["existing_url"],
            }
    prepared = (bundle / "content.prepared.html").read_text(encoding="utf-8")
    final_html = NEW.replace_asset_tokens(prepared, manifest, media)
    (bundle / "content.final.html").write_text(final_html, encoding="utf-8")
    GATE.validate(bundle, profile, "final")
    BUNDLE.verify_source(bundle)
    BUNDLE.verify_audit_gate(bundle)
    status, current = WP.wp_get(base, user, password, path)
    if status != 200:
        raise RuntimeError(f"WP final prewrite fetch HTTP {status}")
    verify_snapshot(current, request)

    payload = build_update_payload(request, final_html, media, profile)
    try:
        status, written = WP.wp_post(base, user, password, f"{endpoint}/{int(request['post_id'])}", payload)
    except (TimeoutError, socket.timeout, urllib.error.URLError) as exc:
        raise RuntimeError("WP-TIMEOUT: AUDIT POST uncertain; reconcile before any retry") from exc
    if status != 200 or int(written.get("id", -1)) != int(request["post_id"]):
        raise RuntimeError(f"WP AUDIT update HTTP {status}; reconcile before retry")
    status, readback = WP.wp_get(base, user, password, path)
    if status != 200:
        raise ValueError(f"VERIFY-DIFF: AUDIT readback HTTP {status}")
    raw = (readback.get("content") or {}).get("raw")
    title = readback.get("title") or {}
    actual_title = title.get("raw") if isinstance(title, dict) else title
    expected_meta = payload.get("meta", {})
    actual_meta = readback.get("meta") or {}
    if (
        readback.get("id") != int(request["post_id"])
        or readback.get("status") != request["wp_status_at_fetch"]
        or raw != final_html
        or actual_title != payload["title"]
        or any(actual_meta.get(key) != value for key, value in expected_meta.items())
    ):
        raise ValueError("VERIFY-DIFF: AUDIT REST readback differs from approved write")
    state.update({"post_id": int(request["post_id"]), "verified": True,
                  "wp_status": readback["status"], "update_mode": request["update_mode"]})
    NEW.atomic_json(state_path, state)
    print(f"OK AUDIT post_id={request['post_id']} status={readback['status']} approval_hash={current_hash}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--site-key", required=True)
    parser.add_argument("--profile")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--approval-hash")
    args = parser.parse_args()
    try:
        return run(args)
    except (ValueError, RuntimeError, OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"STOP {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
