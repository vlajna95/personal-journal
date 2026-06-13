"""Persistent user preferences for Personal Journal.

Stored as a plain INI file (settings.ini) next to the application.
This file is intentionally unencrypted — it holds no sensitive data,
and must be readable before the journal database is unlocked.
"""

import configparser
from pathlib import Path

_SETTINGS_PATH = Path(__file__).parent / "settings.ini"
_SECTION = "General"


def _load() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    if _SETTINGS_PATH.exists():
        cfg.read(str(_SETTINGS_PATH), encoding="utf-8")
    if _SECTION not in cfg:
        cfg[_SECTION] = {}
    return cfg


def get_path() -> Path:
    return _SETTINGS_PATH


def get(key: str, fallback: str = "") -> str:
    return _load()[_SECTION].get(key, fallback)


def set(key: str, value: str) -> None:
    cfg = _load()
    cfg[_SECTION][key] = value
    with _SETTINGS_PATH.open("w", encoding="utf-8") as fh:
        cfg.write(fh)
