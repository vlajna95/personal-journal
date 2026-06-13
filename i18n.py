"""Lightweight translation engine for Personal Journal.

.lng files live in the locales/ directory.
Format: one "key = value" pair per line.
  - Lines starting with # are comments.
  - Empty lines are ignored.
  - Values may contain {placeholder} tokens for str.format_map().

English is always loaded first as a base layer; the requested language
is then overlaid on top, so a partial translation still works.
"""

import locale
from pathlib import Path
from typing import Optional

LOCALES_DIR = Path(__file__).parent / "locales"

_translations: dict[str, str] = {}
_current_code: str = "en"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_lng(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    with path.open(encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if not line or line.lstrip().startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip()
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_available_languages() -> list[dict]:
    """Return [{code, name}, ...] for every .lng file found in locales/."""
    langs: list[dict] = []
    for f in sorted(LOCALES_DIR.glob("*.lng")):
        try:
            data = _parse_lng(f)
        except OSError:
            continue
        langs.append({"code": f.stem, "name": data.get("lang.name", f.stem)})
    return langs


def detect_system_language() -> str:
    """Return an ISO 639-1 code (e.g. 'en', 'es') from the OS locale."""
    try:
        code, _ = locale.getdefaultlocale()
        if code:
            return code.split("_")[0].lower()
    except Exception:
        pass
    return "en"


def best_available_language(preferred: str) -> str:
    """Return *preferred* if a .lng file exists for it, otherwise 'en'."""
    available = {lang["code"] for lang in get_available_languages()}
    return preferred if preferred in available else "en"


def load(language_code: str) -> None:
    """Load translations for *language_code*, falling back to English."""
    global _translations, _current_code

    fallback = LOCALES_DIR / "en.lng"
    target = LOCALES_DIR / f"{language_code}.lng"

    # Start with English base
    _translations = _parse_lng(fallback) if fallback.exists() else {}

    if language_code != "en" and target.exists():
        _translations.update(_parse_lng(target))
        _current_code = language_code
    else:
        _current_code = "en"


def current_code() -> str:
    return _current_code


def format_date(dt, fmt: str) -> str:
    """Format *dt* using translated month/weekday names.

    Handles %B (full month name) and %A (full weekday name) via .lng keys
    so dates are displayed in the app language regardless of system locale.
    All other strftime directives are passed through to strftime unchanged.
    """
    if "%B" in fmt:
        fmt = fmt.replace("%B", t(f"date.month.{dt.month}"))
    if "%A" in fmt:
        fmt = fmt.replace("%A", t(f"date.weekday.{dt.weekday()}"))
    return dt.strftime(fmt)


def t(key: str, **kwargs) -> str:
    """Look up *key* and optionally format with **kwargs.

    Falls back to the key itself if no translation is found.
    """
    value = _translations.get(key, key)
    if kwargs:
        try:
            value = value.format_map(kwargs)
        except (KeyError, ValueError):
            pass
    return value
