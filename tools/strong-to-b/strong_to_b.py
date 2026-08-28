#!/usr/bin/env python3
"""
strong_to_b — Đổi <strong> thành <b>, GIỮ NGUYÊN các thẻ <strong> trong vùng cấm.

Vùng cấm (Protected Zones):
  - Heading: <h1>..<h6>  (strong nằm TRONG heading)
  - Link:    <a>         (strong nằm TRONG link, HOẶC link <a> nằm TRONG strong)

Triết lý: phép biến đổi XÁC ĐỊNH, không "sáng tạo".
Engine tokenize HTML rồi CHỈ splice đúng byte của thẻ <strong>/</strong> cần đổi —
mọi ký tự khác (attribute, xuống dòng, thẻ HOA, <b> có sẵn, nội dung <script>/<style>/
comment) giữ NGUYÊN 100%.

Dùng:
  # mode paste (stdin -> stdout)
  echo '<p><strong>x</strong></p>' | python3 strong_to_b.py

  # mode file (ghi ra scratch/outputs/ theo mặc định, giữ bản gốc)
  python3 strong_to_b.py bai-viet.html
  python3 strong_to_b.py bai-viet.html -o /duong/dan/ket-qua.html

  # chỉ xem báo cáo, không xuất HTML
  python3 strong_to_b.py bai-viet.html --report-only
"""
import argparse
import os
import re
import sys

PROTECT_ANCESTORS = {"h1", "h2", "h3", "h4", "h5", "h6", "a"}
HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
RAW_ELEMENTS = {"script", "style", "textarea"}
# Thẻ rỗng (void) — không bao giờ có nội dung con, không đẩy vào stack.
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr"}

# Khớp 1 thẻ: nhóm1=dấu '/' đóng, nhóm2=tên thẻ, nhóm3=phần attribute, nhóm4=dấu '/' self-close.
# Attribute cho phép value có dấu nháy chứa '>' -> không cắt nhầm.
_TAG_RE = re.compile(
    r'<(/?)([a-zA-Z][a-zA-Z0-9:_-]*)((?:[^<>"\']|"[^"]*"|\'[^\']*\')*?)(/?)\s*>',
    re.S,
)
_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
_CDATA_RE = re.compile(r"<!\[CDATA\[.*?\]\]>", re.S)
_DECL_RE = re.compile(r"<![^>]*>", re.S)


def _tokenize(html):
    """Chia html thành list token (kind, text, tagname).

    kind: 'text' | 'raw' | 'comment' | 'cdata' | 'decl'
        | 'start' | 'end' | 'selfclose'
    Nối text mọi token lại = html gốc (bất biến).
    """
    tokens = []
    i, n = 0, len(html)
    while i < n:
        c = html[i]
        if c != "<":
            j = html.find("<", i + 1)
            if j == -1:
                j = n
            tokens.append(("text", html[i:j], None))
            i = j
            continue

        # c == '<'
        if html.startswith("<!--", i):
            m = _COMMENT_RE.match(html, i)
            if m:
                tokens.append(("comment", m.group(0), None))
                i = m.end()
                continue
        if html[i:i + 9].upper() == "<![CDATA[":
            m = _CDATA_RE.match(html, i)
            if m:
                tokens.append(("cdata", m.group(0), None))
                i = m.end()
                continue
        if html.startswith("<!", i):
            m = _DECL_RE.match(html, i)
            if m:
                tokens.append(("decl", m.group(0), None))
                i = m.end()
                continue

        m = _TAG_RE.match(html, i)
        if not m:
            # '<' lẻ, không phải thẻ hợp lệ -> coi như text 1 ký tự
            tokens.append(("text", "<", None))
            i += 1
            continue

        tagname = m.group(2).lower()
        is_close = m.group(1) == "/"
        is_self = m.group(4) == "/"
        tag_text = m.group(0)

        if (not is_close) and (not is_self) and tagname in RAW_ELEMENTS:
            # Nuốt trọn nội dung raw tới thẻ đóng tương ứng -> không parse <strong> bên trong.
            close_re = re.compile(r"</" + re.escape(tagname) + r"\s*>", re.I)
            cm = close_re.search(html, m.end())
            end = cm.end() if cm else n
            tokens.append(("raw", html[i:end], tagname))
            i = end
            continue

        if is_close:
            kind = "end"
        elif is_self or tagname in VOID:
            kind = "selfclose"
        else:
            kind = "start"
        tokens.append((kind, tag_text, tagname))
        i = m.end()
    return tokens


def convert(html):
    """Đổi <strong>->​<b> ngoài vùng cấm. Trả (new_html, report)."""
    report = {"total": 0, "converted": 0, "protected": 0,
              "protected_heading": 0, "protected_link": 0}
    if not html:
        return "", report

    tokens = _tokenize(html)
    out = [t[1] for t in tokens]  # bản sao text để ghi đè tại chỗ

    open_a = 0          # số <a> tổ tiên đang mở
    open_heading = 0    # số heading tổ tiên đang mở
    # mỗi strong đang mở: dict {open_idx, prot(bool), reason('heading'|'link'|None)}
    pending = []

    for idx, (kind, text, tag) in enumerate(tokens):
        if kind == "start":
            if tag == "strong":
                report["total"] += 1
                if open_heading > 0:
                    reason = "heading"
                elif open_a > 0:
                    reason = "link"
                else:
                    reason = None
                pending.append({"open_idx": idx,
                                "prot": reason is not None,
                                "reason": reason})
            elif tag == "a":
                for p in pending:           # link nằm trong các strong đang mở -> bảo vệ
                    p["prot"] = True
                    if p["reason"] is None:
                        p["reason"] = "link"
                open_a += 1
            elif tag in HEADINGS:
                for p in pending:
                    p["prot"] = True
                    p["reason"] = "heading"
                open_heading += 1

        elif kind == "end":
            if tag == "strong":
                if pending:
                    p = pending.pop()
                    if p["prot"]:
                        report["protected"] += 1
                        if p["reason"] == "heading":
                            report["protected_heading"] += 1
                        else:
                            report["protected_link"] += 1
                    else:
                        report["converted"] += 1
                        out[p["open_idx"]] = _rewrite_open(out[p["open_idx"]])
                        out[idx] = "</b>"
                # else: thẻ đóng lạc (không có open) -> bỏ qua, giữ nguyên
            elif tag == "a":
                open_a = max(0, open_a - 1)
            elif tag in HEADINGS:
                open_heading = max(0, open_heading - 1)

    return "".join(out), report


def _rewrite_open(tag_text):
    """'<strong ...>' -> '<b ...>' giữ nguyên attribute. Bảo toàn hoa/thường phần đuôi."""
    # phần sau 'strong' (attribute + '>') giữ nguyên; tiền tố '<strong' (case-insensitive) -> '<b'
    return "<b" + tag_text[len("<strong"):]


# ----------------------------- CLI -----------------------------

def _format_report(rep, label=""):
    head = f"[strong→b] {label}".rstrip()
    return (f"{head}\n"
            f"  Tổng <strong> tìm thấy : {rep['total']}\n"
            f"  Đã đổi sang <b>        : {rep['converted']}\n"
            f"  Giữ nguyên (vùng cấm)  : {rep['protected']} "
            f"(trong heading {rep['protected_heading']}, trong link {rep['protected_link']})")


def _default_out_path(src):
    """Nơi ghi mặc định, robust cho cả workspace lẫn global install:
    1. Đi NGƯỢC từ thư mục làm việc (cwd) tìm scratch/outputs/ có sẵn -> dùng.
    2. Không thấy -> ghi CẠNH file gốc.
    Tên file: <ten>.b.<ext gốc> (mặc định .html).
    """
    base = os.path.basename(src)
    stem, ext = os.path.splitext(base)
    name = f"{stem}.b{ext or '.html'}"

    d = os.getcwd()
    while True:
        cand = os.path.join(d, "scratch", "outputs")
        if os.path.isdir(cand):
            return os.path.join(cand, name)
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return os.path.join(os.path.dirname(os.path.abspath(src)), name)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Đổi <strong>→<b>, giữ nguyên strong trong heading/link.")
    ap.add_argument("input", nargs="?",
                    help="đường dẫn file HTML. Bỏ trống = đọc stdin (mode paste).")
    ap.add_argument("-o", "--out", help="đường dẫn file kết quả (mode file).")
    ap.add_argument("--report-only", action="store_true",
                    help="chỉ in báo cáo, không xuất HTML.")
    args = ap.parse_args(argv)

    # mode paste: stdin -> stdout
    if not args.input:
        html = sys.stdin.read()
        new_html, rep = convert(html)
        if not args.report_only:
            sys.stdout.write(new_html)
        sys.stderr.write(_format_report(rep, "paste") + "\n")
        return 0

    # mode file
    if not os.path.isfile(args.input):
        sys.stderr.write(f"Không thấy file: {args.input}\n")
        return 1
    with open(args.input, "r", encoding="utf-8") as f:
        html = f.read()
    new_html, rep = convert(html)

    if args.report_only:
        sys.stderr.write(_format_report(rep, os.path.basename(args.input)) + "\n")
        return 0

    out_path = args.out or _default_out_path(args.input)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(new_html)
    sys.stderr.write(_format_report(rep, os.path.basename(args.input)) + "\n")
    sys.stderr.write(f"  → ghi: {out_path}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
