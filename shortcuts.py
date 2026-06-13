"""Keyboard shortcut helpers: parse/format display strings, load/save per-action overrides."""

import wx

import settings


def combo_to_display(mods: int, keycode: int) -> str:
    """Convert accelerator flags + keycode to a human-readable string like 'Ctrl+Shift+F4'."""
    parts = []
    if mods & wx.ACCEL_CTRL:  parts.append("Ctrl")
    if mods & wx.ACCEL_ALT:   parts.append("Alt")
    if mods & wx.ACCEL_SHIFT: parts.append("Shift")
    parts.append(_keycode_to_str(keycode))
    return "+".join(parts)


def _keycode_to_str(keycode: int) -> str:
    if wx.WXK_F1 <= keycode <= wx.WXK_F12:
        return f"F{keycode - wx.WXK_F1 + 1}"
    if 32 <= keycode <= 127:
        return chr(keycode).upper()
    return {
        wx.WXK_TAB:      "Tab",
        wx.WXK_RETURN:   "Enter",
        wx.WXK_SPACE:    "Space",
        wx.WXK_DELETE:   "Del",
        wx.WXK_INSERT:   "Ins",
        wx.WXK_HOME:     "Home",
        wx.WXK_END:      "End",
        wx.WXK_PAGEUP:   "PgUp",
        wx.WXK_PAGEDOWN: "PgDn",
        wx.WXK_UP:       "Up",
        wx.WXK_DOWN:     "Down",
        wx.WXK_LEFT:     "Left",
        wx.WXK_RIGHT:    "Right",
    }.get(keycode, f"Key{keycode}")


def parse_display(text: str):
    """Parse 'Ctrl+Shift+L' → (mods, keycode).  Returns None on failure."""
    if not text:
        return None
    parts = [p.strip() for p in text.strip().split("+")]
    if len(parts) < 2:
        return None
    mods = 0
    for p in parts[:-1]:
        lp = p.lower()
        if lp == "ctrl":    mods |= wx.ACCEL_CTRL
        elif lp == "alt":   mods |= wx.ACCEL_ALT
        elif lp == "shift": mods |= wx.ACCEL_SHIFT
    if mods == 0:
        return None
    keycode = _str_to_keycode(parts[-1])
    if keycode is None:
        return None
    return mods, keycode


def _str_to_keycode(s: str):
    if len(s) == 1 and s.isalpha():
        return ord(s.upper())
    if len(s) == 1 and s.isdigit():
        return ord(s)
    su = s.upper()
    if su.startswith("F") and su[1:].isdigit():
        n = int(su[1:])
        if 1 <= n <= 12:
            return wx.WXK_F1 + n - 1
    return {
        "TAB":    wx.WXK_TAB,
        "ENTER":  wx.WXK_RETURN,
        "SPACE":  wx.WXK_SPACE,
        "DEL":    wx.WXK_DELETE,
        "DELETE": wx.WXK_DELETE,
        "INS":    wx.WXK_INSERT,
        "INSERT": wx.WXK_INSERT,
        "HOME":   wx.WXK_HOME,
        "END":    wx.WXK_END,
        "PGUP":   wx.WXK_PAGEUP,
        "PGDN":   wx.WXK_PAGEDOWN,
        "UP":     wx.WXK_UP,
        "DOWN":   wx.WXK_DOWN,
        "LEFT":   wx.WXK_LEFT,
        "RIGHT":  wx.WXK_RIGHT,
    }.get(su)


def load_shortcut(action_key: str, default_display: str) -> str:
    """Return the saved display string, or the default if nothing is saved or unparseable."""
    saved = settings.get(f"shortcut.{action_key}", "")
    if saved and parse_display(saved) is not None:
        return saved
    return default_display


def save_shortcut(action_key: str, display: str) -> None:
    settings.set(f"shortcut.{action_key}", display)


def reset_shortcut(action_key: str) -> None:
    settings.set(f"shortcut.{action_key}", "")
