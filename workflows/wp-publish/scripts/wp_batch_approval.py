#!/usr/bin/env python3
"""Bind one explicit approval to an exact set of already-gated job bundles."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUNDLE = _load_module(
    "wp_batch_bundle_lib", ROOT / "skills" / "wp-publish-new" / "scripts" / "wp_bundle.py",
)
PROFILE = _load_module("wp_batch_profile_lib", Path(__file__).with_name("wp_profile_status.py"))


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect_bundle(bundle: Path) -> dict:
    bundle = bundle.resolve()
    BUNDLE.verify_source(bundle)
    request = json.loads((bundle / "publish-request.json").read_text(encoding="utf-8"))
    job_id = request.get("job_id") or (
        f"sheet:{request['row_id']}" if request.get("row_id") else None
    )
    if not job_id or not request.get("run_id"):
        raise ValueError("INPUT-MISSING: bundle job_id/run_id")
    return {
        "job_id": job_id,
        "run_id": request["run_id"],
        "task_type": request.get("task_type"),
        "content_type": request.get("content_type", "blog"),
        "title": request.get("title"),
        "bundle": str(bundle),
        "bundle_hash": BUNDLE.bundle_hash(bundle),
    }


def build_manifest(batch_id: str, bundles: list[Path], publish_context_path: Path) -> dict:
    if not batch_id.strip() or not bundles:
        raise ValueError("INPUT-MISSING: batch_id/bundle")
    jobs = sorted((inspect_bundle(path) for path in bundles), key=lambda item: item["job_id"])
    ids = [item["job_id"] for item in jobs]
    if len(ids) != len(set(ids)):
        raise ValueError("ROUTE-CONFLICT: duplicate job_id in batch")
    publish_context_path = publish_context_path.resolve()
    context = PROFILE.load_context(publish_context_path)
    profile_hashes = {}
    for content_type in sorted({item["content_type"] for item in jobs}):
        profile = PROFILE.get_profile(context, content_type)
        if not (
            profile.get("status") == "batch-ready"
            and profile.get("ready") is True
            and profile.get("batch_ready") is True
        ):
            raise ValueError(f"BRAND-MISSING: content profile {content_type} is not batch-ready")
        profile_hashes[content_type] = PROFILE.profile_hash(profile)
    return {
        "version": 2,
        "batch_id": batch_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "publish_context": str(publish_context_path),
        "profile_hashes": profile_hashes,
        "jobs": jobs,
    }


def verify_manifest(manifest: dict) -> None:
    if manifest.get("version") != 2 or not manifest.get("publish_context"):
        raise ValueError("BRAND-MISSING: batch manifest v2 with publish context is required")
    context = PROFILE.load_context(Path(manifest["publish_context"]))
    profile_hashes = manifest.get("profile_hashes") or {}
    job_types = {item.get("content_type", "blog") for item in manifest.get("jobs", [])}
    if set(profile_hashes) != job_types:
        raise ValueError("BRAND-MISSING: batch profile hashes do not match job content types")
    for content_type, expected_hash in profile_hashes.items():
        profile = PROFILE.get_profile(context, content_type)
        if not (
            profile.get("status") == "batch-ready"
            and profile.get("ready") is True
            and profile.get("batch_ready") is True
        ):
            raise ValueError(f"BRAND-MISSING: content profile {content_type} is not batch-ready")
        if PROFILE.profile_hash(profile) != expected_hash:
            raise ValueError(f"SOURCE-STALE: content profile changed: {content_type}")
    for item in manifest.get("jobs", []):
        current = inspect_bundle(Path(item["bundle"]))
        if current["job_id"] != item.get("job_id") or current["bundle_hash"] != item.get("bundle_hash"):
            raise ValueError(f"SOURCE-STALE: batch job changed: {item.get('job_id')}")


def approve_manifest(manifest_path: Path, expected_hash: str, approved_by: str) -> dict:
    current_hash = file_sha256(manifest_path)
    if current_hash != expected_hash:
        raise ValueError("SOURCE-STALE: batch manifest hash mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    verify_manifest(manifest)
    approved_at = datetime.now(timezone.utc).isoformat()
    for item in manifest["jobs"]:
        BUNDLE.atomic_json(Path(item["bundle"]) / "approval.json", {
            "version": 1,
            "approval_hash": item["bundle_hash"],
            "approved_by": approved_by,
            "approved_at": approved_at,
            "files": list(BUNDLE.APPROVAL_FILES),
            "batch_id": manifest["batch_id"],
            "batch_manifest_hash": current_hash,
        })
    return {
        "version": 1,
        "batch_id": manifest["batch_id"],
        "batch_manifest_hash": current_hash,
        "approved_by": approved_by,
        "approved_at": approved_at,
        "job_count": len(manifest["jobs"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--batch-id", required=True)
    build.add_argument("--bundle", action="append", required=True)
    build.add_argument("--profile", required=True, help="Project publish-context.json")
    build.add_argument("--out", required=True)
    approve = sub.add_parser("approve")
    approve.add_argument("--manifest", required=True)
    approve.add_argument("--expected-hash", required=True)
    approve.add_argument("--approved-by", required=True)
    approve.add_argument("--out")
    verify = sub.add_parser("verify")
    verify.add_argument("--manifest", required=True)
    args = parser.parse_args()
    try:
        if args.command == "build":
            manifest = build_manifest(
                args.batch_id, [Path(path) for path in args.bundle], Path(args.profile),
            )
            output = Path(args.out)
            BUNDLE.atomic_json(output, manifest)
            print(f"OK jobs={len(manifest['jobs'])} manifest_hash={file_sha256(output)}")
        elif args.command == "approve":
            manifest_path = Path(args.manifest)
            approval = approve_manifest(manifest_path, args.expected_hash, args.approved_by)
            output = Path(args.out) if args.out else manifest_path.with_name("batch-approval.json")
            BUNDLE.atomic_json(output, approval)
            print(f"OK jobs={approval['job_count']} batch_manifest_hash={approval['batch_manifest_hash']}")
        else:
            manifest_path = Path(args.manifest)
            verify_manifest(json.loads(manifest_path.read_text(encoding="utf-8")))
            print(f"OK manifest_hash={file_sha256(manifest_path)}")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"STOP {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
