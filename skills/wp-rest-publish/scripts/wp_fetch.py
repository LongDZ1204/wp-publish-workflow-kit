#!/usr/bin/env python3
"""B1 — Kéo bài live về + backup. KHÔNG sửa gì.

Usage:
  python3 wp_fetch.py --site example-site --slug bim-level-of-development --out DIR
  python3 wp_fetch.py --site example-site --id 1220 --out DIR
  [--credential-file /path/to/.env.wp-publish]  [--backup /path/to/item/backups]

Xuất ra DIR: <slug|id>.raw.html (content.raw) + <slug|id>.meta.json (id, modified, link, title).
Nếu --backup có, copy thêm 1 bản .raw.html vào đó (timestamp do người gọi tự đặt tên trước).
"""
import argparse
import json
import os
import sys
from wp_lib import load_credential, wp_get, detect_format


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True, help="site key khớp prefix trong .env.wp-publish")
    ap.add_argument("--slug")
    ap.add_argument("--id")
    ap.add_argument("--out", required=True, help="thư mục xuất")
    ap.add_argument("--rest-base", default="posts",
                    help="REST base của post type, vd posts, project, service")
    ap.add_argument("--credential-file", "--claude-local", dest="credential_file")
    ap.add_argument("--backup", help="thư mục backup thêm (vd projects/<client>/content/blog/<slug>/backups)")
    a = ap.parse_args()
    if not a.slug and not a.id:
        sys.exit("ERR: cần --slug hoặc --id")

    base, user, app = load_credential(a.site, credential_path=a.credential_file)
    os.makedirs(a.out, exist_ok=True)

    if a.id:
        st, d = wp_get(base, user, app, f"{a.rest_base}/{a.id}?context=edit&_fields=id,slug,link,modified,status,title,content")
        post = d if isinstance(d, dict) and "id" in d else None
    else:
        st, d = wp_get(base, user, app, f"{a.rest_base}?slug={a.slug}&context=edit&_fields=id,slug,link,modified,status,title,content")
        post = d[0] if isinstance(d, list) and d else None

    if st != 200 or not post:
        sys.exit(f"ERR HTTP {st}: {json.dumps(d)[:300]}")

    stub = a.id or a.slug
    raw = post["content"]["raw"]
    raw_path = os.path.join(a.out, f"{stub}.raw.html")
    open(raw_path, "w", encoding="utf-8").write(raw)
    meta = {k: (post[k]["raw"] if isinstance(post.get(k), dict) and "raw" in post[k] else post.get(k))
            for k in ("id", "slug", "link", "modified", "status", "title")}
    meta["format"] = detect_format(raw)
    meta["rest_base"] = a.rest_base
    open(os.path.join(a.out, f"{stub}.meta.json"), "w", encoding="utf-8").write(json.dumps(meta, indent=2))

    if a.backup:
        os.makedirs(a.backup, exist_ok=True)
        bpath = os.path.join(a.backup, f"{stub}.wp-raw-backup.html")
        open(bpath, "w", encoding="utf-8").write(raw)

    print(json.dumps({
        "id": meta["id"], "modified": meta["modified"], "status": meta["status"],
        "format": meta["format"], "chars": len(raw),
        "tables": raw.count("<table"), "imgs": raw.count("<img"), "iframes": raw.count("<iframe"),
        "raw_file": raw_path, "backup": (bpath if a.backup else None),
        "title": meta["title"],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
