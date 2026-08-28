#!/usr/bin/env python3
"""B2 — Áp edit lên HTML live. Mỗi edit PHẢI khớp đúng 1 lần, sai là dừng (không push mù).

Cốt lõi an toàn: sửa string-replace TRÊN CHÍNH content.raw, KHÔNG regenerate từ markdown
(regenerate làm vỡ table / [caption] / iframe embed / shortcode).

edits.json:
[
  {"label": "mô tả ngắn", "old": "chuỗi cũ khớp đúng 1 lần", "new": "chuỗi mới"},
  ...
]
- new == "" nghĩa là XÓA (dùng cho câu bridge lặp). old vẫn phải khớp đúng 1 lần.
- Thứ tự áp = thứ tự trong file (một edit có thể tạo/hủy match của edit sau — sắp cho đúng).

frozen.json (optional): ["chuỗi vùng khóa 1", ...] — mỗi chuỗi phải CÒN NGUYÊN sau khi áp.

Usage:
  python3 wp_apply_edits.py --html in.raw.html --edits edits.json --out new.html [--frozen frozen.json] [--dry-run]

--dry-run: chỉ kiểm match-count, KHÔNG ghi file. Luôn chạy dry-run trước khi ghi thật.
Exit 1 nếu bất kỳ edit nào không khớp đúng 1 lần, hoặc vùng khóa bị mất.
"""
import argparse
import json
import re
import sys


def h1_count(html):
    return len(re.findall(r"<h1\b", html, flags=re.IGNORECASE))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", required=True)
    ap.add_argument("--edits", required=True)
    ap.add_argument("--out")
    ap.add_argument("--frozen")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    raw = open(a.html, encoding="utf-8").read()
    edits = json.load(open(a.edits, encoding="utf-8"))
    orig_len = len(raw)

    fails, applied = [], []
    for i, e in enumerate(edits):
        old, new, label = e["old"], e.get("new", ""), e.get("label", f"edit#{i}")
        c = raw.count(old)
        if c != 1:
            fails.append((label, c))
            continue
        raw = raw.replace(old, new, 1)
        applied.append((label, "DELETE" if new == "" else ("ADD" if old in new else "EDIT")))

    if fails:
        print("!!! DỪNG — edit không khớp đúng 1 lần (0=không thấy, >1=lệch/nhân bản):")
        for l, c in fails:
            print(f"   [{c}x] {l}")
        print("\nSửa lại chuỗi `old` cho khớp đúng 1 lần rồi chạy lại. KHÔNG push.")
        sys.exit(1)

    # frozen check
    lost = []
    if a.frozen:
        for f in json.load(open(a.frozen, encoding="utf-8")):
            if raw.count(f) < 1:
                lost.append(f[:60])
    if lost:
        print("!!! DỪNG — vùng khóa bị mất sau khi áp:")
        for f in lost:
            print(f"   LOST: {f}")
        sys.exit(1)

    count = h1_count(raw)
    if count != 1:
        print(f"!!! DỪNG — HTML sau edit phải có đúng 1 H1; hiện có {count}.")
        sys.exit(1)

    print(f"OK — {len(applied)}/{len(edits)} edit khớp đúng 1 lần. "
          f"Length {orig_len} -> {len(raw)} ({len(raw)-orig_len:+d}).")
    print(f"Cấu trúc giữ nguyên: h1={count} tables={raw.count('<table')} imgs={raw.count('<img')} iframes={raw.count('<iframe')}")
    for l, kind in applied:
        print(f"   [{kind}] {l}")
    if a.frozen:
        print(f"Vùng khóa: {len(json.load(open(a.frozen)))} chuỗi CÒN NGUYÊN.")

    if a.dry_run:
        print("\n[dry-run] KHÔNG ghi file. Chạy lại bỏ --dry-run để ghi bản mới.")
        return
    if not a.out:
        sys.exit("ERR: cần --out khi ghi thật (hoặc dùng --dry-run).")
    open(a.out, "w", encoding="utf-8").write(raw)
    print(f"\nĐã ghi: {a.out}")


if __name__ == "__main__":
    main()
