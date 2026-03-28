# Linux Wall Launcher

`Linux Wall Launcher` is a GTK4 desktop launcher for Linux with a live wallpaper pane. It opens fast, stays resident after the first launch, and can switch wallpapers with swipe gestures while still acting as an application launcher.

It is packaged as an installable program, not just a one-file script.

## What it supports

- Fast reopen after first launch through single-instance hide/show behavior
- Live refresh of the current wallpaper while the launcher is open or reopened
- App search and launch from desktop entries
- Wallpaper switching for:
  - `swww`
  - `mpvpaper`
  - `hyprpaper`
  - `swaybg`
  - `feh`
  - `nitrogen`
- Video wallpaper browsing when `mpvpaper` is the active backend
- Video wallpaper preview through generated thumbnails via `ffmpeg`
- Theme selection: `auto`, `dark`, `light`
- Accent color override
- Monitor/output override for output-aware backends
- Better portability across Linux desktops through backend auto-detection plus explicit backend forcing

## Install

System packages you usually need:

```bash
# Debian / Ubuntu
sudo apt install python3 python3-gi gir1.2-gtk-4.0

# Arch
sudo pacman -S python python-gobject gtk4

# Fedora
sudo dnf install python3-gobject gtk4
```

Install as a program:

```bash
pipx install git+https://github.com/milord-x/linux-wall-launcher.git
```

That gives you the executable:

```bash
wall-launcher
```

You can also run from source:

```bash
python3 -m linux_wall_launcher.main
```

## Configuration

Environment variables:

- `LAUNCHER_BACKEND=auto|swww|mpvpaper|hyprpaper|swaybg|feh|nitrogen`
- `LAUNCHER_OUTPUT=<monitor-name>`
- `WALL_DIR=/path/to/media`
- `LAUNCHER_THEME=auto|dark|light`
- `LAUNCHER_ACCENT=#4da3ff`
- `MPVPAPER_ARGS="-f -s -o 'no-audio loop'"`

CLI flags:

```bash
wall-launcher --backend mpvpaper --theme dark --accent '#7cd47b'
```

## Controls

- `Esc`: hide launcher
- `Ctrl+Q`: quit launcher process
- `Enter`: launch selected app
- Swipe left/right on the preview pane: switch wallpaper or video wallpaper

## Notes on portability

- On Hyprland, `swww`, `hyprpaper`, and `mpvpaper` are supported
- On wlroots compositors, `swaybg` is supported
- On X11 setups, `feh` and `nitrogen` are supported
- If auto-detection is not correct on a given machine, force the backend with `LAUNCHER_BACKEND`
- If your wallpaper backend is output-specific, set `LAUNCHER_OUTPUT`

## Desktop file

A desktop entry template is included at:

`assets/wall-launcher.desktop`

You can install it manually into:

```bash
~/.local/share/applications/
```

## Development

Project layout:

```text
src/linux_wall_launcher/config.py
src/linux_wall_launcher/backends.py
src/linux_wall_launcher/apps.py
src/linux_wall_launcher/styles.py
src/linux_wall_launcher/app.py
src/linux_wall_launcher/main.py
```

Local sanity check:

```bash
python3 -m py_compile launcher src/linux_wall_launcher/*.py
```
