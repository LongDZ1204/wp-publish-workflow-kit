#!/usr/bin/env python3
"""Run the deterministic strong-to-b engine and persist a machine-readable report."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
ENGINE = ROOT / "tools" / "strong-to-b" / "strong_to_b.py"


def load_convert():
    spec = importlib.util.spec_from_file_location("strong_to_b_engine", ENGINE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {ENGINE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.convert


def atomic_write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(data)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    source = Path(args.input)
    html = source.read_text(encoding="utf-8")
    converted_html, report = load_convert()(html)
    if report["total"] != report["converted"] + report["protected"]:
        print("STOP STRONG-DIFF: report invariant failed")
        return 2
    atomic_write(Path(args.output), converted_html)
    atomic_write(Path(args.report), json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"OK total={report['total']} converted={report['converted']} protected={report['protected']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

