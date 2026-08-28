#!/usr/bin/env python3
"""Securely verify and store one WordPress Application Password.

The password is collected with getpass so it is never placed in shell history,
command arguments, or AI chat. The resulting CLAUDE.local.md is mode 0600 and
is ignored by this repository.
"""

from __future__ import annotations

import argparse
import getpass
import importlib.util
import os
import re
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[3]


def load_wp_lib():
    path = ROOT / "skills/wp-rest-publish/scripts/wp_lib.py"
    spec = importlib.util.spec_from_file_location("wp_setup_credentials_lib", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


WP_LIB = load_wp_lib()
REQUIRED_CAPABILITIES = (
    "edit_posts",
    "edit_others_posts",
    "edit_published_posts",
    "upload_files",
)


def validate_inputs(site_key: str, url: str, user: str) -> tuple[str, str, str]:
    key = site_key.strip().lower()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", key):
        raise ValueError("site-key must be a kebab-case name, for example vibim")
    base_url = url.strip().rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("WordPress URL must be a complete HTTPS URL")
    username = user.strip()
    if not username:
        raise ValueError("WordPress user is required")
    return key, base_url, username


def assess_user(profile: dict) -> dict:
    roles = {str(role).lower() for role in profile.get("roles") or []}
    capabilities = profile.get("capabilities") or {}
    missing = [name for name in REQUIRED_CAPABILITIES if capabilities.get(name) is not True]
    return {
        "roles": sorted(roles),
        "missing_capabilities": missing,
        "administrator": "administrator" in roles,
    }


def credential_block(site_key: str, url: str, user: str, app_password: str) -> str:
    return (
        f"### {site_key} WordPress (REST API)\n"
        f"- URL: {url}\n"
        f"- User: {user}\n"
        f"- App Password: {app_password.strip()}\n"
    )


def update_text(current: str, site_key: str, block: str, replace: bool) -> str:
    pattern = re.compile(
        rf"(?ms)^###\s+{re.escape(site_key)}\s+WordPress\s+\(REST API\)\s*$.*?(?=^###\s+|\Z)",
        flags=re.IGNORECASE,
    )
    match = pattern.search(current)
    if match and not replace:
        raise ValueError(f"credential for {site_key} already exists; use --replace to rotate it")
    if match:
        return (current[:match.start()] + block + current[match.end():]).strip() + "\n"
    prefix = current.strip()
    return (prefix + "\n\n" if prefix else "") + block


def atomic_private_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.chmod(temp_name, 0o600)
        os.replace(temp_name, path)
        os.chmod(path, 0o600)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-key", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--output", default="CLAUDE.local.md")
    parser.add_argument("--replace", action="store_true", help="Replace an existing block for this site")
    args = parser.parse_args()
    try:
        site_key, base_url, username = validate_inputs(args.site_key, args.url, args.user)
        if not sys.stdin.isatty():
            raise ValueError("run this command in an interactive terminal; password piping is disabled")
        app_password = getpass.getpass("Application Password (input hidden): ").strip()
        if not app_password:
            raise ValueError("Application Password is required")
        status, profile = WP_LIB.wp_get(
            base_url,
            username,
            app_password,
            "users/me?context=edit&_fields=id,name,roles,capabilities",
        )
        if status != 200:
            raise ValueError(f"WordPress credential check failed with HTTP {status}")
        assessment = assess_user(profile)
        if assessment["administrator"]:
            raise ValueError("Administrator is too broad; create a dedicated Editor user")
        if assessment["missing_capabilities"]:
            missing = ", ".join(assessment["missing_capabilities"])
            raise ValueError(f"WordPress user lacks required capabilities: {missing}")
        output = Path(args.output).expanduser().resolve()
        current = output.read_text(encoding="utf-8") if output.exists() else ""
        updated = update_text(
            current,
            site_key,
            credential_block(site_key, base_url, username, app_password),
            args.replace,
        )
        atomic_private_write(output, updated)
        roles = ",".join(assessment["roles"]) or "custom"
        print(f"OK site={site_key} role={roles} credential_file={output} mode=0600")
        return 0
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"STOP {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
