#!/usr/bin/env python3
"""Create a project from the visible, non-destructive project skeleton."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_ROOT = ROOT / "templates" / "project-skeleton"


def write_new(path: Path, text: str) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def render(text: str, client: str) -> str:
    title = client.replace("-", " ").title()
    return text.replace("__CLIENT_SLUG__", client).replace("__CLIENT_TITLE__", title)


def scaffold(client: str, projects_root: Path, template_root: Path = TEMPLATE_ROOT) -> dict:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", client):
        raise ValueError("INPUT-MISSING: client must be a kebab-case slug")
    if not template_root.is_dir():
        raise ValueError(f"TEMPLATE-MISSING: project skeleton not found: {template_root}")

    projects_root = projects_root.resolve()
    project = projects_root.resolve() / client
    created: list[str] = []
    template_files = sorted(path for path in template_root.rglob("*") if path.is_file())
    for source in template_files:
        relative = source.relative_to(template_root)
        target = project / relative
        text = render(source.read_text(encoding="utf-8"), client)
        if write_new(target, text):
            created.append(str(target.relative_to(projects_root)))

    legacy = project / "knowledge" / "publish-context.json"
    return {
        "project": str(project),
        "created": created,
        "preserved": len(template_files) - len(created),
        "context_status": (
            "created-needs-confirmation"
            if str(Path(client) / "context.md") in created
            else "preserved"
        ),
        "legacy_publish_context": str(legacy) if legacy.exists() else None,
    }


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
