#!/usr/bin/env python3
"""Bounded error aggregation; never edits production rules."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


MAX_ITEMS = 128
MAX_EVIDENCE = 3
MAX_RECENT_DIGESTS = 32
MAX_INDEX_BYTES = 64 * 1024


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _digest(run_id: str) -> str:
    return hashlib.sha256(run_id.encode()).hexdigest()[:12]


def load_index(path: Path) -> dict:
    if not path.exists():
        return {"version": 1, "items": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data.get("items"), dict):
        raise ValueError("learning index items must be an object")
    return data


def record(index: dict, event: dict) -> dict:
    for key in ("error_code", "client", "step", "run_id"):
        if not event.get(key):
            raise ValueError(f"event missing {key}")
    learning_key = event.get("learning_key") or f"{event['error_code']}|{event['client']}|{event['step']}"
    items = index["items"]
    if learning_key not in items and len(items) >= MAX_ITEMS:
        raise ValueError("learning index item cap reached; consolidate before adding a key")
    item = items.setdefault(learning_key, {
        "learning_key": learning_key,
        "error_code": event["error_code"],
        "client": event["client"],
        "step": event["step"],
        "count": 0,
        "distinct_runs": 0,
        "first_seen": event.get("occurred_at") or _now(),
        "last_seen": None,
        "sample_run_ids": [],
        "recent_run_digests": [],
        "status": "observing",
    })
    item["count"] += 1
    item["last_seen"] = event.get("occurred_at") or _now()
    digest = _digest(str(event["run_id"]))
    if digest not in item["recent_run_digests"]:
        item["distinct_runs"] += 1
        item["recent_run_digests"].append(digest)
        item["recent_run_digests"] = item["recent_run_digests"][-MAX_RECENT_DIGESTS:]
        if len(item["sample_run_ids"]) < MAX_EVIDENCE:
            item["sample_run_ids"].append(str(event["run_id"]))
    if item["distinct_runs"] >= 3 and item["status"] == "observing":
        item["status"] = "candidate"
    return item


def atomic_save(path: Path, data: dict) -> None:
    payload = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode()
    if len(payload) > MAX_INDEX_BYTES:
        raise ValueError("learning index exceeds 64KB hard cap")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(payload)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    rec = sub.add_parser("record")
    rec.add_argument("--index", required=True)
    rec.add_argument("--event", required=True)
    cand = sub.add_parser("candidates")
    cand.add_argument("--index", required=True)
    args = ap.parse_args()
    path = Path(args.index)
    index = load_index(path)
    if args.cmd == "record":
        event = json.loads(Path(args.event).read_text(encoding="utf-8"))
        item = record(index, event)
        atomic_save(path, index)
        print(json.dumps(item, ensure_ascii=False, indent=2))
    else:
        candidates = [v for v in index["items"].values() if v.get("status") == "candidate"]
        print(json.dumps(candidates, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
