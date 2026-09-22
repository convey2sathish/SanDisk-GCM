"""
config.py - Runtime configuration & filesystem layout for the GCM Platform.

Two directory roles:
  BUNDLE_DIR  read-only: code, templates, static assets and *seed* data shipped
              with the application (inside the PyInstaller bundle when frozen).
  DATA_DIR    writable: the user's working copy of countries data, the
              surveillance ledger, user-created alerts/products/certificates,
              action items, settings and the last document-audit report.

Writing into BUNDLE_DIR is a bug in one-file PyInstaller builds (it is a temp
folder that is deleted on exit), so every mutable file lives in DATA_DIR.
"""
import json
import os
import shutil
import sys
import threading

APP_NAME = "GCM Platform"
APP_VERSION = "2.0.0"
APP_CODENAME = "Horizon"

IS_FROZEN = bool(getattr(sys, "frozen", False)) and hasattr(sys, "_MEIPASS")
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BUNDLE_DIR = sys._MEIPASS if IS_FROZEN else CURRENT_DIR


def _default_data_dir():
    override = os.environ.get("GCM_DATA_DIR", "").strip()
    if override:
        return os.path.abspath(override)
    if IS_FROZEN:
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "GCM_Platform", "data")
    return os.path.join(CURRENT_DIR, "data")


DATA_DIR = _default_data_dir()
SEED_FILES = ("countries_data.json", "surveillance_log.json")

DEFAULT_SETTINGS = {
    "company_name": "SanDisk",
    "port": 5000,
    "open_browser": True,
    "anthropic_api_key": "",
    "ai_model": "claude-opus-5",
    "ai_enabled": True,
    "surveillance_auto_scan_hours": 0,
    "default_category": "external_ssd_powered",
    "theme": "dark",
}

_settings_lock = threading.RLock()


def ensure_data_dir():
    """Create DATA_DIR and copy seed files on first run. Idempotent."""
    os.makedirs(DATA_DIR, exist_ok=True)
    for name in SEED_FILES:
        dest = os.path.join(DATA_DIR, name)
        src = os.path.join(BUNDLE_DIR, name)
        if not os.path.exists(dest) and os.path.exists(src):
            shutil.copyfile(src, dest)
    return DATA_DIR


def data_path(*parts):
    return os.path.join(DATA_DIR, *parts)


def bundle_path(*parts):
    return os.path.join(BUNDLE_DIR, *parts)


def atomic_write_json(path, payload, indent=2):
    """Write JSON to a temp file and replace, so a crash never leaves a half-written file."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=indent, ensure_ascii=False)
    os.replace(tmp, path)


def read_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def load_settings():
    with _settings_lock:
        data = read_json(data_path("settings.json"), {}) or {}
        merged = dict(DEFAULT_SETTINGS)
        merged.update({k: v for k, v in data.items() if k in DEFAULT_SETTINGS})
        return merged


def save_settings(updates):
    with _settings_lock:
        current = load_settings()
        for k, v in (updates or {}).items():
            if k in DEFAULT_SETTINGS:
                current[k] = v
        atomic_write_json(data_path("settings.json"), current)
        return current


def get_anthropic_api_key():
    """Environment variable wins over the saved setting."""
    env_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if env_key:
        return env_key
    return (load_settings().get("anthropic_api_key") or "").strip()


def public_settings():
    """Settings safe to send to the browser (API key masked)."""
    s = load_settings()
    key = get_anthropic_api_key()
    s["anthropic_api_key"] = (key[:7] + "…" + key[-4:]) if len(key) > 12 else ("configured" if key else "")
    s["api_key_configured"] = bool(key)
    s["api_key_from_env"] = bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())
    s["data_dir"] = DATA_DIR
    s["bundle_dir"] = BUNDLE_DIR
    s["frozen"] = IS_FROZEN
    s["version"] = APP_VERSION
    s["codename"] = APP_CODENAME
    return s
