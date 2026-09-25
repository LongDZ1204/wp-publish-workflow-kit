#!/usr/bin/env python3
"""Read-only WordPress discovery for proposed per-content-type profiles."""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _load_wp_lib():
    path = ROOT / "skills" / "wp-rest-publish" / "scripts" / "wp_lib.py"
    spec = importlib.util.spec_from_file_location("wp_scan_rest_lib", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


WP_LIB = _load_wp_lib()


def request_json(method: str, url: str, user: str, app_pass: str) -> tuple[int, object]:
    if method not in {"GET", "OPTIONS"}:
        raise ValueError("READ-ONLY: site scan only permits GET and OPTIONS")
    token = base64.b64encode(f"{user}:{app_pass}".encode()).decode()
    request = urllib.request.Request(url, method=method)
    request.add_header("Authorization", f"Basic {token}")
    try:
        with urllib.request.urlopen(request, timeout=60, context=WP_LIB._CTX) as response:
            body = response.read().decode()
            return response.status, json.loads(body or "{}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        try:
            payload = json.loads(body or "{}")
        except json.JSONDecodeError:
            payload = {"error": "non-json response"}
        return exc.code, payload


def _stable_hash(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def _find_type(types: dict, preferred_type: str, default_rest_base: str) -> tuple[str | None, str]:
    preferred = types.get(preferred_type)
    if isinstance(preferred, dict):
        return preferred_type, str(preferred.get("rest_base") or default_rest_base)
    for name, value in types.items():
        if isinstance(value, dict) and str(value.get("rest_base") or name) == default_rest_base:
            return name, default_rest_base
    return None, default_rest_base


def build_scan(
    base_url: str,
    user: str,
    app_pass: str,
    requester=request_json,
) -> dict:
    api = base_url.rstrip("/") + "/wp-json/wp/v2"
    calls: list[dict] = []

    def fetch(method: str, path: str) -> tuple[int, object]:
        status, payload = requester(method, f"{api}/{path}", user, app_pass)
        calls.append({"method": method, "path": path, "status": status})
        return status, payload

    me_status, me = fetch("GET", "users/me?context=edit")
    if me_status != 200 or not isinstance(me, dict) or not me.get("id"):
        raise ValueError(f"WordPress credential check failed: users/me HTTP {me_status}")
    types_status, types = fetch("GET", "types?context=edit")
    tax_status, taxonomies = fetch("GET", "taxonomies?context=edit")
    if not isinstance(me, dict):
        me = {}
    if not isinstance(types, dict):
        types = {}
    if not isinstance(taxonomies, dict):
        taxonomies = {}

    profiles = {}
    mapping = {
        "blog": ("post", "posts", "clean_article", ["edit_posts", "upload_files"]),
        "service-page": ("page", "pages", "preserve_builder", ["edit_pages", "upload_files"]),
        "product": ("product", "product", "preserve_builder", ["edit_products", "upload_files"]),
    }
    capabilities = me.get("capabilities") if isinstance(me.get("capabilities"), dict) else {}
    for content_type, (preferred_type, default_rest_base, html_policy, required_caps) in mapping.items():
        post_type, rest_base = _find_type(types, preferred_type, default_rest_base)
        options_status = None
        schema = {}
        if post_type:
            options_status, options = fetch("OPTIONS", rest_base)
            if isinstance(options, dict):
                schema = options
        missing_caps = [name for name in required_caps if capabilities.get(name) is not True]
        profiles[content_type] = {
            "endpoint": rest_base,
            "post_type": post_type,
            "discovery_status": "available" if post_type else "not_exposed",
            "status": "unconfirmed",
            "ready": False,
            "pilot_allowed": False,
            "batch_ready": False,
            "body_h1_count": None,
            "html_policy": html_policy,
            "required_fields": ["title", "content", "slug"],
            "required_capabilities": required_caps,
            "missing_capabilities": missing_caps,
            "options_status": options_status,
            "schema_hash": _stable_hash(schema) if schema else None,
            "image_policy": {"format_policy": "preserve", "max_kb": 150, "max_width": 1200},
            "seo_meta_adapter": None,
        }

    return {
        "version": 1,
        "read_only": True,
        "site_url": base_url.rstrip("/"),
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "identity": {
            "status": me_status,
            "id": me.get("id"),
            "name": me.get("name"),
            "roles": me.get("roles", []),
            "capabilities": capabilities,
        },
        "types_status": types_status,
        "taxonomies_status": tax_status,
        "taxonomies": sorted(taxonomies),
        "profiles": profiles,
        "calls": calls,
    }


def proposed_context(site_key: str, scan: dict) -> dict:
    return {
        "version": 2,
        "site_key": site_key,
        "tracker": {"type": "none"},
        "content_profiles": scan["profiles"],
        "timezone": "UTC",
        "confirmation": {
            "status": "required",
            "note": "Confirm only the content type requested by the user; pilot it before batch use.",
        },
    }


def safe_stamp(value: str) -> str:
    return re.sub(r"[^0-9T-]", "", value.split("+")[0].replace(":", ""))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--client", required=True)
    parser.add_argument("--site-key", required=True)
    parser.add_argument("--projects-root", default=str(Path.cwd() / "projects"))
    args = parser.parse_args()
    project = Path(args.projects_root).resolve() / args.client
    if not (project / "context.md").is_file():
        print("STOP BRAND-MISSING: create and approve project context.md first")
        return 2
    try:
        shared_file = WP_LIB.KIT_ROOT / "wp-credentials.env"
        if shared_file.is_file():
            WP_LIB.google_service_account_from_env_text(WP_LIB._read_env_file(shared_file))
        base_url, user, app_pass = WP_LIB.load_credential(args.site_key)
        scan = build_scan(base_url, user, app_pass)
        output = project / "scans" / safe_stamp(scan["scanned_at"])
        output.mkdir(parents=True, exist_ok=False)
        (output / "site-scan.json").write_text(
            json.dumps(scan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (output / "publish-context.proposed.json").write_text(
            json.dumps(proposed_context(args.site_key, scan), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"STOP {exc}")
        return 2
    print(f"OK read-only scan={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
