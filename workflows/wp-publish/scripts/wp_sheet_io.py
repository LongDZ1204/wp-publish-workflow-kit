#!/usr/bin/env python3
"""Prepare an allow-listed Sheet tracking patch and verify connector readback."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


TRACKING_FIELDS = {
    "Trạng thái", "URL draft/live", "Note", "Cập nhật lúc",
}
IMMUTABLE_FIELDS = {"Row ID", "Bài / Title", "Loại bài", "Nguồn content", "Slug / URL WP"}
STATUS_VALUES = {"Chờ chạy", "Chờ xác nhận", "Chờ đăng", "Hoàn tất", "Cần xử lý"}


def prepare(row: dict, updates: dict) -> dict:
    row_id = row.get("Row ID") or row.get("row_id")
    if not row_id:
        raise ValueError("INPUT-MISSING: Row ID")
    forbidden = sorted(set(updates) - TRACKING_FIELDS)
    if forbidden or set(updates) & IMMUTABLE_FIELDS:
        raise ValueError(f"SHEET-WRITE: non-tracking fields {forbidden}")
    if "Trạng thái" in updates and updates["Trạng thái"] not in STATUS_VALUES:
        raise ValueError(f"SHEET-WRITE: invalid Trạng thái {updates['Trạng thái']!r}")
    return {"lookup": {"Row ID": row_id}, "updates": updates}


def verify(expected: dict, readback: dict) -> None:
    row_id = expected.get("lookup", {}).get("Row ID")
    if str(readback.get("Row ID")) != str(row_id):
        raise ValueError("SHEET-READBACK: Row ID mismatch")
    mismatches = {
        key: {"expected": value, "actual": readback.get(key)}
        for key, value in expected.get("updates", {}).items()
        if readback.get(key) != value
    }
    if mismatches:
        raise ValueError(f"SHEET-READBACK: {json.dumps(mismatches, ensure_ascii=False, sort_keys=True)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p_prepare = sub.add_parser("prepare")
    p_prepare.add_argument("--row", required=True)
    p_prepare.add_argument("--updates", required=True)
    p_prepare.add_argument("--out", required=True)
    p_verify = sub.add_parser("verify")
    p_verify.add_argument("--expected", required=True)
    p_verify.add_argument("--readback", required=True)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            patch = prepare(
                json.loads(Path(args.row).read_text(encoding="utf-8")),
                json.loads(Path(args.updates).read_text(encoding="utf-8")),
            )
            Path(args.out).write_text(json.dumps(patch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"OK row_id={patch['lookup']['Row ID']} fields={len(patch['updates'])}")
        else:
            verify(
                json.loads(Path(args.expected).read_text(encoding="utf-8")),
                json.loads(Path(args.readback).read_text(encoding="utf-8")),
            )
            print("OK SHEET-READBACK")
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"STOP {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
