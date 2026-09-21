#!/usr/bin/env python3
"""Securely verify and store one WordPress Application Password.

Prefer a native masked password dialog so Codex can wait for completion without
asking the user to interact with, or report back from, a terminal. The password
never appears in shell history, command arguments, AI chat, or script output.
"""

from __future__ import annotations

import argparse
import getpass
import importlib.util
import json
import os
import platform
import re
import shutil
import subprocess
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
MACOS_DIALOG_SCRIPT = r'''
on run argv
    set siteName to item 1 of argv
    set promptText to "Dán Application Password cho " & siteName & "." & return & return & "Mật khẩu được che và không gửi vào chat."
    set answerBox to display dialog promptText default answer "" with hidden answer buttons {"Hủy", "Lưu & kiểm tra"} default button "Lưu & kiểm tra" cancel button "Hủy" with title "WP Publish Setup"
    return text returned of answerBox
end run
'''


class DialogUnavailable(RuntimeError):
    pass


class InputCancelled(ValueError):
    pass


def macos_password_dialog(site_key: str, runner=None) -> str:
    if not shutil.which("osascript"):
        raise DialogUnavailable("osascript is not available")
    runner = runner or subprocess.run
    result = runner(
        ["osascript", "-e", MACOS_DIALOG_SCRIPT, site_key],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise InputCancelled("password entry was cancelled")
    return result.stdout.rstrip("\r\n")


def linux_password_dialog(site_key: str, runner=None) -> str:
    if not shutil.which("zenity"):
        raise DialogUnavailable("zenity is not available")
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        raise DialogUnavailable("no Linux desktop display is available")
    runner = runner or subprocess.run
    result = runner(
        [
            "zenity",
            "--password",
            "--title=WP Publish Setup",
            f"--text=Dán Application Password cho {site_key}. Mật khẩu không gửi vào chat.",
            "--ok-label=Lưu & kiểm tra",
            "--cancel-label=Hủy",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise InputCancelled("password entry was cancelled")
    return result.stdout.rstrip("\r\n")


def native_password_dialog(site_key: str) -> str:
    system = platform.system().lower()
    if system == "darwin":
        return macos_password_dialog(site_key)
    if system == "linux":
        return linux_password_dialog(site_key)
    raise DialogUnavailable(f"native password dialog is not supported on {system or 'this platform'}")


def collect_password(site_key: str, input_mode: str) -> str:
    if input_mode in {"auto", "dialog"}:
        try:
            return native_password_dialog(site_key)
        except DialogUnavailable:
            if input_mode == "dialog":
                raise
    if not sys.stdin.isatty():
        raise ValueError(
            "native password dialog is unavailable and terminal input is not interactive; "
            "rerun from a terminal with --input-mode terminal"
        )
    return getpass.getpass("Application Password (input hidden): ")


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


def env_prefix(site_key: str) -> str:
    return "WP_" + re.sub(r"[^A-Za-z0-9]+", "_", site_key).strip("_").upper()


def dotenv_value(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def credential_block(site_key: str, url: str, user: str, app_password: str) -> str:
    prefix = env_prefix(site_key)
    return (
        f"# site: {site_key}\n"
        f"{prefix}_URL={dotenv_value(url)}\n"
        f"{prefix}_USER={dotenv_value(user)}\n"
        f"{prefix}_APP_PASS={dotenv_value(app_password.strip())}\n"
    )


def update_text(current: str, site_key: str, block: str, replace: bool) -> str:
    pattern = re.compile(
        rf"(?ms)^#\s*site:\s*{re.escape(site_key)}\s*$.*?(?=^#\s*site:\s*|\Z)",
        flags=re.IGNORECASE,
    )
    match = pattern.search(current)
    if match and not replace:
        raise ValueError(f"credential for {site_key} already exists; use --replace to rotate it")
    if match:
        return (current[:match.start()] + block + current[match.end():]).strip() + "\n"
    prefix = current.strip()
    return (prefix + "\n\n" if prefix else "") + block


def parse_legacy_credentials(text: str) -> list[tuple[str, str, str, str]]:
    result = []
    blocks = re.split(r"(?m)^#{2,4}\s+", text)
    for block in blocks:
        if not block.strip():
            continue
        heading = block.splitlines()[0].strip()
        match = re.match(r"(.+?)\s+WordPress\s+\(REST API\)\s*$", heading, re.IGNORECASE)
        if not match:
            continue
        site_key = match.group(1).strip().lower()
        url = WP_LIB._grab(block, "URL")
        user = WP_LIB._grab(block, "User")
        app = WP_LIB._grab(block, "App Password") or WP_LIB._grab(block, "Application Password")
        if url and user and app:
            validate_inputs(site_key, url, user)
            result.append((site_key, url.rstrip("/"), user, app))
    if not result:
        raise ValueError("no WordPress credential blocks found in legacy file")
    return result


def migrate_legacy_text(current: str, legacy: str, replace: bool = False) -> tuple[str, int]:
    updated = current
    entries = parse_legacy_credentials(legacy)
    for site_key, url, user, app_password in entries:
        updated = update_text(
            updated, site_key, credential_block(site_key, url, user, app_password), replace
        )
    return updated, len(entries)


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
    parser.add_argument("--site-key")
    parser.add_argument("--url")
    parser.add_argument("--user")
    parser.add_argument("--output", default=".env.wp-publish")
    parser.add_argument(
        "--migrate-legacy", nargs="?", const="CLAUDE.local.md",
        help="Migrate all legacy Markdown credential blocks; the source file is retained",
    )
    parser.add_argument(
        "--input-mode",
        choices=("auto", "dialog", "terminal"),
        default="auto",
        help="Use a native password dialog when available; terminal is the fallback",
    )
    parser.add_argument("--replace", action="store_true", help="Replace an existing block for this site")
    args = parser.parse_args()
    try:
        output = Path(args.output).expanduser().resolve()
        current = output.read_text(encoding="utf-8") if output.exists() else ""
        if args.migrate_legacy:
            legacy_path = Path(args.migrate_legacy).expanduser().resolve()
            updated, count = migrate_legacy_text(
                current, legacy_path.read_text(encoding="utf-8"), args.replace
            )
            atomic_private_write(output, updated)
            print(
                f"OK migrated_sites={count} credential_file={output} mode=0600 "
                f"legacy_retained={legacy_path}"
            )
            return 0
        if not (args.site_key and args.url and args.user):
            raise ValueError("--site-key, --url and --user are required unless --migrate-legacy is used")
        site_key, base_url, username = validate_inputs(args.site_key, args.url, args.user)
        app_password = collect_password(site_key, args.input_mode).strip()
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
