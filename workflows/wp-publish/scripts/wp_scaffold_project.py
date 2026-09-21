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


def profile(endpoint: str, post_type: str, html_policy: str, capabilities: list[str]) -> dict:
    return {
        "endpoint": endpoint,
        "post_type": post_type,
        "ready": False,
        "body_h1_count": None,
        "html_policy": html_policy,
        "required_fields": ["title", "content", "slug"],
        "required_capabilities": capabilities,
        "image_policy": {"format_policy": "preserve", "max_kb": 150, "max_width": 1200},
        "seo_meta_adapter": None,
        "schema_hash": None,
    }


def scaffold(client: str, projects_root: Path) -> dict:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", client):
        raise ValueError("INPUT-MISSING: client must be a kebab-case slug")
    project = projects_root.resolve() / client
    if not (project / "context.md").is_file():
        raise ValueError("BRAND-MISSING: create and approve project context.md first")
    directories = [
        project / "content/blog",
        project / "content/service-page",
        project / "content/product",
        project / "scans",
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    created = []
    files = {
        project / "content/blog/.gitkeep": "\n",
        project / "content/service-page/.gitkeep": "\n",
        project / "content/product/.gitkeep": "\n",
        project / "scans/.gitkeep": "\n",
        project / "publish-context.md": (
            f"# {client} publish context\n\n"
            "Site-specific decisions for workflow `wp-publish`. Keep brand/business facts in "
            "`context.md`. After the read-only site scan, confirm fields, body H1 ownership, HTML "
            "policy, SEO adapter and permissions for each content type before setting it ready.\n"
        ),
        project / "publish-context.json": json.dumps({
            "version": 2,
            "site_key": client,
            "tracker": {"type": "none"},
            "pilot_allowed": False,
            "content_profiles": {
                "blog": profile("posts", "post", "clean_article", ["edit_posts", "upload_files"]),
                "service-page": profile("pages", "page", "preserve_builder", ["edit_pages", "upload_files"]),
                "product": profile("product", "product", "preserve_builder", ["edit_products", "upload_files"]),
            },
            "timezone": "UTC",
            "notes": "Run wp_site_scan.py, then confirm one profile at a time before enabling writes.",
        }, ensure_ascii=False, indent=2) + "\n",
    }
    for path, text in files.items():
        if write_new(path, text):
            created.append(str(path.relative_to(projects_root.resolve())))
    legacy = project / "knowledge" / "publish-context.json"
    return {
        "project": str(project),
        "created": created,
        "preserved": len(files) - len(created),
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
