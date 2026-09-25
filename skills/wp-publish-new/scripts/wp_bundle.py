#!/usr/bin/env python3
"""Lock one source snapshot and create/verify a content-addressed approval."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path


APPROVAL_FILES = (
    "publish-request.json",
    "content.prepared.html",
    "image-manifest.json",
    "transform-report.json",
)
AUDIT_APPROVAL_FILES = ("audit-plan.json", "audit-gate-report.json")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def approval_files(bundle: Path) -> tuple[str, ...]:
    request = json.loads((bundle / "publish-request.json").read_text(encoding="utf-8"))
    return APPROVAL_FILES + (AUDIT_APPROVAL_FILES if request.get("task_type") == "AUDIT" else ())


def verify_audit_gate(bundle: Path) -> None:
    if "audit-gate-report.json" not in approval_files(bundle):
        return
    path = Path(__file__).resolve().parents[3] / "skills" / "wp-rest-publish" / "scripts" / "wp_audit_gate.py"
    spec = importlib.util.spec_from_file_location("wp_audit_gate_for_bundle", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("AUDIT gate cannot load")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    actual = module.check(bundle)
    report = json.loads((bundle / "audit-gate-report.json").read_text(encoding="utf-8"))
    if report != actual:
        raise ValueError("SOURCE-STALE: AUDIT gate report differs from current inputs")


def bundle_hash(bundle: Path) -> str:
    digest = hashlib.sha256()
    for name in approval_files(bundle):
        path = bundle / name
        if not path.is_file():
            raise ValueError(f"INPUT-MISSING: {name}")
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def verify_source(bundle: Path) -> None:
    lock_path = bundle / "source-lock.json"
    if not lock_path.is_file():
        raise ValueError("INPUT-MISSING: source-lock.json")
    lock_data = json.loads(lock_path.read_text(encoding="utf-8"))
    if lock_data.get("source_type") in {"local_markdown", "local_html"}:
        source = Path(lock_data.get("source_path", ""))
        if not source.is_file() or sha256_file(source) != lock_data.get("source_sha256"):
            raise ValueError("SOURCE-STALE: local source changed after lock")
    elif lock_data.get("source_type") == "google_doc":
        snapshot = bundle / str(lock_data.get("snapshot", "source.snapshot.md"))
        if not snapshot.is_file() or sha256_file(snapshot) != lock_data.get("snapshot_sha256"):
            raise ValueError("SOURCE-STALE: Google Doc snapshot changed after lock")


def lock(args: argparse.Namespace) -> int:
    bundle = Path(args.bundle).resolve()
    approval = bundle / "approval.json"
    if approval.exists():
        raise ValueError("SOURCE-STALE: approval exists; remove it explicitly before rebuilding")
    request_path = Path(args.request).resolve()
    source = Path(args.source).resolve()
    if not request_path.is_file() or not source.is_file():
        raise ValueError("INPUT-MISSING: request/source")
    request = json.loads(request_path.read_text(encoding="utf-8"))
    task_type = str(request.get("task_type", "")).upper()
    required = {"run_id", "client", "site_key", "task_type", "title"}
    if task_type == "NEW":
        required.add("slug")
    missing = sorted(key for key in required if not request.get(key))
    if not (request.get("job_id") or request.get("row_id")):
        missing.append("job_id")
    if task_type not in {"NEW", "AUDIT"} or missing:
        raise ValueError(f"INPUT-MISSING: {task_type} request {missing or ['task_type']}")
    audit_snapshot = None
    if task_type == "AUDIT":
        if request.get("update_mode") not in {"MINIMAL_DIFF", "REBUILD"}:
            raise ValueError("INPUT-MISSING: AUDIT update_mode")
        if not (request.get("post_id") or request.get("target_url")):
            raise ValueError("INPUT-MISSING: AUDIT target_url or post_id")
        if not args.snapshot_meta:
            raise ValueError("INPUT-MISSING: AUDIT --snapshot-meta")
        audit_snapshot = json.loads(Path(args.snapshot_meta).read_text(encoding="utf-8"))
        backup = Path(str(audit_snapshot.get("backup_path", "")))
        if not backup.is_file() or sha256_file(backup) != audit_snapshot.get("raw_sha256"):
            raise ValueError("SOURCE-STALE: AUDIT backup is missing or changed")
        if not all(audit_snapshot.get(key) for key in ("id", "modified", "status", "raw_sha256")):
            raise ValueError("INPUT-MISSING: AUDIT snapshot id/modified/status/raw_sha256")
        if request.get("post_id") and int(request["post_id"]) != int(audit_snapshot["id"]):
            raise ValueError("ROUTE-CONFLICT: AUDIT request post_id differs from snapshot")
        if request.get("target_url") and str(request["target_url"]).rstrip("/") != str(audit_snapshot.get("link", "")).rstrip("/"):
            raise ValueError("ROUTE-CONFLICT: AUDIT target URL differs from snapshot")
    bundle.mkdir(parents=True, exist_ok=True)
    canonical_request = dict(request)
    canonical_request.update(source_type=args.source_type, source_ref=args.source_ref)
    if audit_snapshot:
        canonical_request.update({
            "post_id": int(audit_snapshot["id"]),
            "wp_modified_at_fetch": audit_snapshot["modified"],
            "wp_status_at_fetch": audit_snapshot["status"],
            "wp_raw_sha256_at_fetch": audit_snapshot["raw_sha256"],
            "backup_path": str(Path(audit_snapshot["backup_path"]).resolve()),
        })
        canonical_request.setdefault("target_url", audit_snapshot.get("link"))
    atomic_json(bundle / "publish-request.json", canonical_request)
    lock_data = {
        "version": 1,
        "source_type": args.source_type,
        "source_ref": args.source_ref,
        "source_path": str(source),
        "source_sha256": sha256_file(source),
        "locked_at": datetime.now(timezone.utc).isoformat(),
        "source_revision": args.source_revision,
    }
    if args.source_type == "google_doc":
        suffix = ".html" if source.suffix.lower() in {".html", ".htm"} else ".md"
        snapshot = bundle / f"source.snapshot{suffix}"
        shutil.copyfile(source, snapshot)
        lock_data["snapshot"] = snapshot.name
        lock_data["snapshot_sha256"] = sha256_file(snapshot)
    atomic_json(bundle / "source-lock.json", lock_data)
    print(f"OK locked source_sha256={lock_data['source_sha256']}")
    return 0


def approve(args: argparse.Namespace) -> int:
    bundle = Path(args.bundle).resolve()
    verify_source(bundle)
    verify_audit_gate(bundle)
    digest = bundle_hash(bundle)
    value = {
        "version": 1,
        "approval_hash": digest,
        "approved_by": args.approved_by,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "files": list(approval_files(bundle)),
    }
    atomic_json(bundle / "approval.json", value)
    print(f"OK approval_hash={digest}")
    return 0


def verify(args: argparse.Namespace) -> int:
    bundle = Path(args.bundle).resolve()
    approval_path = bundle / "approval.json"
    if not approval_path.is_file():
        raise ValueError("INPUT-MISSING: approval.json")
    verify_source(bundle)
    verify_audit_gate(bundle)
    approval = json.loads(approval_path.read_text(encoding="utf-8"))
    current = bundle_hash(bundle)
    if approval.get("approval_hash") != current:
        raise ValueError("SOURCE-STALE: approval hash no longer matches bundle")
    if approval.get("files") != list(approval_files(bundle)):
        raise ValueError("SOURCE-STALE: approval file list differs")
    print(f"OK approval_hash={current}")
    return 0


def show_hash(args: argparse.Namespace) -> int:
    bundle = Path(args.bundle).resolve()
    verify_source(bundle)
    print(f"OK approval_hash={bundle_hash(bundle)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p_lock = sub.add_parser("lock")
    p_lock.add_argument("--request", required=True)
    p_lock.add_argument("--source", required=True)
    p_lock.add_argument("--source-type", choices=("google_doc", "local_markdown", "local_html"), required=True)
    p_lock.add_argument("--source-ref", required=True)
    p_lock.add_argument("--source-revision")
    p_lock.add_argument("--snapshot-meta", help="Required for AUDIT: fresh wp_fetch.py metadata")
    p_lock.add_argument("--bundle", required=True)
    p_lock.set_defaults(func=lock)
    p_approve = sub.add_parser("approve")
    p_approve.add_argument("--bundle", required=True)
    p_approve.add_argument("--approved-by", required=True)
    p_approve.set_defaults(func=approve)
    p_verify = sub.add_parser("verify")
    p_verify.add_argument("--bundle", required=True)
    p_verify.set_defaults(func=verify)
    p_hash = sub.add_parser("hash")
    p_hash.add_argument("--bundle", required=True)
    p_hash.set_defaults(func=show_hash)
    args = parser.parse_args()
    try:
        return args.func(args)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"STOP {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
