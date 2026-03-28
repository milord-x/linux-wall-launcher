from __future__ import annotations

import os
import shlex
import tomllib
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional


def _env(*names: str) -> Optional[str]:
    for name in names:
        value = os.environ.get(name)
        if value is not None and value.strip():
            return value.strip()
    return None


def _expand_path(value: str) -> str:
    return os.path.abspath(os.path.expanduser(value))


def resolve_config_path(path: Optional[str] = None) -> str:
    raw = path or _env("LUMAQ_CONFIG", "LAUNCHER_CONFIG") or "~/.config/lumaq/config.toml"
    return _expand_path(raw)


def _read_toml(path: str) -> Mapping[str, Any]:
    try:
        with open(path, "rb") as handle:
            data = tomllib.load(handle)
    except FileNotFoundError:
        return {}
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _section(data: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = data.get(key, {})
    return value if isinstance(value, dict) else {}


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [item for item in shlex.split(value) if item]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _int_value(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _bool_value(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return default


def default_config_text() -> str:
    return """# ~/.config/lumaq/config.toml
#
# Minimal config. Delete any option you do not need.

[app]
backend = "auto"
media_dir = "~/Pictures/Wallpapers"
output = ""
poll_interval = 1
hide_on_escape = true
show_preview_meta = true
quit_chars = ["q", "й"]
mpvpaper_args = ["-f", "-s", "-o", "no-audio loop"]

[theme]
mode = "auto"
accent_color = "#4da3ff"
# panel_color = "#000000"
# panel_soft_color = "#000000"

[window]
width = 940
height = 520
preview_width = 540
sidebar_width = 270
resizable = false
manage_geometry = false
anchor = "center"
margin_x = 0
margin_y = 0
"""


def write_default_config(path: str, overwrite: bool = False) -> bool:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path) and not overwrite:
        return False
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(default_config_text())
    return True


@dataclass(slots=True)
class WindowConfig:
    width: int = 940
    height: int = 520
    preview_width: int = 540
    sidebar_width: int = 270
    resizable: bool = False
    manage_geometry: bool = False
    anchor: str = "center"
    margin_x: int = 0
    margin_y: int = 0


@dataclass(slots=True)
class AppConfig:
    app_id: str = "dev.milordx.Lumaq"
    title: str = "Lumaq"
    config_dir: str = _expand_path("~/.config/lumaq")
    config_path: str = _expand_path("~/.config/lumaq/config.toml")
    media_dir: str = _expand_path("~/Pictures/Wallpapers")
    swww_cache_dir: str = _expand_path("~/.cache/swww")
    cache_dir: str = _expand_path("~/.cache/lumaq")
    hyprpaper_conf: str = _expand_path("~/.config/hypr/hyprpaper.conf")
    fehbg_path: str = _expand_path("~/.fehbg")
    nitrogen_conf: str = _expand_path("~/.config/nitrogen/bg-saved.cfg")
    backend: str = "auto"
    output: Optional[str] = None
    theme: str = "auto"
    accent_color: str = "#4da3ff"
    panel_color: Optional[str] = None
    panel_soft_color: Optional[str] = None
    poll_interval: int = 1
    hide_on_escape: bool = True
    show_preview_meta: bool = True
    quit_chars: list[str] = field(default_factory=lambda: ["q", "й"])
    mpvpaper_args: list[str] = field(default_factory=lambda: ["-f", "-s", "-o", "no-audio loop"])
    window: WindowConfig = field(default_factory=WindowConfig)

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "AppConfig":
        path = resolve_config_path(config_path)
        config = cls(config_dir=os.path.dirname(path), config_path=path)
        config.apply_file(_read_toml(path))
        config.apply_env()
        return config

    def apply_file(self, data: Mapping[str, Any]) -> None:
        app = _section(data, "app")
        theme = _section(data, "theme")
        window = _section(data, "window")

        media_dir = app.get("media_dir")
        if isinstance(media_dir, str) and media_dir.strip():
            self.media_dir = _expand_path(media_dir)

        backend = app.get("backend")
        if isinstance(backend, str) and backend.strip():
            self.backend = backend.strip().lower()

        output = app.get("output")
        if isinstance(output, str):
            self.output = output.strip() or None

        self.poll_interval = max(0, _int_value(app.get("poll_interval"), self.poll_interval))
        self.hide_on_escape = _bool_value(app.get("hide_on_escape"), self.hide_on_escape)
        self.show_preview_meta = _bool_value(app.get("show_preview_meta"), self.show_preview_meta)

        quit_chars = _string_list(app.get("quit_chars"))
        if quit_chars:
            self.quit_chars = quit_chars

        mpvpaper_args = _string_list(app.get("mpvpaper_args"))
        if mpvpaper_args:
            self.mpvpaper_args = mpvpaper_args

        theme_mode = theme.get("mode")
        if isinstance(theme_mode, str) and theme_mode.strip():
            self.theme = theme_mode.strip().lower()

        accent = theme.get("accent_color")
        if isinstance(accent, str) and accent.strip():
            self.accent_color = accent.strip()

        panel = theme.get("panel_color")
        if isinstance(panel, str) and panel.strip():
            self.panel_color = panel.strip()

        panel_soft = theme.get("panel_soft_color")
        if isinstance(panel_soft, str) and panel_soft.strip():
            self.panel_soft_color = panel_soft.strip()

        self.window.width = max(640, _int_value(window.get("width"), self.window.width))
        self.window.height = max(360, _int_value(window.get("height"), self.window.height))
        self.window.preview_width = max(320, _int_value(window.get("preview_width"), self.window.preview_width))
        self.window.sidebar_width = max(220, _int_value(window.get("sidebar_width"), self.window.sidebar_width))
        self.window.resizable = _bool_value(window.get("resizable"), self.window.resizable)
        self.window.manage_geometry = _bool_value(window.get("manage_geometry"), self.window.manage_geometry)

        anchor = window.get("anchor")
        if isinstance(anchor, str) and anchor.strip():
            self.window.anchor = anchor.strip().lower()

        self.window.margin_x = _int_value(window.get("margin_x"), self.window.margin_x)
        self.window.margin_y = _int_value(window.get("margin_y"), self.window.margin_y)

    def apply_env(self) -> None:
        output = _env("LUMAQ_OUTPUT", "LAUNCHER_OUTPUT")
        if output is not None:
            self.output = output or None

        backend = _env("LUMAQ_BACKEND", "LAUNCHER_BACKEND")
        if backend is not None:
            self.backend = backend.lower()

        theme = _env("LUMAQ_THEME", "LAUNCHER_THEME")
        if theme is not None:
            self.theme = theme.lower()

        accent = _env("LUMAQ_ACCENT", "LAUNCHER_ACCENT")
        if accent is not None:
            self.accent_color = accent

        panel = _env("LUMAQ_PANEL_COLOR")
        if panel is not None:
            self.panel_color = panel

        panel_soft = _env("LUMAQ_PANEL_SOFT_COLOR")
        if panel_soft is not None:
            self.panel_soft_color = panel_soft

        media_dir = _env("LUMAQ_MEDIA_DIR", "WALL_DIR")
        if media_dir is not None:
            self.media_dir = _expand_path(media_dir)

        show_preview_meta = _env("LUMAQ_SHOW_PREVIEW_META")
        if show_preview_meta is not None:
            self.show_preview_meta = _bool_value(show_preview_meta, self.show_preview_meta)

        quit_chars = _env("LUMAQ_QUIT_CHARS")
        if quit_chars is not None:
            parsed = [item.strip() for item in quit_chars.split(",") if item.strip()]
            if parsed:
                self.quit_chars = parsed

        mpvpaper_args = _env("LUMAQ_MPVPAPER_ARGS", "MPVPAPER_ARGS")
        if mpvpaper_args is not None:
            parsed = [item for item in shlex.split(mpvpaper_args) if item]
            if parsed:
                self.mpvpaper_args = parsed
