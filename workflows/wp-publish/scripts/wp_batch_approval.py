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


def _load_bundle_lib():
    path = ROOT / "skills" / "wp-publish-new" / "scripts" / "wp_bundle.py"
    spec = importlib.util.spec_from_file_location("wp_batch_bundle_lib", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUNDLE = _load_bundle_lib()


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


def build_manifest(batch_id: str, bundles: list[Path]) -> dict:
    if not batch_id.strip() or not bundles:
        raise ValueError("INPUT-MISSING: batch_id/bundle")
    jobs = sorted((inspect_bundle(path) for path in bundles), key=lambda item: item["job_id"])
    ids = [item["job_id"] for item in jobs]
    if len(ids) != len(set(ids)):
        raise ValueError("ROUTE-CONFLICT: duplicate job_id in batch")
    return {
        "version": 1,
        "batch_id": batch_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "jobs": jobs,
    }


def verify_manifest(manifest: dict) -> None:
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
            manifest = build_manifest(args.batch_id, [Path(path) for path in args.bundle])
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
