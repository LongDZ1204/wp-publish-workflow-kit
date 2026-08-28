#!/usr/bin/env python3
"""Fail-closed router: Sheet chooses intent, WP state only verifies it."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit


class RouteConflict(ValueError):
    pass


def _matches(wp_state) -> list[dict]:
    if wp_state is None:
        return []
    if isinstance(wp_state, list):
        return wp_state
    if isinstance(wp_state, dict) and isinstance(wp_state.get("matches"), list):
        return wp_state["matches"]
    if isinstance(wp_state, dict) and wp_state.get("id"):
        return [wp_state]
    return []


def _same_url(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    pa, pb = urlsplit(a), urlsplit(b)
    return (pa.netloc.lower(), pa.path.rstrip("/")) == (pb.netloc.lower(), pb.path.rstrip("/"))


def route(row: dict, wp_state, run_state: dict | None = None) -> dict:
    matches = _matches(wp_state)
    task = row.get("task_type")
    if task == "NEW":
        if not matches:
            return {"route": "NEW_PREPARE", "reason": "slug absent on WordPress"}
        if len(matches) != 1:
            raise RouteConflict("ROUTE-CONFLICT: NEW matched multiple WordPress objects")
        post = matches[0]
        if (
            post.get("status") == "draft"
            and run_state
            and str(run_state.get("post_id")) == str(post.get("id"))
            and run_state.get("run_id") == row.get("run_id")
        ):
            return {"route": "NEW_RESUME", "post_id": post.get("id"), "reason": "same managed draft"}
        raise RouteConflict("ROUTE-CONFLICT: NEW slug already exists and is not the same managed draft")

    if task == "AUDIT":
        if len(matches) != 1:
            raise RouteConflict(f"ROUTE-CONFLICT: AUDIT expected one WordPress object, got {len(matches)}")
        post = matches[0]
        if row.get("post_id") and str(row["post_id"]) != str(post.get("id")):
            raise RouteConflict("ROUTE-CONFLICT: Sheet post_id differs from WordPress")
        if row.get("target_url") and not _same_url(row["target_url"], post.get("link")):
            raise RouteConflict("ROUTE-CONFLICT: Sheet target_url differs from WordPress")
        return {"route": "AUDIT_PREPARE", "post_id": post.get("id"), "status": post.get("status")}

    raise RouteConflict("ROUTE-CONFLICT: unsupported task_type")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--row", required=True)
    ap.add_argument("--wp-state", required=True)
    ap.add_argument("--run-state")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    try:
        row = json.loads(Path(args.row).read_text(encoding="utf-8"))
        wp_state = json.loads(Path(args.wp_state).read_text(encoding="utf-8"))
        run_state = json.loads(Path(args.run_state).read_text(encoding="utf-8")) if args.run_state else None
        result = route(row, wp_state, run_state)
    except (OSError, json.JSONDecodeError, RouteConflict) as exc:
        result = {"route": "STOP", "error_code": "ROUTE-CONFLICT", "details": str(exc)}
        Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(result["details"], file=sys.stderr)
        return 2
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(result["route"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
