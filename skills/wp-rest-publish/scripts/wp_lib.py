#!/usr/bin/env python3
"""Shared WordPress REST helpers with explicitly loaded local credentials.

The preferred file is one root `wp-credentials.env` for every site. Older
per-project files, `.env.wp-publish` and `CLAUDE.local.md` are read-only
compatibility fallbacks. Credential files are parsed, never sourced.
"""
import os
import re
import sys
import json
from pathlib import Path
import ssl
import base64
import urllib.request
import urllib.error


PROJECTS_ROOT = Path(__file__).resolve().parents[3] / "projects"
KIT_ROOT = PROJECTS_ROOT.parent


def _ssl_ctx():
    """CA bundle chắc chắn có (macOS Python hay thiếu system CA → dùng certifi)."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


_CTX = _ssl_ctx()


def _site_token(site_key):
    token = re.sub(r"[^A-Za-z0-9]+", "_", str(site_key)).strip("_").upper()
    if not token:
        raise ValueError("site_key is required")
    return token


def parse_env_text(text):
    """Parse a small dotenv subset without expansion or shell execution."""
    values = {}
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        number = index + 1
        raw = lines[index]
        index += 1
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise ValueError(f"invalid credential line {number}")
        key, value = line.split("=", 1)
        key = key.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise ValueError(f"invalid credential key on line {number}")
        if key in values:
            raise ValueError(f"duplicate credential key: {key}")
        value = value.strip()
        if value.startswith('"""'):
            value = value[3:]
            if value.endswith('"""'):
                value = value[:-3]
            else:
                chunks = [value] if value else []
                while index < len(lines) and lines[index].strip() != '"""':
                    chunks.append(lines[index])
                    index += 1
                if index == len(lines):
                    raise ValueError(f"unterminated multiline value on line {number}")
                index += 1
                value = "\n".join(chunks)
        elif value.startswith('"'):
            try:
                value = json.loads(value)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid quoted value on line {number}") from exc
            if not isinstance(value, str):
                raise ValueError(f"credential value must be text on line {number}")
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1]
        values[key] = value
    return values


def google_service_account_from_env_text(text):
    """Validate an optional shared service-account JSON, without logging its contents."""
    raw = parse_env_text(text).get("GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw:
        return None
    try:
        info = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid Google Sheets service-account JSON") from exc
    required = ("client_email", "private_key", "token_uri")
    if not isinstance(info, dict) or info.get("type") != "service_account" or not all(info.get(k) for k in required):
        raise ValueError("incomplete Google Sheets service-account JSON")
    return info


def credential_from_env_text(site_key, text):
    values = parse_env_text(text)
    prefix = f"WP_{_site_token(site_key)}"
    url = values.get(f"{prefix}_URL")
    user = values.get(f"{prefix}_USER")
    app = values.get(f"{prefix}_APP_PASS")
    if any((url, user, app)) and not all((url, user, app)):
        raise ValueError(f"incomplete credential entry for {site_key}")
    if url and user and app:
        if not url.startswith("https://"):
            raise ValueError(f"credential URL for {site_key} must use HTTPS")
        return url.rstrip("/"), user, app
    return None


def credential_from_project_text(text):
    """Parse one visible, per-project credential file with fixed field names."""
    values = parse_env_text(text)
    fields = (values.get("WP_URL"), values.get("WP_USER"), values.get("WP_APP_PASS"))
    if not all(fields):
        raise ValueError("incomplete project credential: WP_URL, WP_USER and WP_APP_PASS are required")
    url, user, app = fields
    if not url.startswith("https://"):
        raise ValueError("project credential WP_URL must use HTTPS")
    return url.rstrip("/"), user, app


def credential_from_legacy_text(site_key, text):
    key = str(site_key).lower()
    blocks = re.split(r"(?m)^#{2,4}\s+", text)
    for block in blocks:
        head = block.splitlines()[0].lower() if block.strip() else ""
        url = _grab(block, "URL")
        if not url:
            continue
        domain = re.sub(r"^https?://", "", url).rstrip("/").lower()
        if key in head or key in domain:
            user = _grab(block, "User")
            app = _grab(block, "App Password") or _grab(block, "Application Password")
            if url and user and app:
                return url.rstrip("/"), user, app
    return None


def _read_env_file(path):
    target = Path(path).expanduser()
    if os.name != "nt" and target.stat().st_mode & 0o077:
        raise ValueError(f"credential file permissions are too broad: {target}; run chmod 600")
    return target.read_text(encoding="utf-8")


def load_credential(site_key, credential_path=None, claude_local_path=None):
    """Return (base_url, user, app_pass), preferring the shared root file."""
    explicit = credential_path or claude_local_path or os.environ.get("WP_CREDENTIAL_FILE")
    if explicit:
        if not os.path.isfile(explicit):
            sys.exit(f"ERR: credential file not found: {explicit}")
        if str(explicit).lower().endswith(".md"):
            found = credential_from_legacy_text(
                site_key, Path(explicit).expanduser().read_text(encoding="utf-8")
            )
        else:
            contents = _read_env_file(explicit)
            found = credential_from_env_text(site_key, contents)
            if not found and "WP_URL" in parse_env_text(contents):
                found = credential_from_project_text(contents)
        if found:
            return found
        sys.exit(f"ERR: credential file has no complete entry for '{site_key}': {explicit}")

    shared_file = KIT_ROOT / "wp-credentials.env"
    if shared_file.is_file():
        found = credential_from_env_text(site_key, _read_env_file(shared_file))
        if found:
            return found

    if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", str(site_key)):
        project_file = PROJECTS_ROOT / str(site_key) / "wp-credentials.env"
        if project_file.is_file():
            return credential_from_project_text(_read_env_file(project_file))

    process_values = (
        os.environ.get("WP_URL"), os.environ.get("WP_USER"), os.environ.get("WP_APP_PASS")
    )
    if any(process_values) and not all(process_values):
        raise ValueError("incomplete WP_URL/WP_USER/WP_APP_PASS process environment")
    if all(process_values):
        if not os.environ["WP_URL"].startswith("https://"):
            raise ValueError("WP_URL must use HTTPS")
        return (os.environ["WP_URL"].rstrip("/"),
                os.environ["WP_USER"], os.environ["WP_APP_PASS"])

    env_paths = []
    env_paths += [".env.wp-publish", os.path.expanduser("~/.config/wp-publish/credentials.env")]
    for path in env_paths:
        if path and os.path.isfile(path):
            found = credential_from_env_text(site_key, _read_env_file(path))
            if found:
                return found

    legacy_paths = ["CLAUDE.local.md", os.path.expanduser("~/CLAUDE.local.md")]
    for path in legacy_paths:
        if path and os.path.isfile(path):
            found = credential_from_legacy_text(
                site_key, Path(path).expanduser().read_text(encoding="utf-8")
            )
            if found:
                return found
    sys.exit(
        f"ERR: không thấy credential cho '{site_key}'. Dùng wp-credentials.env ở root, "
        "WP_CREDENTIAL_FILE hoặc WP_URL/WP_USER/WP_APP_PASS."
    )


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
