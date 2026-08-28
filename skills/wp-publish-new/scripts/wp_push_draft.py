#!/usr/bin/env python3
"""Approval-bound WordPress draft creator. Dry-run unless --execute is explicit."""

from __future__ import annotations

import argparse
import importlib.util
import json
import mimetypes
import os
import socket
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUNDLE_LIB = load_module("wp_bundle_local", Path(__file__).with_name("wp_bundle.py"))
WP_LIB = load_module("wp_rest_lib", ROOT / "skills" / "wp-rest-publish" / "scripts" / "wp_lib.py")
GATE_LIB = load_module("wp_gate_local", Path(__file__).with_name("wp_gate.py"))


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def replace_asset_tokens(html: str, manifest: dict, media: dict) -> str:
    result = html
    for item in manifest.get("images", []):
        asset_id = str(item.get("asset_id", ""))
        if not asset_id:
            raise ValueError("IMG-MISSING: asset_id")
        url = item.get("existing_url") if item.get("action") == "preserve-existing" else media.get(asset_id, {}).get("source_url")
        if not url:
            raise ValueError(f"IMG-MISSING: no WordPress URL for {asset_id}")
        result = result.replace(f"asset://{asset_id}", str(url))
    if "asset://" in result:
        raise ValueError("IMG-MISSING: unresolved asset token")
    return result


def media_search(base_url: str, user: str, app_pass: str, filename: str) -> list[dict]:
    stem = Path(filename).stem
    query = urllib.parse.urlencode({"search": stem, "context": "edit", "per_page": 100})
    status, rows = WP_LIB.wp_get(base_url, user, app_pass, f"media?{query}")
    if status >= 300:
        raise RuntimeError(f"WP media search failed HTTP {status}")
    return [row for row in rows if Path(urllib.parse.urlparse(row.get("source_url", "")).path).name == filename]


def upload_media(base_url: str, user: str, app_pass: str, item: dict) -> dict:
    source = Path(item.get("output", ""))
    filename = str(item.get("filename", source.name))
    if not source.is_file():
        raise ValueError(f"IMG-MISSING: {source}")
    matches = media_search(base_url, user, app_pass, filename)
    if matches:
        raise ValueError(f"IMG-DUP: {filename} already exists; approve explicit reuse instead")
    req = urllib.request.Request(
        f"{base_url}/wp-json/wp/v2/media",
        data=source.read_bytes(),
        method="POST",
    )
    req.add_header("Authorization", WP_LIB._auth_header(user, app_pass))
    req.add_header("Content-Type", mimetypes.guess_type(filename)[0] or "application/octet-stream")
    req.add_header("Content-Disposition", f'attachment; filename="{filename}"')
    try:
        with urllib.request.urlopen(req, timeout=120, context=WP_LIB._CTX) as response:
            media = WP_LIB._decode(response.read().decode(), "POST media")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        raise RuntimeError(f"WP media upload HTTP {exc.code}: {body[:300]}") from exc
    media_id = int(media["id"])
    payload = {
        "alt_text": item.get("alt", ""),
        "caption": item.get("caption", ""),
        "title": Path(filename).stem.replace("-", " "),
    }
    status, updated = WP_LIB.wp_post(base_url, user, app_pass, f"media/{media_id}", payload)
    if status >= 300:
        raise RuntimeError(f"WP media metadata HTTP {status}")
    return {"media_id": media_id, "source_url": updated.get("source_url") or media.get("source_url")}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_payload(request: dict, final_html: str, media: dict, profile: dict | None = None) -> dict:
    payload: dict = {
        "status": "draft",
        "title": request["title"],
        "slug": request["slug"],
        "content": final_html,
    }
    for source_key, target_key in (("excerpt", "excerpt"), ("category_ids", "categories"), ("tag_ids", "tags")):
        if request.get(source_key) not in (None, "", []):
            payload[target_key] = request[source_key]
    meta = dict(request.get("meta") or {})
    adapter = str((profile or {}).get("seo_meta_adapter") or "").lower()
    if request.get("meta_description") or request.get("seo_title"):
        seo_title = request.get("seo_title") or request["title"]
        if adapter == "yoast":
            meta["_yoast_wpseo_title"] = seo_title
            if request.get("meta_description"):
                meta["_yoast_wpseo_metadesc"] = request["meta_description"]
        elif adapter == "rankmath":
            meta["rank_math_title"] = seo_title
            if request.get("meta_description"):
                meta["rank_math_description"] = request["meta_description"]
        else:
            raise ValueError("BRAND-MISSING: seo_meta_adapter must be yoast or rankmath")
    if meta:
        payload["meta"] = meta
    featured = request.get("featured_asset_id")
    if featured:
        record = media.get(str(featured))
        if not record:
            raise ValueError(f"IMG-MISSING: featured asset {featured}")
        payload["featured_media"] = int(record["media_id"])
    return payload


def run(args: argparse.Namespace) -> int:
    bundle = Path(args.bundle).resolve()
    request = read_json(bundle / "publish-request.json")
    manifest = read_json(bundle / "image-manifest.json")
    approval = read_json(bundle / "approval.json")
    BUNDLE_LIB.verify_source(bundle)
    current_hash = BUNDLE_LIB.bundle_hash(bundle)
    if approval.get("approval_hash") != current_hash:
        raise ValueError("SOURCE-STALE: approval no longer matches bundle")
    if str(request.get("task_type", "")).upper() != "NEW":
        raise ValueError("ROUTE-CONFLICT: wp-publish-new only accepts NEW")
    uploads = [item for item in manifest.get("images", []) if item.get("action") == "prepare-upload"]
    if not args.execute:
        print(json.dumps({
            "mode": "dry-run",
            "approval_hash": current_hash,
            "slug": request.get("slug"),
            "uploads": [item.get("filename") for item in uploads],
            "target_status": "draft",
        }, ensure_ascii=False, indent=2))
        return 0
    if args.approval_hash != current_hash:
        raise ValueError("SOURCE-STALE: --approval-hash mismatch")
    if not args.profile:
        raise ValueError("BRAND-MISSING: --profile")
    profile = read_json(Path(args.profile))
    if profile.get("ready") is not True and not (args.pilot and profile.get("pilot_allowed") is True):
        raise ValueError("BRAND-MISSING: publish context is not ready")
    state_path = bundle / "run-state.json"
    state = read_json(state_path) if state_path.exists() else {
        "version": 1, "run_id": request["run_id"], "row_id": request["row_id"], "media": {}, "post_id": None,
    }
    if state.get("run_id") != request.get("run_id") or state.get("row_id") != request.get("row_id"):
        raise ValueError("RESUME-CONFLICT: run-state belongs to another request")
    base_url, user, app_pass = WP_LIB.load_credential(args.site_key)
    media = dict(state.get("media") or {})
    for item in uploads:
        asset_id = str(item["asset_id"])
        if asset_id in media:
            continue
        media[asset_id] = upload_media(base_url, user, app_pass, item)
        state["media"] = media
        atomic_json(state_path, state)
    for item in manifest.get("images", []):
        if item.get("action") == "preserve-existing" and item.get("media_id"):
            media[str(item["asset_id"])] = {"media_id": int(item["media_id"]), "source_url": item["existing_url"]}
    prepared = (bundle / "content.prepared.html").read_text(encoding="utf-8")
    final_html = replace_asset_tokens(prepared, manifest, media)
    (bundle / "content.final.html").write_text(final_html, encoding="utf-8")
    GATE_LIB.validate(bundle, profile, "final", allow_pilot=args.pilot)
    if state.get("post_id"):
        status, post = WP_LIB.wp_get(base_url, user, app_pass, f"posts/{int(state['post_id'])}?context=edit")
        if status >= 300 or post.get("status") != "draft":
            raise ValueError("RESUME-CONFLICT: stored draft cannot be verified")
    else:
        query = urllib.parse.urlencode({"slug": request["slug"], "context": "edit", "status": "any"})
        status, existing = WP_LIB.wp_get(base_url, user, app_pass, f"posts?{query}")
        if status >= 300:
            raise RuntimeError(f"WP slug lookup HTTP {status}")
        if existing:
            raise ValueError("ROUTE-CONFLICT: slug already exists in WordPress")
        payload = build_payload(request, final_html, media, profile)
        try:
            status, post = WP_LIB.wp_post(base_url, user, app_pass, "posts", payload)
        except (TimeoutError, socket.timeout, urllib.error.URLError) as exc:
            raise RuntimeError("WP-TIMEOUT: draft POST uncertain; reconcile before retry") from exc
        if status >= 300:
            raise RuntimeError(f"WP create draft HTTP {status}")
        state["post_id"] = int(post["id"])
        atomic_json(state_path, state)
    status, readback = WP_LIB.wp_get(base_url, user, app_pass, f"posts/{int(state['post_id'])}?context=edit")
    raw = (readback.get("content") or {}).get("raw")
    expected_meta = build_payload(request, final_html, media, profile).get("meta", {})
    readback_meta = readback.get("meta") or {}
    meta_diff = {
        key: {"expected": value, "actual": readback_meta.get(key)}
        for key, value in expected_meta.items()
        if readback_meta.get(key) != value
    }
    if status >= 300 or readback.get("status") != "draft" or raw != final_html or meta_diff:
        raise ValueError("VERIFY-DIFF: WordPress draft readback differs")
    state["verified"] = True
    state["wp_status"] = "draft"
    atomic_json(state_path, state)
    print(f"OK post_id={state['post_id']} status=draft approval_hash={current_hash}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--site-key", required=True)
    parser.add_argument("--profile")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--approval-hash")
    parser.add_argument("--pilot", action="store_true", help="Run one explicitly enabled draft-only pilot")
    args = parser.parse_args()
    try:
        return run(args)
    except (ValueError, RuntimeError, OSError, json.JSONDecodeError) as exc:
        print(f"STOP {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
