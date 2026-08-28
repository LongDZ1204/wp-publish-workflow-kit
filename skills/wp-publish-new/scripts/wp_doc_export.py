#!/usr/bin/env python3
"""Convert a Google Docs HTML ZIP into clean WordPress HTML and an image request."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from bs4 import BeautifulSoup, NavigableString, Tag


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_member(name: str) -> str:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"INPUT-MISSING: unsafe ZIP member {name}")
    return str(path)


def clean_inline(source, target_soup: BeautifulSoup):
    if isinstance(source, NavigableString):
        return NavigableString(str(source).replace("\u00a0", " "))
    if not isinstance(source, Tag):
        return None
    name = source.name.lower()
    style = source.get("style", "").lower()
    if name == "br":
        return target_soup.new_tag("br")
    if name == "a":
        tag = target_soup.new_tag("a", href=source.get("href", ""))
    elif name in {"strong", "b"} or re.search(r"font-weight\s*:\s*(700|bold)", style):
        tag = target_soup.new_tag("strong")
    elif name in {"em", "i"} or "font-style:italic" in style.replace(" ", ""):
        tag = target_soup.new_tag("em")
    elif name == "code" or "roboto mono" in style:
        tag = target_soup.new_tag("code")
    else:
        tag = target_soup.new_tag("span")
    for child in source.children:
        cleaned = clean_inline(child, target_soup)
        if cleaned is not None:
            tag.append(cleaned)
    if tag.name == "span":
        return list(tag.contents)
    return tag


def append_inline_children(target: Tag, source: Tag, soup: BeautifulSoup) -> None:
    for child in source.children:
        cleaned = clean_inline(child, soup)
        if isinstance(cleaned, list):
            for item in cleaned:
                target.append(item)
        elif cleaned is not None:
            target.append(cleaned)


def image_figure(source: Tag, soup: BeautifulSoup, mapping_by_path: dict[str, dict]) -> Tag:
    image = source.find("img")
    src = safe_member(str(image.get("src", "")))
    item = mapping_by_path.get(src)
    if not item:
        raise ValueError(f"IMG-MISSING: no mapping for {src}")
    figure = soup.new_tag("figure")
    img = soup.new_tag("img", src=f"asset://{item['asset_id']}", alt=item.get("alt", ""))
    figure.append(img)
    caption = str(item.get("caption", "")).strip()
    if caption:
        figcaption = soup.new_tag("figcaption")
        figcaption.string = caption
        figure.append(figcaption)
    return figure


def clean_block(source: Tag, soup: BeautifulSoup, mapping_by_path: dict[str, dict]):
    name = source.name.lower()
    if name == "p" and source.find("img"):
        return image_figure(source, soup, mapping_by_path)
    if name == "p" and "title" in source.get("class", []):
        return None
    if name in {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "th", "td"}:
        tag = soup.new_tag(name)
        append_inline_children(tag, source, soup)
        return tag if tag.get_text(strip=True) else None
    if name in {"ul", "ol", "table", "thead", "tbody", "tfoot", "tr"}:
        tag = soup.new_tag(name)
        for child in source.children:
            if isinstance(child, Tag):
                cleaned = clean_block(child, soup, mapping_by_path)
                if cleaned is not None:
                    tag.append(cleaned)
        return tag if tag.contents else None
    return None


def convert(zip_path: Path, mapping: dict) -> tuple[str, dict]:
    with zipfile.ZipFile(zip_path) as archive:
        html_names = [name for name in archive.namelist() if name.lower().endswith(".html")]
        if len(html_names) != 1:
            raise ValueError(f"INPUT-MISSING: expected one HTML file, got {len(html_names)}")
        raw = archive.read(html_names[0]).decode("utf-8")
        source = BeautifulSoup(raw, "html.parser")
        output = BeautifulSoup("", "html.parser")
        items = mapping.get("images", [])
        mapping_by_path = {safe_member(str(item["zip_path"])): item for item in items}
        found_paths = {safe_member(str(img.get("src", ""))) for img in source.find_all("img")}
        if found_paths != set(mapping_by_path):
            raise ValueError(f"IMG-COUNT: HTML={sorted(found_paths)} mapping={sorted(mapping_by_path)}")
        body = source.body
        if body is None:
            raise ValueError("INPUT-MISSING: exported HTML has no body")
        for child in body.children:
            if isinstance(child, Tag):
                cleaned = clean_block(child, output, mapping_by_path)
                if cleaned is not None:
                    output.append(cleaned)
        extracted = []
        for item in items:
            member = safe_member(str(item["zip_path"]))
            data = archive.read(member)
            destination = Path(item["source_output"]).expanduser().resolve()
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists() and digest(destination.read_bytes()) != digest(data):
                raise ValueError(f"IMG-DUP: different file already exists at {destination}")
            if not destination.exists():
                fd, temp_name = tempfile.mkstemp(prefix=destination.name + ".", dir=destination.parent)
                try:
                    with os.fdopen(fd, "wb") as handle:
                        handle.write(data)
                    os.replace(temp_name, destination)
                finally:
                    if os.path.exists(temp_name):
                        os.unlink(temp_name)
            record = {key: value for key, value in item.items() if key not in {"zip_path", "source_output"}}
            record["source"] = str(destination)
            extracted.append(record)
    html = "".join(str(node) for node in output.contents).strip() + "\n"
    request = {"profile": mapping.get("profile", {}), "images": extracted}
    return html, request


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", required=True)
    parser.add_argument("--mapping", required=True)
    parser.add_argument("--html-out", required=True)
    parser.add_argument("--image-request-out", required=True)
    args = parser.parse_args()
    try:
        mapping = json.loads(Path(args.mapping).read_text(encoding="utf-8"))
        html, request = convert(Path(args.zip), mapping)
        Path(args.html_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.html_out).write_text(html, encoding="utf-8")
        Path(args.image_request_out).write_text(json.dumps(request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"OK html_chars={len(html)} images={len(request['images'])}")
        return 0
    except (ValueError, OSError, KeyError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print(f"STOP {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

