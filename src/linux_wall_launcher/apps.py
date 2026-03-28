from __future__ import annotations

from typing import List, Optional, Tuple

from gi.repository import Gio

_APPS_ALL: Optional[List[Gio.AppInfo]] = None
_APPS_SEARCH_TEXT: Optional[List[str]] = None


def app_label(app: Gio.AppInfo) -> str:
    name = app.get_display_name() or app.get_name() or ""
    return name.strip()


def app_search_text(app: Gio.AppInfo) -> str:
    parts = [app_label(app)]
    try:
        did = app.get_id() if hasattr(app, "get_id") else ""
        exe = app.get_executable() if hasattr(app, "get_executable") else ""
        parts += [did or "", exe or ""]
    except Exception:
        pass
    return " ".join(part for part in parts if part).lower()


def list_desktop_apps_cached() -> Tuple[List[Gio.AppInfo], List[str]]:
    global _APPS_ALL, _APPS_SEARCH_TEXT

    if _APPS_ALL is not None and _APPS_SEARCH_TEXT is not None:
        return _APPS_ALL, _APPS_SEARCH_TEXT

    apps = [app for app in Gio.AppInfo.get_all() if app.should_show()]
    apps.sort(key=lambda app: app_label(app).lower())

    _APPS_ALL = apps
    _APPS_SEARCH_TEXT = [app_search_text(app) for app in apps]
    return _APPS_ALL, _APPS_SEARCH_TEXT


def is_subsequence(needle: str, haystack: str) -> bool:
    iterator = iter(haystack)
    return all(char in iterator for char in needle)


def score_match(query: str, text: str) -> int:
    if not query:
        return 1
    if text.startswith(query):
        return 4000
    for word in text.split():
        if word.startswith(query):
            return 3000
    if query in text:
        return 2000 - (len(text) - len(query))
    if len(query) >= 2 and is_subsequence(query, text):
        return 900 - (len(text) - len(query))
    return 0

