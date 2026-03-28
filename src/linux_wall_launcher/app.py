from __future__ import annotations

import threading
from typing import List, Optional, Tuple

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gio, GLib, Gtk

from .apps import app_label, list_desktop_apps_cached, score_match
from .backends import BackendManager, WallpaperState, run
from .config import AppConfig
from .preview import resolve_preview_path
from .styles import install_css


class LauncherApplication(Gtk.Application):
    def __init__(self, config: AppConfig):
        super().__init__(application_id=config.app_id, flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.config = config
        self.backend_manager = BackendManager(config)

        self.apps_all: List[Gio.AppInfo] = []
        self.apps_text: List[str] = []
        self.apps_filtered_idx: List[int] = []

        self.listbox: Gtk.ListBox = None  # type: ignore[assignment]
        self.search: Gtk.SearchEntry = None  # type: ignore[assignment]
        self.preview: Gtk.Picture = None  # type: ignore[assignment]
        self.preview_meta: Gtk.Label = None  # type: ignore[assignment]
        self.window: Gtk.ApplicationWindow = None  # type: ignore[assignment]

        self.current_state: Optional[WallpaperState] = None
        self.current_wallpaper: Optional[str] = None
        self.wallpapers: List[str] = []
        self.wall_idx = 0
        self.refresh_timer_started = False
        self.preview_job_path: Optional[str] = None

    def do_activate(self) -> None:
        if self.window is not None:
            self.window.present()
            GLib.idle_add(self.prepare_for_show)
            GLib.idle_add(self.refresh_wallpaper_state)
            GLib.idle_add(self.focus_search)
            return

        self.apps_all, self.apps_text = list_desktop_apps_cached()
        self.apps_filtered_idx = list(range(len(self.apps_all)))

        self.window = Gtk.ApplicationWindow(application=self)
        self.window.set_title(self.config.title)
        self.window.set_default_size(self.config.window_width, self.config.window_height)
        self.window.set_resizable(True)
        self.window.set_hide_on_close(True)

        install_css(self.config.theme, self.config.accent_color)

        root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        root.set_name("root")

        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        left.set_size_request(540, -1)
        left.set_hexpand(False)

        frame = Gtk.Frame()
        frame.set_hexpand(False)
        frame.set_vexpand(True)
        frame.set_size_request(540, int(540 * 4 / 5))

        self.preview = Gtk.Picture()
        self.preview.set_hexpand(False)
        self.preview.set_vexpand(True)
        self.preview.set_content_fit(Gtk.ContentFit.COVER)
        frame.set_child(self.preview)
        left.append(frame)

        self.preview_meta = Gtk.Label(xalign=0)
        self.preview_meta.set_name("preview-meta")
        self.preview_meta.set_wrap(True)
        self.preview_meta.set_margin_top(8)
        self.preview_meta.set_margin_start(6)
        self.preview_meta.set_margin_end(6)
        left.append(self.preview_meta)

        swipe = Gtk.GestureSwipe()
        swipe.connect("end", self.on_swipe_end)
        self.preview.add_controller(swipe)

        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        right.set_hexpand(True)
        right.set_vexpand(True)
        right.set_size_request(270, -1)
        right.set_margin_top(16)
        right.set_margin_bottom(16)
        right.set_margin_start(18)
        right.set_margin_end(16)

        topbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        topbar.set_hexpand(True)

        self.search = Gtk.SearchEntry()
        self.search.set_name("search")
        self.search.set_placeholder_text("Search applications…")
        self.search.set_hexpand(True)
        self.search.connect("search-changed", self.on_search_changed)
        self.search.connect("activate", self.on_activate_enter)
        topbar.append(self.search)

        scroller = Gtk.ScrolledWindow()
        scroller.set_hexpand(True)
        scroller.set_vexpand(True)
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.listbox = Gtk.ListBox()
        self.listbox.set_name("apps")
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.set_activate_on_single_click(True)
        self.listbox.connect("row-activated", self.on_row_activated)
        scroller.set_child(self.listbox)

        right.append(topbar)
        right.append(scroller)

        root.append(left)
        root.append(right)
        self.window.set_child(root)

        controller = Gtk.EventControllerKey()
        controller.connect("key-pressed", self.on_key)
        self.window.add_controller(controller)

        self.window.present()
        self.ensure_refresh_timer()
        GLib.idle_add(self.load_initial_state)
        GLib.idle_add(self.focus_search)

    def ensure_refresh_timer(self) -> None:
        if self.refresh_timer_started:
            return
        GLib.timeout_add_seconds(1, self.poll_wallpaper_state)
        self.refresh_timer_started = True

    def load_initial_state(self) -> bool:
        self.prepare_for_show()
        self.refresh_wallpaper_state()
        return False

    def prepare_for_show(self) -> None:
        if self.search is not None and self.search.get_text():
            self.search.set_text("")
        if self.listbox is not None and self.listbox.get_first_child() is not None:
            return
        if self.apps_all:
            self.apps_filtered_idx = list(range(len(self.apps_all)))
            self.populate_list()

    def refresh_wallpaper_state(self) -> bool:
        state = self.backend_manager.detect_state()
        previous = self.current_state
        self.current_state = state

        if state is None or not state.path:
            if self.preview_meta is not None:
                self.preview_meta.set_text("No supported wallpaper backend detected")
            if self.preview is not None:
                self.preview.set_paintable(None)
            return False

        if (
            previous is None
            or previous.path != state.path
            or previous.backend != state.backend
            or previous.output != state.output
        ):
            self.wallpapers = []

        self.current_wallpaper = state.path
        if self.preview_meta is not None:
            bits = [state.backend]
            if state.output:
                bits.append(state.output)
            bits.append(state.path.rsplit("/", 1)[-1])
            self.preview_meta.set_text(" / ".join(bits))

        if self.preview is not None:
            try:
                preview_path = resolve_preview_path(self.config, state, generate=False)
                if preview_path is None:
                    self.preview.set_paintable(None)
                    if state.media_kind == "video":
                        self.ensure_preview_job(state.path)
                else:
                    self.preview.set_filename(preview_path)
            except Exception:
                self.preview.set_paintable(None)
        return False

    def ensure_preview_job(self, path: str) -> None:
        if self.preview_job_path == path:
            return

        self.preview_job_path = path
        state = WallpaperState(backend="preview", path=path, media_kind="video")

        def worker() -> None:
            preview_path = resolve_preview_path(self.config, state, generate=True)
            GLib.idle_add(self.apply_generated_preview, path, preview_path)

        threading.Thread(target=worker, daemon=True).start()

    def apply_generated_preview(self, expected_path: str, preview_path: Optional[str]) -> bool:
        self.preview_job_path = None
        if (
            preview_path
            and self.current_state is not None
            and self.current_state.path == expected_path
            and self.preview is not None
        ):
            try:
                self.preview.set_filename(preview_path)
            except Exception:
                self.preview.set_paintable(None)
        return False

    def ensure_media_loaded(self) -> None:
        if self.wallpapers and (self.current_wallpaper is None or self.current_wallpaper in self.wallpapers):
            return
        self.wallpapers = self.backend_manager.list_media(self.current_wallpaper, self.current_state)
        if self.current_wallpaper and self.wallpapers:
            try:
                self.wall_idx = self.wallpapers.index(self.current_wallpaper)
            except ValueError:
                self.wall_idx = 0

    def focus_search(self) -> bool:
        if self.search is not None:
            self.search.grab_focus()
        return False

    def poll_wallpaper_state(self) -> bool:
        if self.window is not None and self.window.is_visible():
            self.refresh_wallpaper_state()
        return True

    def on_key(self, _controller, keyval, _keycode, state) -> bool:
        if keyval == Gdk.KEY_q and (state & Gdk.ModifierType.CONTROL_MASK):
            self.quit()
            return True
        if keyval == Gdk.KEY_Escape and self.window is not None:
            self.window.hide()
            return True
        return False

    def on_swipe_end(self, _gesture, vx: float, vy: float) -> None:
        if abs(vx) <= abs(vy) or abs(vx) < 200:
            return
        if self.current_state is None:
            self.current_state = self.backend_manager.detect_state()
        if self.current_state is None:
            return

        self.ensure_media_loaded()
        if not self.wallpapers:
            return

        if vx < 0:
            self.wall_idx = (self.wall_idx + 1) % len(self.wallpapers)
        else:
            self.wall_idx = (self.wall_idx - 1) % len(self.wallpapers)

        path = self.wallpapers[self.wall_idx]
        if not self.backend_manager.apply(self.current_state, path):
            return

        self.current_wallpaper = path
        self.current_state.path = path
        self.current_state.media_kind = "video" if path.lower().endswith((".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v")) else "image"
        if self.current_state.backend in {"mpvpaper", "swaybg"}:
            self.current_state.pid = None
        self.refresh_wallpaper_state()

    def populate_list(self) -> None:
        child = self.listbox.get_first_child()
        while child is not None:
            sibling = child.get_next_sibling()
            self.listbox.remove(child)
            child = sibling

        for index in self.apps_filtered_idx:
            app = self.apps_all[index]
            row = Gtk.ListBoxRow()

            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            box.set_margin_top(6)
            box.set_margin_bottom(6)
            box.set_margin_start(8)
            box.set_margin_end(8)

            icon = Gtk.Image.new_from_gicon(app.get_icon())
            icon.set_pixel_size(30)

            label = Gtk.Label(label=app_label(app), xalign=0)
            label.set_hexpand(True)

            box.append(icon)
            box.append(label)
            row.set_child(box)
            row._appinfo = app  # type: ignore[attr-defined]
            self.listbox.append(row)

        first = self.listbox.get_first_child()
        if isinstance(first, Gtk.ListBoxRow):
            self.listbox.select_row(first)

    def filter_apps(self, query: str) -> None:
        query = (query or "").strip().lower()
        if not query:
            self.apps_filtered_idx = list(range(len(self.apps_all)))
            return

        tokens = [token for token in query.split() if token]
        scored: List[Tuple[int, int]] = []
        for index, text in enumerate(self.apps_text):
            total = 0
            matched = True
            for token in tokens:
                score = score_match(token, text)
                if score == 0:
                    matched = False
                    break
                total += score
            if matched:
                scored.append((total, index))

        scored.sort(key=lambda item: item[0], reverse=True)
        self.apps_filtered_idx = [index for _, index in scored]

    def on_search_changed(self, _entry) -> None:
        self.filter_apps(self.search.get_text() if self.search is not None else "")
        self.populate_list()

    def selected_app(self) -> Optional[Gio.AppInfo]:
        row = self.listbox.get_selected_row()
        if row is None:
            return None
        return getattr(row, "_appinfo", None)

    def on_activate_enter(self, _entry) -> None:
        app = self.selected_app()
        if app is not None:
            self.launch(app)

    def on_row_activated(self, _listbox, row: Gtk.ListBoxRow) -> None:
        app = getattr(row, "_appinfo", None)
        if app is not None:
            self.launch(app)

    def launch(self, app: Gio.AppInfo) -> None:
        try:
            app.launch([], None)
        except Exception:
            app_id = app.get_id() if hasattr(app, "get_id") else None
            if app_id:
                run(["gtk-launch", app_id])
        if self.window is not None:
            self.window.hide()
