#!/usr/bin/env python3
"""Create non-destructive wp-publish folders and fail-closed site context templates."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def write_new(path: Path, text: str) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def scaffold(client: str, projects_root: Path) -> dict:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", client):
        raise ValueError("INPUT-MISSING: client must be a kebab-case slug")
    project = projects_root.resolve() / client
    if not (project / "context.md").is_file():
        raise ValueError("BRAND-MISSING: create and approve project context.md first")
    directories = [
        project / "content/06-assets",
        project / "content/07-publish-ready",
        project / "content/_audit-snapshots",
        project / "content/_inbox",
        project / "knowledge",
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    created = []
    files = {
        project / "content/07-publish-ready/.gitkeep": "\n",
        project / "content/_audit-snapshots/.gitkeep": "\n",
        project / "content/_inbox/.gitignore": "*\n!.gitignore\n",
        project / "knowledge/publish-context.md": (
            f"# {client} publish context\n\n"
            "Site-specific decisions for workflow `wp-publish`. Keep brand/business facts in "
            "`../context.md`. Confirm REST, Sheet/tab, body H1 ownership, SEO meta adapter and a media "
            "round-trip before enabling writes.\n"
        ),
        project / "knowledge/publish-context.json": json.dumps({
            "version": 1,
            "site_key": client,
            "ready": False,
            "pilot_allowed": False,
            "body_h1_count": None,
            "format_policy": "preserve",
            "max_kb": 150,
            "max_width": 1200,
            "seo_meta_adapter": None,
            "spreadsheet_id": None,
            "sheet_tab": None,
            "timezone": "UTC",
            "notes": "Confirm integrations before setting ready=true.",
        }, ensure_ascii=False, indent=2) + "\n",
    }
    for path, text in files.items():
        if write_new(path, text):
            created.append(str(path.relative_to(projects_root.resolve())))
    return {"project": str(project), "created": created, "preserved": len(files) - len(created)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--client", required=True)
    parser.add_argument("--projects-root", default=str(Path.cwd() / "projects"))
    args = parser.parse_args()
    try:
        result = scaffold(args.client, Path(args.projects_root))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError) as exc:
        print(f"STOP {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
