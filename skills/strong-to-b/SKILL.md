---
name: strong-to-b
description: Deterministically convert body-level HTML strong elements to b while preserving strong inside headings and links, including a link nested inside strong. Use when preparing WordPress HTML and the site reserves strong for headings and anchors.
---

# Strong to b

This is a deterministic HTML transformation. Always run the bundled engine; do not perform the
conversion manually or with free-form text generation.

## Preserve `<strong>` when

- It has an `h1`–`h6` ancestor.
- It has an `a` ancestor.
- It contains an `a` descendant.

Convert every other `<strong>` pair to `<b>` while preserving attributes, case, whitespace, raw
script/style/comment content, and all bytes outside the tag names.

## Commands

```bash
python3 tools/strong-to-b/strong_to_b.py article.html
python3 tools/strong-to-b/strong_to_b.py article.html -o prepared.html
python3 tools/strong-to-b/strong_to_b.py article.html --report-only
```

For standard input:

```bash
python3 tools/strong-to-b/strong_to_b.py < article.html > prepared.html
```

The report must reconcile: total found = converted + preserved. Re-running the engine must produce
no further changes.
