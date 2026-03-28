from __future__ import annotations

import os
import shlex
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(slots=True)
class AppConfig:
    app_id: str = "dev.milordx.LinuxWallLauncher"
    title: str = "Linux Wall Launcher"
    media_dir: str = os.path.expanduser("~/Pictures/Wallpapers")
    swww_cache_dir: str = os.path.expanduser("~/.cache/swww")
    cache_dir: str = os.path.expanduser("~/.cache/linux-wall-launcher")
    hyprpaper_conf: str = os.path.expanduser("~/.config/hypr/hyprpaper.conf")
    fehbg_path: str = os.path.expanduser("~/.fehbg")
    nitrogen_conf: str = os.path.expanduser("~/.config/nitrogen/bg-saved.cfg")
    backend: str = "auto"
    output: Optional[str] = None
    theme: str = "auto"
    accent_color: str = "#4da3ff"
    window_width: int = 940
    window_height: int = 520
    mpvpaper_args: List[str] = field(default_factory=lambda: ["-f", "-s", "-o", "no-audio loop"])

    @classmethod
    def from_env(cls) -> "AppConfig":
        output = (os.environ.get("LAUNCHER_OUTPUT") or "").strip() or None
        mpvpaper_args = (os.environ.get("MPVPAPER_ARGS") or "").strip()
        theme = (os.environ.get("LAUNCHER_THEME") or "auto").strip().lower() or "auto"
        backend = (os.environ.get("LAUNCHER_BACKEND") or "auto").strip().lower() or "auto"
        accent = (os.environ.get("LAUNCHER_ACCENT") or "#4da3ff").strip() or "#4da3ff"
        media_dir = os.path.expanduser(os.environ.get("WALL_DIR", "~/Pictures/Wallpapers"))
        return cls(
            media_dir=media_dir,
            backend=backend,
            output=output,
            theme=theme,
            accent_color=accent,
            mpvpaper_args=shlex.split(mpvpaper_args) if mpvpaper_args else ["-f", "-s", "-o", "no-audio loop"],
        )
