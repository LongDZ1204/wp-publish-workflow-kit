#!/usr/bin/env python3
"""Atomic run-state transitions for wp-publish bundles."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ORDER = [
    "NEW", "CONTEXT_LOCKED", "ROUTED", "PREPARED", "GATED", "APPROVED",
    "MEDIA_READY", "WP_WRITTEN", "WP_VERIFIED", "SHEET_VERIFIED", "COMPLETE",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def transition(state: dict, target: str, error_code: str | None = None, details: str | None = None) -> dict:
    current = state["state"]
    if target == "STOPPED":
        if current != "STOPPED":
            state["resume_state"] = current
        state["state"] = "STOPPED"
        state["error_code"] = error_code or "UNKNOWN"
        state["details"] = details or ""
    elif current == "STOPPED":
        if target != state.get("resume_state"):
            raise ValueError(f"RESUME-CONFLICT: expected {state.get('resume_state')}, got {target}")
        state["state"] = target
        state.pop("error_code", None)
        state.pop("details", None)
    else:
        if current not in ORDER or target not in ORDER or ORDER.index(target) != ORDER.index(current) + 1:
            raise ValueError(f"RESUME-CONFLICT: invalid transition {current} -> {target}")
        state["state"] = target
    state["updated_at"] = _now()
    state.setdefault("history", []).append({"state": state["state"], "at": state["updated_at"]})
    state["history"] = state["history"][-20:]
    return state


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    init = sub.add_parser("init")
    init.add_argument("--file", required=True)
    init.add_argument("--row-id", required=True)
    init.add_argument("--run-id", required=True)
    init.add_argument("--task-type", required=True, choices=["NEW", "AUDIT"])
    init.add_argument("--client", required=True)
    move = sub.add_parser("transition")
    move.add_argument("--file", required=True)
    move.add_argument("--to", required=True)
    move.add_argument("--error-code")
    move.add_argument("--details")
    args = ap.parse_args()
    path = Path(args.file)
    if args.cmd == "init":
        if path.exists():
            raise SystemExit("RESUME-CONFLICT: state file already exists")
        now = _now()
        data = {
            "version": 1, "row_id": args.row_id, "run_id": args.run_id,
            "task_type": args.task_type, "client": args.client,
            "state": "NEW", "created_at": now, "updated_at": now,
            "history": [{"state": "NEW", "at": now}],
        }
    else:
        data = json.loads(path.read_text(encoding="utf-8"))
        data = transition(data, args.to, args.error_code, args.details)
    atomic_write(path, data)
    print(f"OK {data['state']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
