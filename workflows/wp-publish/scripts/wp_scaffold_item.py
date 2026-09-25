#!/usr/bin/env python3
"""Create one non-destructive, per-run workspace for a WordPress item."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


CONTENT_TYPES = {"blog", "service-page", "product"}
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


def scaffold_item(client: str, content_type: str, slug: str, run_id: str, projects_root: Path) -> dict:
    for label, value in (("client", client), ("slug", slug), ("run_id", run_id)):
        if not SLUG.fullmatch(value):
            raise ValueError(f"INPUT-MISSING: {label} must be a kebab-case slug")
    if content_type not in CONTENT_TYPES:
        raise ValueError("INPUT-MISSING: content_type must be blog, service-page or product")
    project = projects_root.resolve() / client
    if not (project / "publish-context.json").is_file():
        raise ValueError("INPUT-MISSING: scaffold the project before creating an item run")
    item = project / "content" / content_type / slug
    folders = (
        item / "assets" / "original" / run_id,
        item / "assets" / "prepared" / run_id,
        item / "backups",
        item / "runs" / run_id / "intake",
        item / "runs" / run_id / "snapshot",
        item / "runs" / run_id / "work",
        item / "runs" / run_id / "bundle",
    )
    created = []
    for folder in folders:
        if not folder.is_dir():
            folder.mkdir(parents=True, exist_ok=True)
            created.append(str(folder.relative_to(project)))
    return {
        "item": str(item),
        "run": str(item / "runs" / run_id),
        "created": created,
        "preserved": len(folders) - len(created),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--client", required=True)
    parser.add_argument("--content-type", required=True)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--projects-root", default=str(Path.cwd() / "projects"))
    args = parser.parse_args()
    try:
        result = scaffold_item(args.client, args.content_type, args.slug, args.run_id, Path(args.projects_root))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError) as exc:
        print(f"STOP {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
