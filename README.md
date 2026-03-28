# GTK Wall Launcher

Minimal GTK4 app launcher with a wallpaper preview pane and swipe-based wallpaper switching.

## Features

- Fast startup path for `swww` by reading `~/.cache/swww/*` instead of calling `swww query`
- Single-instance behavior: reopen is instant after the first launch
- Supports multiple wallpaper backends:
  - `swww`
  - `mpvpaper`
  - `hyprpaper`
- Video wallpaper aware: when `mpvpaper` is active, swipe switches through media files, not just images
- Fallback wallpaper directory detection from the current wallpaper path

## Controls

- `Esc` hides the launcher
- `Ctrl+Q` fully quits the launcher
- `Enter` launches the selected app
- Swipe left/right on the preview area to switch wallpaper/media

## Configuration

Environment variables:

- `WALL_DIR` is not required, but you can edit the script default if you want a fixed media directory
- `LAUNCHER_BACKEND=auto|swww|mpvpaper|hyprpaper`
- `LAUNCHER_OUTPUT=<monitor-name>` for monitor-specific backends
- `MPVPAPER_ARGS="..."` to override default `mpvpaper` flags

## Run

```bash
chmod +x ./launcher
./launcher
```

## Requirements

- Python 3
- GTK4 / PyGObject
- One of the supported wallpaper backends installed
