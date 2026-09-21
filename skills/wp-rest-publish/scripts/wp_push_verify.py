#!/usr/bin/env python3
"""B4 — Push bản mới + verify live. Chỉ chạy SAU khi apply-edits OK và operator đã gật.

Push: POST /posts/<id> {"content": ...}. WordPress tự lưu revision (hoàn tác được).
KHÔNG gửi 'date' -> 'modified' tự nhảy sang hôm nay = freshness signal.

Verify: fetch URL public (cache-bust) + grep các probe (câu mới PHẢI thấy, vùng khóa PHẢI còn).

Usage:
  python3 wp_push_verify.py --site example-site --id 1220 --html new.html \
      --expect "Level of Detail vs LOD in Revit||LOD Specification 2025" \
      --keep "The main difference between LOD 300 and LOD 350"
  [--credential-file PATH]  [--verify-only]  (verify-only: bỏ push, chỉ soi live)

--expect: chuỗi câu MỚI phải xuất hiện live (ngăn bằng ||).
--keep:   chuỗi vùng khóa phải CÒN live (ngăn bằng ||).
"""
import argparse
import json
import re
import sys
import time
import urllib.request
from wp_lib import load_credential, wp_post, wp_get, _CTX


def fetch_public(url):
    bust = f"{url}{'&' if '?' in url else '?'}_nocache={int(time.time())}"
    req = urllib.request.Request(bust, headers={"User-Agent": "Mozilla/5.0 wp-verify"})
    with urllib.request.urlopen(req, timeout=60, context=_CTX) as r:
        return r.read().decode("utf-8", "ignore")


def h1_count(html):
    return len(re.findall(r"<h1\b", html, flags=re.IGNORECASE))


def build_seo_meta(adapter, title=None, description=None):
    """Map normalized SEO fields to the selected plugin's registered post meta."""
    if not title and not description:
        return {}
    adapter = (adapter or "").lower()
    if adapter == "yoast":
        keys = ("_yoast_wpseo_title", "_yoast_wpseo_metadesc")
    elif adapter == "rankmath":
        keys = ("rank_math_title", "rank_math_description")
    else:
        raise ValueError("--seo-adapter must be yoast or rankmath when SEO fields are supplied")
    values = {}
    if title:
        values[keys[0]] = title
    if description:
        values[keys[1]] = description
    return values


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--id", required=True)
    ap.add_argument("--html", required=True)
    ap.add_argument("--rest-base", default="posts",
                    help="REST base của post type, vd posts, project, service")
    ap.add_argument("--edits",
                help="File edits.json — tu rut chuoi phai thay live tu cac gia tri "
                     "'new'. Dung cai nay thay vi go tay --expect: go tay hai lan "
                     "hom 19/08 deu sai byte (&nbsp; vs \\xa0, cat nham duoi cau) "
                     "va deu bao dong gia 'THIEU CA TREN content.raw'.")
    ap.add_argument("--expect", action="append", default=[],
                    help="Chuoi phai thay live. Truyen nhieu lan -> cong don, "
                         "KHONG ghi de (an le 19/08: 3 expect chi kiem 1, van bao ALL GOOD).")
    ap.add_argument("--keep", default="")
    ap.add_argument("--credential-file", "--claude-local", dest="credential_file")
    ap.add_argument("--title", default=None, help="Optional: update the WordPress post title in the same call")
    ap.add_argument("--seo-adapter", choices=("yoast", "rankmath"),
                    help="SEO plugin used to map title and meta description")
    ap.add_argument("--seo-title", default=None, help="Optional SEO title")
    ap.add_argument("--meta-description", default=None, help="Optional SEO meta description")
    ap.add_argument("--yoast-title", default=None,
                    help="Deprecated alias for --seo-adapter yoast --seo-title")
    ap.add_argument("--yoast-metadesc", default=None,
                    help="Deprecated alias for --seo-adapter yoast --meta-description")
    ap.add_argument("--verify-only", action="store_true")
    ap.add_argument("--expected-h1", type=int, default=None,
                    help="Số H1 body site yêu cầu (= body_h1_count trong publish-context). "
                         "Bỏ qua: không assert H1 (apply-edits đã giữ nguyên số H1 bản gốc).")
    a = ap.parse_args()

    base, user, app = load_credential(a.site, credential_path=a.credential_file)
    content = open(a.html, encoding="utf-8").read()
    if a.expected_h1 is not None and h1_count(content) != a.expected_h1:
        sys.exit(f"ERR: HTML phải có {a.expected_h1} H1 (body_h1_count của site); hiện có {h1_count(content)}")
    legacy_yoast = bool(a.yoast_title or a.yoast_metadesc)
    adapter = "yoast" if legacy_yoast else a.seo_adapter
    seo_title = a.yoast_title or a.seo_title
    meta_description = a.yoast_metadesc or a.meta_description
    expected_seo_meta = build_seo_meta(adapter, seo_title, meta_description)

    if not a.verify_only:
        payload = {"content": content}
        if a.title:
            payload["title"] = a.title
        if expected_seo_meta:
            payload["meta"] = expected_seo_meta
        st, d = wp_post(base, user, app, f"{a.rest_base}/{a.id}", payload)
        if st != 200 or "id" not in d:
            sys.exit(f"ERR push HTTP {st}: {json.dumps(d)[:300]}")
        print(f"PUSHED id={d['id']} modified={d.get('modified')} status={d.get('status')}")
        # Revision ID = duong rollback duy nhat khi khong co file backup tien-dot.
        # In ngay tai day vi moi dot deu can no cho log + cot Note cua plan sheet;
        # truoc 20/08 phai tu goi wp_lib de dao ra, sai 4 lan moi ra (sai chu ky
        # ham, thieu tien to duong dan, quen wp_get tra tuple).
        try:
            rst, rv = wp_get(base, user, app, f"{a.rest_base}/{a.id}/revisions?per_page=1&_fields=id")
            if rst == 200 and rv:
                print(f"REVISION {rv[0]['id']}  (rollback: khoi phuc revision truoc no)")
            else:
                print(f"REVISION khong doc duoc (HTTP {rst}) — tu tra truoc khi ghi log", file=sys.stderr)
        except Exception as e:
            print(f"REVISION khong doc duoc ({type(e).__name__}) — tu tra truoc khi ghi log", file=sys.stderr)
        link = d.get("link")
        time.sleep(3)
    else:
        # verify-only: bỏ push, chỉ lấy link để soi live
        _, meta = wp_get(base, user, app, f"{a.rest_base}/{a.id}?_fields=link")
        link = meta.get("link")

    # ---- verify live ----
    if not link:
        print("WARN: không có link để verify. Bỏ qua verify."); return
    html = fetch_public(link)

    # Frontend là bản ĐÃ qua filter (wptexturize đổi ' thành &#8217;, theme bọc lại
    # ranh giới thẻ), nên probe trượt ở frontend CHƯA chắc là đẩy hỏng. Lấy sẵn
    # content.raw để đối chiếu — nguồn sự thật là đây, không phải trang public.
    raw = ""
    readback_meta = {}
    try:
        _, d_raw = wp_get(base, user, app, f"{a.rest_base}/{a.id}?context=edit&_fields=content,meta")
        raw = (d_raw.get("content") or {}).get("raw") or ""
        readback_meta = d_raw.get("meta") or {}
    except Exception as e:
        print(f"WARN: không đọc được content.raw để đối chiếu ({e})")

    def probe(p):
        """(verdict, nhãn) — CHỈ FAIL khi content.raw cũng thiếu."""
        if p in html:
            return True, "✓"
        if raw and p in raw:
            return True, "✓ (raw OK — frontend đổi ký tự khi render)"
        return False, "✗ THIẾU CẢ TRÊN content.raw"

    ok = True
    if a.expected_h1 is not None and raw and h1_count(raw) != a.expected_h1:
        ok = False
        print(f"✗ content.raw phải có {a.expected_h1} H1; hiện có {h1_count(raw)}")
    for key, expected in expected_seo_meta.items():
        if readback_meta.get(key) != expected:
            ok = False
            print(f"✗ SEO meta {key} đọc lại không khớp")
    _exp = list(a.expect)
    if a.edits:
        import json as _j
        for _e in _j.load(open(a.edits, encoding="utf-8")):
            _n = _e.get("new", "")
            # uu tien the <a ...>...</a>: doan on dinh nhat qua render
            _m = re.findall(r'<a href="[^"]+"[^>]*>.*?</a>', _n, re.S)
            _exp.extend(_m if _m else [_n[:120]])
        print(f"[expect] rut {len(_exp) - len(a.expect)} chuoi tu {a.edits}")
    if _exp:
        print("\n-- Câu MỚI phải thấy live --")
        for p in [x for one in _exp for x in one.split("||") if x.strip()]:
            good, tag = probe(p)
            ok &= good
            print(f"  {tag} {p[:70]}")
    if a.keep:
        print("\n-- Vùng khóa phải CÒN live --")
        for p in [x for x in a.keep.split("||") if x.strip()]:
            good, tag = probe(p)
            ok &= good
            print(f"  {tag} {p[:70]}")
    print(f"\n{'ALL GOOD ✓' if ok else '!!! CÓ PROBE FAIL — kiểm tra + cân nhắc revert qua WP Revisions'}")
    print(f"Live: {link}")
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
