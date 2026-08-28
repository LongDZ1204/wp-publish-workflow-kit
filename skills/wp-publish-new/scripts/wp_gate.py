#!/usr/bin/env python3
"""Fail-closed validation for prepared and final publish bundles."""

from __future__ import annotations

import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


class InventoryParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.h1_count = 0
        self.images: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        if tag.lower() == "h1":
            self.h1_count += 1
        elif tag.lower() == "img":
            self.images.append(values)


def is_local_src(src: str) -> bool:
    parsed = urlparse(src)
    return (
        src.startswith(("/Users/", "../", "./", "projects/", "file:"))
        or (not parsed.scheme and not src.startswith(("//", "data:")))
    )


def validate(bundle: Path, profile: dict, phase: str, allow_pilot: bool = False) -> dict:
    required = ["publish-request.json", "content.prepared.html", "image-manifest.json", "transform-report.json"]
    missing = [name for name in required if not (bundle / name).is_file()]
    if missing:
        raise ValueError(f"INPUT-MISSING: {missing}")
    if profile.get("ready") is not True and not (allow_pilot and profile.get("pilot_allowed") is True):
        raise ValueError("BRAND-MISSING: publish-context.json is not ready")
    html_name = "content.final.html" if phase == "final" else "content.prepared.html"
    if not (bundle / html_name).is_file():
        raise ValueError(f"INPUT-MISSING: {html_name}")
    html = (bundle / html_name).read_text(encoding="utf-8")
    manifest = json.loads((bundle / "image-manifest.json").read_text(encoding="utf-8"))
    transform = json.loads((bundle / "transform-report.json").read_text(encoding="utf-8"))
    errors: list[str] = []
    if re.search(r"\[IMAGE\s*[—-]", html, flags=re.I):
        errors.append("IMG-MISSING: unresolved image marker")
    if re.search(r"(?m)^#{1,6}\s+", html):
        errors.append("INPUT-MISSING: Markdown heading remains in HTML")
    parser = InventoryParser()
    parser.feed(html)
    expected_h1 = profile.get("body_h1_count")
    if expected_h1 is None:
        errors.append("BRAND-MISSING: body_h1_count")
    elif parser.h1_count != int(expected_h1):
        errors.append(f"VERIFY-DIFF: h1 expected={expected_h1} actual={parser.h1_count}")
    items = manifest.get("images", [])
    by_id = {str(item.get("asset_id")): item for item in items}
    if len(by_id) != len(items):
        errors.append("IMG-DUP: duplicate asset_id")
    alts: set[str] = set()
    for item in items:
        alt = str(item.get("alt", "")).strip()
        if not item.get("decorative") and not alt:
            errors.append(f"ALT-MISSING: {item.get('asset_id')}")
        if alt and alt in alts:
            errors.append(f"ALT-MISSING: duplicate alt {alt!r}")
        alts.add(alt)
    tokens = re.findall(r"asset://([A-Za-z0-9._-]+)", html)
    unknown = sorted(set(tokens) - set(by_id))
    if unknown:
        errors.append(f"IMG-MISSING: unknown asset tokens {unknown}")
    if phase == "final" and tokens:
        errors.append(f"IMG-MISSING: unresolved asset tokens {sorted(set(tokens))}")
    for image in parser.images:
        src = image.get("src", "")
        if not src:
            errors.append("IMG-MISSING: img without src")
        elif phase == "prepared" and src.startswith("asset://"):
            asset_id = src.removeprefix("asset://")
            item = by_id.get(asset_id)
            if item and image.get("alt", "").strip() != str(item.get("alt", "")).strip():
                errors.append(f"VERIFY-DIFF: HTML alt differs from manifest for {asset_id}")
        elif not src.startswith("asset://") and is_local_src(src):
            errors.append(f"IMG-MISSING: local/relative src {src}")
    total = int(transform.get("total", -1))
    converted = int(transform.get("converted", -1))
    protected = int(transform.get("protected", -1))
    if min(total, converted, protected) < 0 or total != converted + protected:
        errors.append("STRONG-DIFF: total must equal converted + protected")
    if len(parser.images) != len(items):
        errors.append(f"IMG-COUNT: html={len(parser.images)} manifest={len(items)}")
    report = {
        "version": 1,
        "phase": phase,
        "ok": not errors,
        "h1_count": parser.h1_count,
        "image_count": len(parser.images),
        "errors": errors,
    }
    (bundle / "gate-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if errors:
        raise ValueError("; ".join(errors))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--phase", choices=("prepared", "final"), required=True)
    parser.add_argument("--pilot", action="store_true", help="Allow an explicitly enabled draft-only pilot")
    args = parser.parse_args()
    try:
        profile = json.loads(Path(args.profile).read_text(encoding="utf-8"))
        report = validate(Path(args.bundle).resolve(), profile, args.phase, allow_pilot=args.pilot)
        print(f"OK phase={args.phase} images={report['image_count']} h1={report['h1_count']}")
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"STOP {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
