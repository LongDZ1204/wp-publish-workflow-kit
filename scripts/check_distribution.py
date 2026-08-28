#!/usr/bin/env python3
"""Fail when a distribution folder contains secrets, runtime bundles or local home paths."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_NAMES = {
    ".env",
    "CLAUDE.local.md",
    "approval.json",
    "run-state.json",
    "source-lock.json",
    "content.final.html",
}
TEXT_SUFFIXES = {".md", ".py", ".json", ".yaml", ".yml", ".txt", ".csv", ".toml"}
LOCAL_HOME = re.compile(r"/(?:Users|home)/[^/\s]+/")


def main() -> int:
    errors: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        rel = path.relative_to(ROOT)
        if path.name in FORBIDDEN_NAMES:
            errors.append(f"runtime/secret file: {rel}")
        if path.suffix.lower() in TEXT_SUFFIXES:
            text = path.read_text(encoding="utf-8", errors="replace")
            if LOCAL_HOME.search(text):
                errors.append(f"absolute home path: {rel}")
    if errors:
        print("DISTRIBUTION CHECK FAILED")
        for error in errors:
            print(f"- {error}")
        return 2
    print("OK distribution contains no runtime files or absolute home paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
