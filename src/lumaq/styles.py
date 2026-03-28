from __future__ import annotations

import os
from typing import Optional

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk

_CSS_PROVIDER: Gtk.CssProvider | None = None


def prefer_dark(theme: str) -> bool:
    if theme == "dark":
        return True
    if theme == "light":
        return False

    gtk_theme = (os.environ.get("GTK_THEME") or "").lower()
    if ":dark" in gtk_theme or "dark" in gtk_theme:
        return True
    return True


def build_css(theme: str, accent: str, panel_override: Optional[str], panel_soft_override: Optional[str]) -> str:
    dark = prefer_dark(theme)
    if dark:
        panel = panel_override or "#08090b"
        panel_soft = panel_soft_override or "#111317"
        fg = "#eaeaea"
        fg_soft = "#9ea7b3"
        border = "rgba(255,255,255,0.10)"
        border_focus = "rgba(255,255,255,0.22)"
        row_hover = "rgba(255,255,255,0.05)"
    else:
        panel = panel_override or "#f6f7f9"
        panel_soft = panel_soft_override or "#ffffff"
        fg = "#15181c"
        fg_soft = "#5f6a77"
        border = "rgba(0,0,0,0.10)"
        border_focus = "rgba(0,0,0,0.18)"
        row_hover = "rgba(0,0,0,0.04)"

    return f"""
window {{
  border-radius: 0px;
  background: {panel};
  color: {fg};
}}

overshoot.top, overshoot.bottom, overshoot.left, overshoot.right,
undershoot.top, undershoot.bottom, undershoot.left, undershoot.right {{
  background: transparent;
}}

#root {{
  background: {panel};
}}

#preview-meta {{
  color: {fg_soft};
  font-size: 12px;
}}

#search {{
  background: {panel_soft};
  color: {fg};
  border: 1px solid {border};
  border-radius: 12px;
  padding: 10px 12px;
  caret-color: {accent};
}}

#search:focus {{
  border: 1px solid {border_focus};
  box-shadow: 0 0 0 2px alpha({accent}, 0.20);
}}

#apps row {{
  border-radius: 10px;
}}

#apps row:hover {{
  background: {row_hover};
}}

#apps label {{
  font-weight: 700;
}}
"""


def install_css(theme: str, accent: str, panel_override: Optional[str], panel_soft_override: Optional[str]) -> None:
    global _CSS_PROVIDER

    display = Gdk.Display.get_default()
    if display is None:
        return

    css = build_css(theme, accent, panel_override, panel_soft_override)
    provider = Gtk.CssProvider()
    provider.load_from_data(css.encode())
    Gtk.StyleContext.add_provider_for_display(
        display,
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )
    _CSS_PROVIDER = provider
