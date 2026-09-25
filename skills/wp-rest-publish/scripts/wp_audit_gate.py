#!/usr/bin/env python3
"""Check an AUDIT bundle against its fresh backup and approved change plan."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path


COUNTS = ("h1", "h2", "h3", "table", "img", "iframe")


class Inventory(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.counts = {name: 0 for name in COUNTS}
        self.images: list[str] = []
        self.links: list[tuple[str, str]] = []
        self._active_link: tuple[str, list[str]] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        values = dict(attrs)
        if tag in self.counts:
            self.counts[tag] += 1
        if tag == "img" and values.get("src"):
            self.images.append(str(values["src"]))
        if tag == "a" and values.get("href"):
            self._active_link = (str(values["href"]), [])

    def handle_data(self, data: str) -> None:
        if self._active_link is not None:
            self._active_link[1].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._active_link is not None:
            href, parts = self._active_link
            self.links.append((href, " ".join("".join(parts).split())))
            self._active_link = None


def inventory(html: str, image_manifest: dict | None = None) -> Inventory:
    parsed = Inventory()
    parsed.feed(html)
    for item in (image_manifest or {}).get("images", []):
        token = f"asset://{item.get('asset_id')}"
        if token in parsed.images and item.get("existing_url"):
            parsed.images = [str(item["existing_url"]) if src == token else src for src in parsed.images]
    return parsed


def check(bundle: Path) -> dict:
    request = json.loads((bundle / "publish-request.json").read_text(encoding="utf-8"))
    plan = json.loads((bundle / "audit-plan.json").read_text(encoding="utf-8"))
    manifest = json.loads((bundle / "image-manifest.json").read_text(encoding="utf-8"))
    if request.get("task_type") != "AUDIT" or request.get("update_mode") not in {"MINIMAL_DIFF", "REBUILD"}:
        raise ValueError("ROUTE-CONFLICT: explicit AUDIT update_mode is required")
    if plan.get("update_mode") != request["update_mode"]:
        raise ValueError("ROUTE-CONFLICT: audit plan mode differs from request")
    backup = Path(str(request.get("backup_path", "")))
    if not backup.is_file():
        raise ValueError("INPUT-MISSING: immutable AUDIT backup")
    original = backup.read_text(encoding="utf-8")
    if hashlib.sha256(original.encode("utf-8")).hexdigest() != request.get("wp_raw_sha256_at_fetch"):
        raise ValueError("SOURCE-STALE: AUDIT backup differs from approved snapshot")
    prepared = (bundle / "content.prepared.html").read_text(encoding="utf-8")
    old, new = inventory(original), inventory(prepared, manifest)
    delta = {name: new.counts[name] - old.counts[name] for name in COUNTS}
    expected = plan.get("expected_structure_delta")
    if not isinstance(expected, dict) or set(expected) != set(COUNTS):
        raise ValueError("INPUT-MISSING: expected_structure_delta must list h1/h2/h3/table/img/iframe")
    if any(type(expected[name]) is not int for name in COUNTS) or delta != expected:
        raise ValueError(f"VERIFY-DIFF: structure delta expected={expected} actual={delta}")
    removed_images = sorted((Counter(old.images) - Counter(new.images)).elements())
    removed_links = sorted((Counter(old.links) - Counter(new.links)).elements())
    removed_link_records = [{"href": href, "anchor": anchor} for href, anchor in removed_links]
    approved_images = plan.get("approved_removed_image_urls")
    approved_links = plan.get("approved_removed_links")
    if not isinstance(approved_images, list) or any(not isinstance(value, str) for value in approved_images):
        raise ValueError("INPUT-MISSING: approved_removed_image_urls must be a list")
    if not isinstance(approved_links, list) or any(
        not isinstance(row, dict) or not isinstance(row.get("href"), str)
        or not isinstance(row.get("anchor"), str) for row in approved_links
    ):
        raise ValueError("INPUT-MISSING: approved_removed_links must list href and anchor")
    if removed_images != sorted(approved_images):
        raise ValueError(f"VERIFY-DIFF: removed images need exact approval {removed_images}")
    if removed_link_records != sorted(approved_links, key=lambda row: (row["href"], row["anchor"])):
        raise ValueError(f"VERIFY-DIFF: removed links/anchors need exact approval {removed_link_records}")
    keep = plan.get("keep_passages", [])
    if not isinstance(keep, list) or any(not isinstance(item, str) or item not in original or item not in prepared for item in keep):
        raise ValueError("VERIFY-DIFF: frozen passage missing from backup or prepared HTML")
    if request["update_mode"] == "REBUILD":
        if not str(plan.get("rebuild_reason", "")).strip():
            raise ValueError("INPUT-MISSING: REBUILD needs an approved reason")
    else:
        edits = plan.get("edits")
        if not isinstance(edits, list) or not edits:
            raise ValueError("INPUT-MISSING: MINIMAL_DIFF needs exact edits")
        for edit in edits:
            before, after = edit.get("old"), edit.get("new")
            if not isinstance(before, str) or not before or not isinstance(after, str):
                raise ValueError("INPUT-MISSING: each edit needs old and new text")
            if original.count(before) != 1 or (after and after not in prepared):
                raise ValueError("VERIFY-DIFF: edit does not match original once or prepared output")
    return {
        "version": 1,
        "ok": True,
        "post_id": int(request["post_id"]),
        "update_mode": request["update_mode"],
        "backup_sha256": request["wp_raw_sha256_at_fetch"],
        "prepared_sha256": hashlib.sha256(prepared.encode("utf-8")).hexdigest(),
        "structure_delta": delta,
        "removed_image_urls": removed_images,
        "removed_links": removed_link_records,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True)
    args = parser.parse_args()
    bundle = Path(args.bundle).resolve()
    try:
        report = check(bundle)
        (bundle / "audit-gate-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"OK AUDIT {report['update_mode']} post_id={report['post_id']}")
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"STOP {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
