#!/usr/bin/env python3
"""Setup / preflight for /watch.

Modes:
  setup.py --check      Silent preflight. Exit 0 if ready, 2/3/4 on failure.
  setup.py --json       Machine-readable status for Claude to parse.
  setup.py              Installer. Auto-installs deps, scaffolds .env, marks SETUP_COMPLETE.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


REQUIRED_BINARIES = ["ffmpeg", "ffprobe", "yt-dlp"]
CONFIG_DIR = Path.home() / ".config" / "watch"
CONFIG_FILE = CONFIG_DIR / ".env"
ENV_TEMPLATE = """# /watch API configuration
#
# Whisper transcription fallback — used only when yt-dlp cannot get captions
# (or when you point /watch at a local file with no subtitles).
#
# Groq is preferred: it runs whisper-large-v3 at a fraction of OpenAI's price
# and is faster in practice. OpenAI is the compatible fallback.
#
# Get a Groq key:  https://console.groq.com/keys
# Get an OpenAI key:  https://platform.openai.com/api-keys
#
# Leave both blank to disable Whisper — /watch will still work, but videos
# without native captions will come back frames-only.

GROQ_API_KEY=
OPENAI_API_KEY=
"""


def _check_binaries() -> list[str]:
    return [b for b in REQUIRED_BINARIES if shutil.which(b) is None]


def _check_api_key() -> bool:
    for key in ("GROQ_API_KEY", "OPENAI_API_KEY"):
        if os.environ.get(key, "").strip():
            return True
    if CONFIG_FILE.exists():
        for line in CONFIG_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                if k.strip() in ("GROQ_API_KEY", "OPENAI_API_KEY") and v.strip():
                    return True
    return False


def _setup_complete() -> bool:
    if CONFIG_FILE.exists():
        for line in CONFIG_FILE.read_text(encoding="utf-8").splitlines():
            if line.strip() == "SETUP_COMPLETE=true":
                return True
    return False


def _install_binary(name: str) -> bool:
    system = platform.system()
    if system == "Darwin" and shutil.which("brew"):
        pkg = "ffmpeg" if name in ("ffmpeg", "ffprobe") else name
        result = subprocess.run(["brew", "install", pkg])
        return result.returncode == 0
    return False


def _scaffold_env() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(ENV_TEMPLATE, encoding="utf-8")
        CONFIG_FILE.chmod(0o600)
        print(f"[setup] created {CONFIG_FILE}")
    else:
        print(f"[setup] {CONFIG_FILE} already exists — skipping")


def _mark_complete() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    existing = CONFIG_FILE.read_text(encoding="utf-8") if CONFIG_FILE.exists() else ""
    if "SETUP_COMPLETE=true" not in existing:
        with CONFIG_FILE.open("a", encoding="utf-8") as f:
            f.write("\nSETUP_COMPLETE=true\n")
        CONFIG_FILE.chmod(0o600)


def check_mode() -> None:
    missing = _check_binaries()
    if missing:
        raise SystemExit(2)
    if not _check_api_key():
        raise SystemExit(3)
    if not _setup_complete():
        raise SystemExit(4)


def json_mode() -> None:
    missing = _check_binaries()
    has_key = _check_api_key()
    complete = _setup_complete()
    status = {
        "ready": not missing and has_key and complete,
        "missing_binaries": missing,
        "has_api_key": has_key,
        "setup_complete": complete,
        "config_file": str(CONFIG_FILE),
    }
    print(json.dumps(status, indent=2))


def install_mode() -> None:
    print("[setup] checking dependencies…")
    missing = _check_binaries()

    if missing:
        system = platform.system()
        if system == "Darwin" and shutil.which("brew"):
            for name in missing:
                print(f"[setup] installing {name} via Homebrew…")
                if _install_binary(name):
                    print(f"[setup] {name} installed")
                else:
                    print(f"[setup] failed to install {name} — install manually", file=sys.stderr)
        else:
            print(
                f"[setup] missing: {', '.join(missing)}\n"
                "Install manually:\n"
                "  ffmpeg/ffprobe: https://ffmpeg.org/download.html\n"
                "  yt-dlp: https://github.com/yt-dlp/yt-dlp#installation",
                file=sys.stderr,
            )

    _scaffold_env()

    if not _check_api_key():
        print(
            f"\n[setup] No API key found. Edit {CONFIG_FILE} and add your Groq or OpenAI key.\n"
            "  Groq (free tier, faster): https://console.groq.com/keys\n"
            "  OpenAI: https://platform.openai.com/api-keys"
        )
    else:
        print("[setup] API key found")

    _mark_complete()
    print("[setup] done")


def main() -> None:
    args = sys.argv[1:]
    if "--check" in args:
        check_mode()
    elif "--json" in args:
        json_mode()
    else:
        install_mode()


if __name__ == "__main__":
    main()
