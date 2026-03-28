# Lumaq

`Lumaq` is a GTK4 launcher for Linux that keeps the current wallpaper visible, tracks external wallpaper changes, and can switch both static and video wallpapers.

It is packaged as an installable program, not as a single local script.

## What it supports

- Fast reopen after first launch through single-instance hide/show behavior
- Three close paths:
  - repeat your window-manager bind via `lumaq-toggle`
  - `Esc` hides the window
  - `Ctrl+Q` quits the process, with configurable quit characters for non-English layouts
- Live refresh when wallpaper changes outside the launcher
- App search and launch from desktop entries
- Wallpaper switching for `swww`, `mpvpaper`, `hyprpaper`, `swaybg`, `feh`, and `nitrogen`
- Video wallpaper preview through generated thumbnails via `ffmpeg`
- Theme support with `auto`, `dark`, `light`, accent color, and optional panel color overrides
- Config file in `~/.config/lumaq/config.toml`
- Better portability across Linux desktops through backend auto-detection plus explicit backend forcing

## Install

System packages you usually need:

```bash
# Debian / Ubuntu
sudo apt install python3 python3-gi gir1.2-gtk-4.0 ffmpeg

# Arch
sudo pacman -S python python-gobject gtk4 ffmpeg

# Fedora
sudo dnf install python3-gobject gtk4 ffmpeg
```

Install as a program:

```bash
pipx install git+https://github.com/milord-x/lumaq.git
```

That gives you:

```bash
lumaq
lumaq-toggle
```

Run from source:

```bash
python3 -m lumaq.main
```

## Config path

The active config file is:

```bash
~/.config/lumaq/config.toml
```

Print it directly:

```bash
lumaq --print-config-path
```

Create the default config:

```bash
lumaq --write-default-config
```

## Config example

```toml
[app]
backend = "auto"
media_dir = "~/Pictures/Wallpapers"
output = ""
poll_interval = 1
hide_on_escape = true
quit_chars = ["q", "й"]

[theme]
mode = "dark"
accent_color = "#4da3ff"
# panel_color = "#000000"
# panel_soft_color = "#000000"

[window]
width = 940
height = 520
preview_width = 540
sidebar_width = 270
resizable = false
anchor = "center"
margin_x = 0
margin_y = 0
```

`anchor`, `margin_x`, and `margin_y` are used by `lumaq-toggle` on Hyprland when it places the floating window.

## Controls

- `Esc`: hide launcher
- `Ctrl+Q`: quit launcher process
- `Enter`: launch selected app
- Swipe left/right on the preview pane: switch wallpaper or video wallpaper

## WM binding

For Hyprland, bind the toggle helper instead of the GUI binary:

```text
bind = $mainMod, R, exec, lumaq-toggle
windowrule = match:class ^(dev\.milordx\.Lumaq)$, float on
```

That gives repeated-bind close behavior without killing the resident process on every open.

## Notes on portability

- On Hyprland, `swww`, `hyprpaper`, and `mpvpaper` are supported
- On wlroots compositors, `swaybg` is supported
- On X11 setups, `feh` and `nitrogen` are supported
- If auto-detection is not correct on a given machine, force the backend in config or with `--backend`
- If your wallpaper backend is output-specific, set `output`
- If you want local-only pure black styling, set `panel_color` and `panel_soft_color` in your config instead of patching the package

## Development

Project layout:

```text
src/lumaq/config.py
src/lumaq/keys.py
src/lumaq/backends.py
src/lumaq/apps.py
src/lumaq/preview.py
src/lumaq/styles.py
src/lumaq/app.py
src/lumaq/toggle.py
src/lumaq/main.py
```

Local sanity check:

```bash
python3 -m py_compile lumaq src/lumaq/*.py
```
