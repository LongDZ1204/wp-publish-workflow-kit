#!/usr/bin/env python3
"""Shared helpers cho wp-rest-publish skill.

Credential KHÔNG bao giờ nằm trên command line — đọc từ CLAUDE.local.md hoặc env.
Format khối trong CLAUDE.local.md (mục 1):

    ### <Tên site> WordPress (REST API)
    - URL: https://example.com
    - User: someuser
    - App Password: xxxx xxxx xxxx xxxx xxxx xxxx

`site_key` khớp theo tên heading HOẶC domain trong URL (không phân biệt hoa/thường).
"""
import os
import re
import sys
import json
import ssl
import base64
import urllib.request
import urllib.error


def _ssl_ctx():
    """CA bundle chắc chắn có (macOS Python hay thiếu system CA → dùng certifi)."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


_CTX = _ssl_ctx()


def load_credential(site_key, claude_local_path=None):
    """Trả (base_url, user, app_pass). Ưu tiên env WP_URL/WP_USER/WP_APP_PASS."""
    if os.environ.get("WP_URL") and os.environ.get("WP_USER") and os.environ.get("WP_APP_PASS"):
        return (os.environ["WP_URL"].rstrip("/"),
                os.environ["WP_USER"], os.environ["WP_APP_PASS"])

    paths = [claude_local_path] if claude_local_path else []
    paths += ["CLAUDE.local.md", os.path.expanduser("~/CLAUDE.local.md")]
    text = None
    for p in paths:
        if p and os.path.exists(p):
            text = open(p, encoding="utf-8").read()
            break
    if text is None:
        sys.exit("ERR: không tìm thấy credential. Set env WP_URL/WP_USER/WP_APP_PASS "
                 "hoặc thêm khối site vào CLAUDE.local.md.")

    # tách theo heading ### hoặc ####
    blocks = re.split(r"(?m)^#{2,4}\s+", text)
    key = site_key.lower()
    for b in blocks:
        head = b.splitlines()[0].lower() if b.strip() else ""
        url = _grab(b, "URL")
        if not url:
            continue
        domain = re.sub(r"^https?://", "", url).rstrip("/").lower()
        if key in head or key in domain:
            user = _grab(b, "User")
            app = _grab(b, "App Password") or _grab(b, "Application Password")
            if url and user and app:
                return url.rstrip("/"), user, app
    sys.exit(f"ERR: không thấy khối site khớp '{site_key}' trong CLAUDE.local.md.")


def _grab(block, label):
    m = re.search(rf"(?im)^[-*]?\s*{re.escape(label)}\s*:\s*(.+?)\s*$", block)
    return m.group(1).strip() if m else None


def _auth_header(user, app_pass):
    tok = base64.b64encode(f"{user}:{app_pass}".encode()).decode()
    return f"Basic {tok}"


def _decode(body, where):
    """REST tra JSON. Tra HTML = KHONG phai '404 khong tim thay'.

    WAF, CDN challenge, proxy or maintenance pages can return HTML, sometimes
    even with HTTP 200. That state is ambiguous and must stop the workflow;
    it must never be interpreted as a missing post or a safe retry signal.
    """
    b = (body or "").lstrip()
    if b[:1] in ("{", "["):
        return json.loads(b)
    if b.lower().startswith("<!doctype") or b[:5].lower() == "<html":
        raise RuntimeError(
            f"WP tra HTML thay vi JSON o {where} — site dang chan bot "
            f"(hoac WAF/maintenance). DUNG LAI, cho vai phut roi thu lai. "
            f"KHONG duoc hieu la 'khong tim thay'.")
    return json.loads(b or "{}")


def wp_get(base_url, user, app_pass, path):
    req = urllib.request.Request(f"{base_url}/wp-json/wp/v2/{path}")
    req.add_header("Authorization", _auth_header(user, app_pass))
    try:
        with urllib.request.urlopen(req, timeout=60, context=_CTX) as r:
            return r.status, _decode(r.read().decode(), f"GET {path}")
    except urllib.error.HTTPError as e:
        return e.code, _decode(e.read().decode(), f"GET {path}")


def wp_post(base_url, user, app_pass, path, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(f"{base_url}/wp-json/wp/v2/{path}", data=data, method="POST")
    req.add_header("Authorization", _auth_header(user, app_pass))
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=90, context=_CTX) as r:
            return r.status, _decode(r.read().decode(), f"POST {path}")
    except urllib.error.HTTPError as e:
        return e.code, _decode(e.read().decode(), f"POST {path}")


def detect_format(raw):
    """Classic vs Gutenberg — quyết định cách sửa an toàn."""
    if "<!-- wp:" in raw:
        return "gutenberg"
    return "classic"
