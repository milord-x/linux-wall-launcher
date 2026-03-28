from __future__ import annotations

import argparse
import os

from .app import LauncherApplication
from .config import AppConfig, resolve_config_path, write_default_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lumaq app launcher with wallpaper switching")
    parser.add_argument("--config", help="Path to config TOML file")
    parser.add_argument("--print-config-path", action="store_true", help="Print the active config path and exit")
    parser.add_argument("--write-default-config", action="store_true", help="Write the default config if it does not exist")
    parser.add_argument("--backend", choices=["auto", "swww", "mpvpaper", "hyprpaper", "swaybg", "feh", "nitrogen"])
    parser.add_argument("--output", help="Monitor/output name for output-aware wallpaper backends")
    parser.add_argument("--media-dir", help="Directory containing wallpapers or video wallpapers")
    parser.add_argument("--theme", choices=["auto", "dark", "light"], help="Launcher theme")
    parser.add_argument("--accent", help="Accent color in #RRGGBB")
    return parser.parse_args()


def build_config(args: argparse.Namespace) -> AppConfig:
    config = AppConfig.load(args.config)
    if args.backend:
        config.backend = args.backend
    if args.output:
        config.output = args.output
    if args.media_dir:
        config.media_dir = os.path.abspath(os.path.expanduser(args.media_dir))
    if args.theme:
        config.theme = args.theme
    if args.accent:
        config.accent_color = args.accent
    return config


def main() -> int:
    args = parse_args()
    config_path = resolve_config_path(args.config)

    if args.print_config_path:
        print(config_path)
        return 0

    if args.write_default_config:
        created = write_default_config(config_path)
        if created:
            print(f"Wrote default config to {config_path}")
        else:
            print(f"Config already exists at {config_path}")
        return 0

    app = LauncherApplication(build_config(args))
    return app.run(None)


if __name__ == "__main__":
    raise SystemExit(main())
