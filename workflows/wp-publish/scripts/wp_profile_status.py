#!/usr/bin/env python3
"""Move one content-type profile from JIT confirmation to pilot and batch readiness."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


CONTENT_TYPES = {"blog", "service-page", "product"}
STATE_FIELDS = {
    "status", "ready", "pilot_allowed", "batch_ready", "confirmation", "certification",
}
RENDER_CHECKS = {"content", "images", "heading", "links", "seo_meta"}


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def stable_hash(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def profile_hash(profile: dict) -> str:
    return stable_hash({key: value for key, value in profile.items() if key not in STATE_FIELDS})


def load_context(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("version") != 2 or not isinstance(value.get("content_profiles"), dict):
        raise ValueError("BRAND-MISSING: publish context v2 with content_profiles is required")
    return value


def get_profile(context: dict, content_type: str) -> dict:
    if content_type not in CONTENT_TYPES:
        raise ValueError(f"INPUT-MISSING: unsupported content type {content_type}")
    profile = context["content_profiles"].get(content_type)
    if not isinstance(profile, dict):
        raise ValueError(f"BRAND-MISSING: content profile {content_type}")
    return profile


def validate_configuration(profile: dict, expected_schema_hash: str | None = None) -> None:
    required = ["endpoint", "post_type", "html_policy", "required_fields", "required_capabilities", "image_policy"]
    missing = [key for key in required if profile.get(key) in (None, "", [], {})]
    if profile.get("body_h1_count") not in {0, 1}:
        missing.append("body_h1_count")
    if not profile.get("schema_hash"):
        missing.append("schema_hash")
    if "missing_capabilities" not in profile:
        missing.append("missing_capabilities")
    if profile.get("missing_capabilities"):
        raise ValueError(
            "BRAND-MISSING: missing capabilities " + ", ".join(profile["missing_capabilities"])
        )
    if missing:
        raise ValueError("BRAND-MISSING: incomplete profile " + ", ".join(sorted(set(missing))))
    if expected_schema_hash and profile.get("schema_hash") != expected_schema_hash:
        raise ValueError("SOURCE-STALE: WordPress schema hash changed before confirmation")
    adapter = profile.get("seo_meta_adapter")
    if adapter not in {None, "none", "yoast", "rankmath"}:
        raise ValueError("BRAND-MISSING: seo_meta_adapter must be none, yoast or rankmath")


def confirm(
    context_path: Path,
    content_type: str,
    confirmed_by: str,
    expected_schema_hash: str | None = None,
) -> dict:
    context = load_context(context_path)
    profile = get_profile(context, content_type)
    if profile.get("status") == "batch-ready" or profile.get("batch_ready") is True:
        raise ValueError("ROUTE-CONFLICT: profile is already batch-ready")
    validate_configuration(profile, expected_schema_hash)
    now = datetime.now(timezone.utc).isoformat()
    profile.update({
        "status": "pilot-ready",
        "ready": False,
        "pilot_allowed": True,
        "batch_ready": False,
    })
    profile["confirmation"] = {
        "confirmed_by": confirmed_by,
        "confirmed_at": now,
        "profile_hash": profile_hash(profile),
    }
    atomic_json(context_path, context)
    return {"content_type": content_type, "status": "pilot-ready", "profile_hash": profile_hash(profile)}


def certify(
    context_path: Path,
    content_type: str,
    bundle: Path,
    render_report_path: Path,
    certified_by: str,
) -> dict:
    context = load_context(context_path)
    profile = get_profile(context, content_type)
    if profile.get("status") != "pilot-ready" or profile.get("pilot_allowed") is not True:
        raise ValueError("BRAND-MISSING: profile must be confirmed as pilot-ready first")
    request = json.loads((bundle / "publish-request.json").read_text(encoding="utf-8"))
    state = json.loads((bundle / "run-state.json").read_text(encoding="utf-8"))
    render = json.loads(render_report_path.read_text(encoding="utf-8"))
    if request.get("content_type", "blog") != content_type:
        raise ValueError("RESUME-CONFLICT: pilot content type does not match profile")
    request_job_id = request.get("job_id") or (
        f"sheet:{request['row_id']}" if request.get("row_id") else None
    )
    state_job_id = state.get("job_id") or (
        f"sheet:{state['row_id']}" if state.get("row_id") else None
    )
    if state.get("run_id") != request.get("run_id") or state_job_id != request_job_id:
        raise ValueError("RESUME-CONFLICT: pilot state does not match request")
    if not (
        state.get("pilot") is True
        and state.get("verified") is True
        and state.get("wp_status") == "draft"
        and state.get("content_type") == content_type
    ):
        raise ValueError("VERIFY-DIFF: pilot REST readback is not verified")
    current_profile_hash = profile_hash(profile)
    if state.get("profile_hash") != current_profile_hash:
        raise ValueError("SOURCE-STALE: profile changed after pilot execution")
    checks = render.get("checks") if isinstance(render.get("checks"), dict) else {}
    failed_checks = sorted(name for name in RENDER_CHECKS if checks.get(name) is not True)
    if render.get("ok") is not True or failed_checks:
        raise ValueError("VERIFY-DIFF: rendered QA incomplete " + ", ".join(failed_checks))
    if int(render.get("post_id", 0)) != int(state.get("post_id", -1)):
        raise ValueError("VERIFY-DIFF: rendered QA post_id differs from pilot")

    now = datetime.now(timezone.utc).isoformat()
    profile.update({
        "status": "batch-ready",
        "ready": True,
        "pilot_allowed": False,
        "batch_ready": True,
        "certification": {
            "certified_by": certified_by,
            "certified_at": now,
            "pilot_job_id": request_job_id,
            "pilot_run_id": request.get("run_id"),
            "post_id": int(state["post_id"]),
            "profile_hash": current_profile_hash,
            "render_report_sha256": hashlib.sha256(render_report_path.read_bytes()).hexdigest(),
        },
    })
    atomic_json(context_path, context)
    return {"content_type": content_type, "status": "batch-ready", "post_id": int(state["post_id"])}


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    confirm_parser = sub.add_parser("confirm")
    confirm_parser.add_argument("--context", required=True)
    confirm_parser.add_argument("--content-type", choices=sorted(CONTENT_TYPES), required=True)
    confirm_parser.add_argument("--confirmed-by", required=True)
    confirm_parser.add_argument("--expected-schema-hash")
    certify_parser = sub.add_parser("certify")
    certify_parser.add_argument("--context", required=True)
    certify_parser.add_argument("--content-type", choices=sorted(CONTENT_TYPES), required=True)
    certify_parser.add_argument("--bundle", required=True)
    certify_parser.add_argument("--render-report", required=True)
    certify_parser.add_argument("--certified-by", required=True)
    args = parser.parse_args()
    try:
        if args.command == "confirm":
            result = confirm(
                Path(args.context), args.content_type, args.confirmed_by, args.expected_schema_hash,
            )
        else:
            result = certify(
                Path(args.context), args.content_type, Path(args.bundle),
                Path(args.render_report), args.certified_by,
            )
        print(
            f"OK content_type={result['content_type']} status={result['status']}"
            + (f" post_id={result['post_id']}" if result.get("post_id") else "")
        )
        return 0
    except (OSError, ValueError, json.JSONDecodeError, KeyError) as exc:
        print(f"STOP {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
