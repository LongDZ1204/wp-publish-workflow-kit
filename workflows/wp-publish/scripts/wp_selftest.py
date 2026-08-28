#!/usr/bin/env python3
"""Structural self-test: every operational component is wired into the workflow."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WF = ROOT / "workflows" / "wp-publish"


def main() -> int:
    required = [
        WF / "CLAUDE.md", WF / "AGENTS.md", WF / "learning-index.json", WF / "learnings.md",
        WF / "references" / "bundle-contract.md", WF / "references" / "sheet-schema.md",
        WF / "references" / "state-machine.md", WF / "references" / "error-codes.md",
        WF / "references" / "brand-publish-context.md", WF / "references" / "learning-policy.md",
        WF / "references" / "project-folders.md",
        ROOT / "skills" / "wp-publish-new" / "SKILL.md",
        ROOT / "skills" / "wp-rest-publish" / "SKILL.md",
        ROOT / "skills" / "image-onpage" / "SKILL.md",
        ROOT / "skills" / "strong-to-b" / "SKILL.md",
    ]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
    text = (WF / "CLAUDE.md").read_text(encoding="utf-8")
    orphan_scripts = [p.name for p in (WF / "scripts").glob("*.py") if p.name not in text]
    learn_size = (WF / "learnings.md").stat().st_size
    if missing or orphan_scripts or learn_size > 15 * 1024:
        if missing:
            print("MISSING:", ", ".join(missing))
        if orphan_scripts:
            print("ORPHAN SCRIPTS:", ", ".join(orphan_scripts))
        if learn_size > 15 * 1024:
            print("LEARNINGS TOO LARGE:", learn_size)
        return 2
    print(f"OK required={len(required)} scripts={len(list((WF / 'scripts').glob('*.py')))} learnings={learn_size}B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
