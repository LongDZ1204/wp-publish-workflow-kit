#!/usr/bin/env python3
"""Create an immutable, format-aware source snapshot and asset inventory."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


ADAPTER_SUFFIX = {
    "local_markdown": ".md",
    "local_html": ".html",
    "google_doc": ".html",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_intake(
    adapter: str,
    source: Path,
    source_ref: str,
    output: Path,
    assets_path: Path | None = None,
    source_revision: str | None = None,
) -> dict:
    if adapter not in ADAPTER_SUFFIX:
        raise ValueError("INPUT-MISSING: unsupported adapter")
    if not source.is_file():
        raise ValueError("INPUT-MISSING: source file")
    if not source_ref.strip():
        raise ValueError("INPUT-MISSING: source_ref")
    suffix = source.suffix.lower()
    if adapter == "google_doc" and suffix not in {".html", ".htm", ".md", ".markdown"}:
        raise ValueError("INPUT-MISSING: Google Doc export must be HTML or Markdown")
    if adapter == "google_doc" and suffix in {".md", ".markdown"}:
        snapshot_name = "content.snapshot.md"
    else:
        snapshot_name = "content.snapshot" + ADAPTER_SUFFIX[adapter]

    assets = {"version": 1, "images": []}
    if assets_path:
        assets = json.loads(assets_path.read_text(encoding="utf-8"))
        if not isinstance(assets, dict) or not isinstance(assets.get("images"), list):
            raise ValueError("INPUT-MISSING: assets.images must be a list")
    output.mkdir(parents=True, exist_ok=True)
    snapshot = output / snapshot_name
    if snapshot.exists() or (output / "intake.json").exists():
        raise ValueError("SOURCE-STALE: intake already exists")
    shutil.copyfile(source, snapshot)
    (output / "assets.json").write_text(
        json.dumps(assets, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    intake = {
        "version": 1,
        "adapter": adapter,
        "source_ref": source_ref,
        "source_revision": source_revision,
        "snapshot": snapshot_name,
        "media_type": "text/html" if snapshot.suffix == ".html" else "text/markdown",
        "source_sha256": sha256(source),
        "snapshot_sha256": sha256(snapshot),
        "assets_sha256": sha256(output / "assets.json"),
        "asset_count": len(assets["images"]),
        "locked_at": datetime.now(timezone.utc).isoformat(),
    }
    (output / "intake.json").write_text(
        json.dumps(intake, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return intake


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", choices=tuple(ADAPTER_SUFFIX), required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--source-revision")
    parser.add_argument("--assets-json")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    try:
        intake = create_intake(
            args.adapter,
            Path(args.source).resolve(),
            args.source_ref,
            Path(args.out).resolve(),
            Path(args.assets_json).resolve() if args.assets_json else None,
            args.source_revision,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"STOP {exc}")
        return 2
    print(f"OK snapshot={intake['snapshot']} assets={intake['asset_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
