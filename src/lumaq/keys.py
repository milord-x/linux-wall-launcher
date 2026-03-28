from __future__ import annotations

from collections.abc import Iterable

import gi

gi.require_version("Gdk", "4.0")
from gi.repository import Gdk


def key_char(keyval: int) -> str:
    codepoint = Gdk.keyval_to_unicode(keyval)
    if not codepoint:
        return ""
    return chr(codepoint).casefold()


def is_quit_shortcut(keyval: int, state: Gdk.ModifierType, quit_chars: Iterable[str]) -> bool:
    if not (state & Gdk.ModifierType.CONTROL_MASK):
        return False
    pressed = key_char(keyval)
    if not pressed:
        return False
    allowed = {char.casefold() for char in quit_chars if char}
    return pressed in allowed
