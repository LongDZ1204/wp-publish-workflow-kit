#!/usr/bin/env python3
"""Validate and normalize one wp-publish Sheet row without network access."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ALIASES = {
    "Row ID": "row_id",
    "Bài / Title": "title",
    "Loại bài": "task_type",
    "Nguồn content": "source_ref",
    "Slug / URL WP": "slug_or_target",
    "Ngày public dự kiến": "planned_publish_at",
    "Trạng thái": "workflow_status",
    "URL draft/live": "draft_live_url",
    "Note": "note",
    "Cập nhật lúc": "updated_at",
    # Legacy aliases remain readable so old exports can be migrated safely.
    "Client": "client",
    "Site key": "site_key",
    "Task type": "task_type",
    "Update mode": "update_mode",
    "Content source": "source_ref",
    "Source type": "source_type",
    "Slug": "slug",
    "Target URL": "target_url",
    "Post ID": "post_id",
    "Title": "title",
    "Meta description": "meta_description",
    "Category IDs": "category_ids",
    "Tag IDs": "tag_ids",
    "Featured asset": "featured_asset_id",
    "Internal-link plan": "internal_link_plan",
    "Planned publish at": "planned_publish_at",
    "Run ID": "run_id",
}


class ContractError(ValueError):
    pass


def _nonempty(value) -> bool:
    return value is not None and (not isinstance(value, str) or bool(value.strip()))


def normalize(row: dict) -> dict:
    out = {}
    for key, value in row.items():
        canonical = ALIASES.get(key, key)
        out[canonical] = value.strip() if isinstance(value, str) else value

    task = str(out.get("task_type", "")).upper()
    if task in {"VIẾT MỚI", "Viet moi".upper(), "NEW_POST"}:
        task = "NEW"
    if task in {"CẬP NHẬT", "AUDIT/CẬP NHẬT", "UPDATE", "EXISTING"}:
        task = "AUDIT"
    out["task_type"] = task

    locator = out.pop("slug_or_target", None)
    if _nonempty(locator):
        if task == "NEW" and not _nonempty(out.get("slug")):
            out["slug"] = locator
        elif task == "AUDIT" and not _nonempty(out.get("target_url")):
            out["target_url"] = locator

    if out.get("update_mode"):
        out["update_mode"] = str(out["update_mode"]).upper().replace("-", "_")

    source_ref = str(out.get("source_ref", ""))
    if not out.get("source_type") and source_ref:
        out["source_type"] = "google_doc" if "docs.google.com" in source_ref else "local_markdown"
    return out


def validate(row: dict) -> dict:
    row = normalize(row)
    missing = [k for k in ("row_id", "task_type", "source_ref", "title") if not _nonempty(row.get(k))]
    if missing:
        raise ContractError("INPUT-MISSING: " + ", ".join(missing))
    if row["task_type"] not in {"NEW", "AUDIT"}:
        raise ContractError("INPUT-MISSING: task_type must be NEW or AUDIT")
    if row["task_type"] == "NEW" and not _nonempty(row.get("slug")):
        raise ContractError("INPUT-MISSING: slug is required for NEW")
    if row["task_type"] == "AUDIT":
        if not (_nonempty(row.get("target_url")) or _nonempty(row.get("post_id"))):
            raise ContractError("INPUT-MISSING: target_url or post_id is required for AUDIT")
        if row.get("update_mode") and row["update_mode"] not in {"MINIMAL_DIFF", "REBUILD"}:
            raise ContractError("INPUT-MISSING: invalid legacy update_mode")
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="input_path", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    try:
        row = validate(json.loads(Path(args.input_path).read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, ContractError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK row_id={row['row_id']} task_type={row['task_type']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
