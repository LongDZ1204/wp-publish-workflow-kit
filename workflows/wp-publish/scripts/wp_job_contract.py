#!/usr/bin/env python3
"""Normalize one publishing job independently from any tracker."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ADAPTERS = {"local_markdown", "local_html", "google_doc"}
TRACKERS = {"none", "google_sheet"}
CONTENT_TYPES = {"blog", "service-page", "product"}


class ContractError(ValueError):
    pass


def _nonempty(value) -> bool:
    return value is not None and (not isinstance(value, str) or bool(value.strip()))


def _infer_adapter(source_ref: str) -> str:
    ref = source_ref.lower()
    if "docs.google.com/document" in ref:
        return "google_doc"
    if ref.endswith((".html", ".htm")):
        return "local_html"
    return "local_markdown"


def normalize(value: dict) -> dict:
    """Return the v2 job while accepting v1 Sheet-shaped requests."""
    job = dict(value)
    task_type = str(job.get("task_type", "")).strip().upper()
    job["task_type"] = task_type

    row_id = str(job.get("row_id", "")).strip()
    job_id = str(job.get("job_id", "")).strip()
    if not job_id and row_id:
        job_id = f"sheet:{row_id}"
    job["job_id"] = job_id

    source = dict(job.get("source") or {})
    source_ref = str(source.get("ref") or job.get("source_ref") or "").strip()
    adapter = str(source.get("adapter") or job.get("source_type") or "").strip()
    if source_ref and not adapter:
        adapter = _infer_adapter(source_ref)
    source.update({"adapter": adapter, "ref": source_ref})
    if job.get("source_revision") and not source.get("revision"):
        source["revision"] = job["source_revision"]
    job["source"] = source

    tracker = dict(job.get("tracker") or {})
    if not tracker:
        tracker = {"type": "google_sheet", "row_id": row_id} if row_id else {"type": "none"}
    tracker.setdefault("type", "none")
    if tracker["type"] == "google_sheet" and row_id:
        tracker.setdefault("row_id", row_id)
    job["tracker"] = tracker
    job.setdefault("content_type", "blog")
    if job.get("update_mode"):
        job["update_mode"] = str(job["update_mode"]).strip().upper().replace("-", "_")
    job["version"] = 2
    return job


def validate(value: dict) -> dict:
    job = normalize(value)
    missing = [
        key for key in ("job_id", "run_id", "client", "site_key", "task_type", "title")
        if not _nonempty(job.get(key))
    ]
    if not _nonempty(job["source"].get("ref")):
        missing.append("source.ref")
    if missing:
        raise ContractError("INPUT-MISSING: " + ", ".join(missing))
    if job["task_type"] not in {"NEW", "AUDIT"}:
        raise ContractError("INPUT-MISSING: task_type must be NEW or AUDIT")
    if job["source"].get("adapter") not in ADAPTERS:
        raise ContractError("INPUT-MISSING: unsupported source.adapter")
    if job["tracker"].get("type") not in TRACKERS:
        raise ContractError("INPUT-MISSING: unsupported tracker.type")
    if job.get("content_type") not in CONTENT_TYPES:
        raise ContractError("INPUT-MISSING: unsupported content_type")
    if job["task_type"] == "NEW" and not _nonempty(job.get("slug")):
        raise ContractError("INPUT-MISSING: slug is required for NEW")
    if job["task_type"] == "AUDIT" and not (
        _nonempty(job.get("target_url")) or _nonempty(job.get("post_id"))
    ):
        raise ContractError("INPUT-MISSING: target_url or post_id is required for AUDIT")
    if job["task_type"] == "AUDIT" and job.get("update_mode") not in {"MINIMAL_DIFF", "REBUILD"}:
        raise ContractError("INPUT-MISSING: AUDIT update_mode must be MINIMAL_DIFF or REBUILD")
    if job["tracker"]["type"] == "google_sheet" and not _nonempty(job["tracker"].get("row_id")):
        raise ContractError("INPUT-MISSING: tracker.row_id")
    return job


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="input_path", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    try:
        job = validate(json.loads(Path(args.input_path).read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, ContractError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(job, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK job_id={job['job_id']} task_type={job['task_type']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
