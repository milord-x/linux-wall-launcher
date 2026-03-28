from __future__ import annotations

import argparse

from .app import LauncherApplication
from .config import AppConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Linux app launcher with wallpaper switching")
    parser.add_argument("--backend", choices=["auto", "swww", "mpvpaper", "hyprpaper", "swaybg", "feh", "nitrogen"])
    parser.add_argument("--output", help="Monitor/output name for output-aware wallpaper backends")
    parser.add_argument("--media-dir", help="Directory containing wallpapers or video wallpapers")
    parser.add_argument("--theme", choices=["auto", "dark", "light"], help="Launcher theme")
    parser.add_argument("--accent", help="Accent color in #RRGGBB")
    return parser.parse_args()


def build_config(args: argparse.Namespace) -> AppConfig:
    config = AppConfig.from_env()
    if args.backend:
        config.backend = args.backend
    if args.output:
        config.output = args.output
    if args.media_dir:
        config.media_dir = args.media_dir
    if args.theme:
        config.theme = args.theme
    if args.accent:
        config.accent_color = args.accent
    return config


def main() -> int:
    args = parse_args()
    app = LauncherApplication(build_config(args))
    return app.run(None)


if __name__ == "__main__":
    raise SystemExit(main())

