#!/usr/bin/env python3
"""Deterministic image preparation with immutable sources and a JSON manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover - environment guard
    raise SystemExit("Pillow is required: python3 -m pip install Pillow") from exc


VALID_MODES = {"prepare-new", "audit-existing"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def validate_item(item: dict) -> None:
    if not item.get("asset_id"):
        raise ValueError("IMG-MISSING: asset_id")
    if not item.get("source") and not item.get("existing_url"):
        raise ValueError(f"IMG-MISSING: {item['asset_id']} has no source/existing_url")
    if not item.get("decorative") and not str(item.get("alt", "")).strip():
        raise ValueError(f"ALT-MISSING: {item['asset_id']}")
    if item.get("decorative") and item.get("alt") not in (None, ""):
        raise ValueError(f"ALT-MISSING: decorative {item['asset_id']} must use empty alt")


def target_name(item: dict, source: Path, policy: str) -> str:
    requested = item.get("filename")
    stem = slugify(Path(requested).stem if requested else (item.get("alt") or item.get("heading") or item["asset_id"]))
    if not stem:
        raise ValueError(f"IMG-MISSING: cannot derive semantic filename for {item['asset_id']}")
    if policy == "webp":
        ext = ".webp"
    else:
        ext = Path(requested).suffix.lower() if requested and Path(requested).suffix else source.suffix.lower()
        if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
            raise ValueError(f"IMG-MISSING: unsupported extension {ext}")
        if ext == ".jpeg":
            ext = ".jpg"
    return stem + ext


def _save_candidate(image: Image.Image, path: Path, ext: str, quality: int, max_width: int) -> tuple[int, int]:
    work = image.copy()
    if max_width and work.width > max_width:
        height = round(work.height * max_width / work.width)
        work.thumbnail((max_width, height), Image.Resampling.LANCZOS)
    kwargs = {"optimize": True}
    if ext in {".jpg", ".jpeg"}:
        if work.mode not in {"RGB", "L"}:
            work = work.convert("RGB")
        kwargs.update(quality=quality, progressive=True)
        fmt = "JPEG"
    elif ext == ".webp":
        kwargs.update(quality=quality, method=6)
        fmt = "WEBP"
    else:
        fmt = "PNG"
    work.save(path, format=fmt, **kwargs)
    return work.width, work.height


def process_image(source: Path, target: Path, max_kb: int, max_width: int) -> dict:
    if not source.is_file():
        raise ValueError(f"IMG-MISSING: {source}")
    if target.exists():
        raise ValueError(f"IMG-DUP: output exists {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    ext = target.suffix.lower()
    with Image.open(source) as image:
        original_width, original_height = image.size
        qualities = [88, 82, 76, 70, 64, 58, 52] if ext in {".jpg", ".jpeg", ".webp"} else [88]
        fd, tmp_name = tempfile.mkstemp(prefix=target.stem + ".", suffix=ext, dir=target.parent)
        os.close(fd)
        tmp = Path(tmp_name)
        try:
            final_width = final_height = 0
            for quality in qualities:
                final_width, final_height = _save_candidate(image, tmp, ext, quality, max_width)
                if tmp.stat().st_size <= max_kb * 1024:
                    break
            if tmp.stat().st_size > max_kb * 1024:
                raise ValueError(f"IMG-SIZE: {source} remains {tmp.stat().st_size} bytes above {max_kb}KB")
            os.replace(tmp, target)
        finally:
            if tmp.exists():
                tmp.unlink()
    return {
        "original_width": original_width, "original_height": original_height,
        "final_width": final_width, "final_height": final_height,
        "before_bytes": source.stat().st_size, "after_bytes": target.stat().st_size,
        "source_sha256": sha256(source), "output_sha256": sha256(target),
    }


def prepare(request: dict, mode: str, output_dir: Path) -> dict:
    if mode not in VALID_MODES:
        raise ValueError(f"unsupported mode {mode}")
    profile = request.get("profile") or {}
    policy = profile.get("format_policy", "preserve")
    if policy not in {"preserve", "webp"}:
        raise ValueError("format_policy must be preserve or webp")
    max_kb = int(profile.get("max_kb", 150))
    max_width = int(profile.get("max_width", 1200))
    items = []
    seen_alt = set()
    seen_names = set()
    for raw in request.get("images", []):
        item = dict(raw)
        validate_item(item)
        alt = str(item.get("alt", "")).strip()
        if alt and alt in seen_alt:
            raise ValueError(f"ALT-MISSING: duplicate alt {alt!r}")
        seen_alt.add(alt)
        preserve = mode == "audit-existing" and item.get("existing_url") and not item.get("approved_replace")
        record = {
            "asset_id": item["asset_id"], "heading": item.get("heading", ""),
            "alt": alt, "caption": item.get("caption", ""),
            "decorative": bool(item.get("decorative")), "existing_url": item.get("existing_url"),
        }
        if preserve:
            record.update(action="preserve-existing", status="ready")
            items.append(record)
            continue
        source = Path(item["source"]).expanduser().resolve()
        name = target_name(item, source, policy)
        if name in seen_names:
            raise ValueError(f"IMG-DUP: duplicate output filename {name}")
        seen_names.add(name)
        target = output_dir / name
        metrics = process_image(source, target, max_kb, max_width)
        record.update(
            action="prepare-upload", status="ready", source=str(source), output=str(target.resolve()), filename=name,
            **metrics,
        )
        items.append(record)
    return {"version": 1, "mode": mode, "profile": profile, "images": items}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=sorted(VALID_MODES), required=True)
    ap.add_argument("--request", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--manifest", required=True)
    args = ap.parse_args()
    request = json.loads(Path(args.request).read_text(encoding="utf-8"))
    manifest = prepare(request, args.mode, Path(args.output_dir))
    out = Path(args.manifest)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    prepared = sum(1 for x in manifest["images"] if x["action"] == "prepare-upload")
    preserved = len(manifest["images"]) - prepared
    print(f"OK images={len(manifest['images'])} prepared={prepared} preserved={preserved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
