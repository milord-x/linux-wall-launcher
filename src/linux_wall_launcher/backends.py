from __future__ import annotations

import configparser
import os
import re
import shlex
import shutil
import signal
import subprocess
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence, Tuple

from .config import AppConfig

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")
VIDEO_EXTS = (".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v")
MEDIA_EXTS = IMAGE_EXTS + VIDEO_EXTS


@dataclass(slots=True)
class WallpaperState:
    backend: str
    path: str
    output: Optional[str] = None
    fit_mode: Optional[str] = None
    media_kind: str = "image"
    pid: Optional[int] = None
    launcher_args: List[str] = field(default_factory=list)


def run(cmd: Sequence[str]) -> Tuple[int, str]:
    try:
        process = subprocess.run(
            list(cmd),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        return process.returncode, (process.stdout or "").strip()
    except FileNotFoundError:
        return 127, ""


def run_detached(cmd: Sequence[str]) -> bool:
    try:
        subprocess.Popen(
            list(cmd),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True
    except FileNotFoundError:
        return False


def media_kind_for_path(path: str) -> str:
    return "video" if path.lower().endswith(VIDEO_EXTS) else "image"


def _last_existing_path(parts: Iterable[str]) -> Optional[str]:
    for part in reversed(list(parts)):
        expanded = os.path.expanduser(part.strip().strip("'").strip('"'))
        if expanded.startswith("/") and os.path.exists(expanded):
            return expanded
    return None


class BackendManager:
    def __init__(self, config: AppConfig):
        self.config = config

    def detect_state(self) -> Optional[WallpaperState]:
        forced = self.config.backend
        detectors = {
            "mpvpaper": self._detect_mpvpaper,
            "swww": self._detect_swww,
            "hyprpaper": self._detect_hyprpaper,
            "swaybg": self._detect_swaybg,
            "feh": self._detect_feh,
            "nitrogen": self._detect_nitrogen,
        }

        if forced in detectors:
            state = detectors[forced]()
            return state or WallpaperState(
                backend=forced,
                path="",
                output=self.config.output,
                media_kind="video" if forced == "mpvpaper" else "image",
                launcher_args=list(self.config.mpvpaper_args) if forced == "mpvpaper" else [],
            )

        for name in ("mpvpaper", "swww", "hyprpaper", "swaybg", "feh", "nitrogen"):
            state = detectors[name]()
            if state is not None:
                return state
        return None

    def list_media(self, current_path: Optional[str], state: Optional[WallpaperState]) -> List[str]:
        base_dir = self._media_dir(current_path)
        if base_dir is None:
            return []

        exts = MEDIA_EXTS if state and state.backend == "mpvpaper" else IMAGE_EXTS
        files: List[str] = []
        for entry in os.scandir(base_dir):
            if entry.is_file() and entry.name.lower().endswith(exts):
                files.append(entry.path)
        files.sort()
        return files

    def apply(self, state: WallpaperState, path: str) -> bool:
        backend = state.backend
        if backend == "swww":
            return run(["swww", "img", path])[0] == 0

        if backend == "hyprpaper":
            output = self.config.output or state.output
            if not output:
                return False
            request = f"{output},{path}"
            if state.fit_mode:
                request += f",{state.fit_mode}"
            return run(["hyprctl", "hyprpaper", "wallpaper", request])[0] == 0

        if backend == "mpvpaper":
            output = self.config.output or state.output
            if not output:
                return False
            if state.pid is not None:
                try:
                    os.kill(state.pid, signal.SIGTERM)
                except OSError:
                    pass
            args = state.launcher_args or list(self.config.mpvpaper_args)
            return run_detached(["mpvpaper", *args, output, path])

        if backend == "swaybg":
            mode = state.fit_mode or "fill"
            if state.pid is not None:
                try:
                    os.kill(state.pid, signal.SIGTERM)
                except OSError:
                    pass
            cmd = ["swaybg"]
            if self.config.output or state.output:
                cmd += ["-o", self.config.output or state.output or ""]
            cmd += ["-m", mode, "-i", path]
            return run_detached(cmd)

        if backend == "feh":
            mode = state.fit_mode or "fill"
            return run(["feh", f"--bg-{mode}", path])[0] == 0

        if backend == "nitrogen":
            mode = state.fit_mode or "zoom-fill"
            return run(["nitrogen", f"--set-{mode}", "--save", path])[0] == 0

        return False

    def _media_dir(self, current_path: Optional[str]) -> Optional[str]:
        if os.path.isdir(self.config.media_dir):
            return self.config.media_dir
        if current_path:
            candidate = os.path.dirname(current_path)
            if candidate and os.path.isdir(candidate):
                return candidate
        return None

    def _detect_swww(self) -> Optional[WallpaperState]:
        if not os.path.isdir(self.config.swww_cache_dir):
            return None

        try:
            cache_files = [
                os.path.join(self.config.swww_cache_dir, name)
                for name in os.listdir(self.config.swww_cache_dir)
                if os.path.isfile(os.path.join(self.config.swww_cache_dir, name))
            ]
            cache_files.sort(key=os.path.getmtime, reverse=True)
        except OSError:
            return None

        for cache_path in cache_files:
            try:
                with open(cache_path, "rb") as handle:
                    data = handle.read()
            except OSError:
                continue
            parts = [part.decode("utf-8", errors="ignore").strip() for part in data.split(b"\0") if part]
            path = _last_existing_path(parts)
            if path:
                return WallpaperState(
                    backend="swww",
                    path=path,
                    output=os.path.basename(cache_path),
                    media_kind=media_kind_for_path(path),
                )
        return None

    def _detect_mpvpaper(self) -> Optional[WallpaperState]:
        for pid in self._candidate_pids():
            parts = self._read_cmdline(pid)
            if len(parts) < 3 or os.path.basename(parts[0]) != "mpvpaper":
                continue
            path = os.path.expanduser(parts[-1])
            output = parts[-2]
            if not os.path.exists(path):
                continue
            return WallpaperState(
                backend="mpvpaper",
                path=path,
                output=output,
                media_kind=media_kind_for_path(path),
                pid=pid,
                launcher_args=parts[1:-2],
            )
        return None

    def _detect_hyprpaper(self) -> Optional[WallpaperState]:
        if not os.path.exists(self.config.hyprpaper_conf):
            return None
        try:
            with open(self.config.hyprpaper_conf, "r", encoding="utf-8", errors="ignore") as handle:
                data = handle.read()
        except OSError:
            return None

        matches = list(
            re.finditer(
                r"^\s*wallpaper\s*=\s*([^,]+?)\s*,\s*([^,]+?)(?:\s*,\s*([^\s,]+))?\s*$",
                data,
                flags=re.MULTILINE,
            )
        )
        if matches:
            match = matches[-1]
            output = match.group(1).strip()
            path = os.path.expanduser(match.group(2).strip())
            fit_mode = (match.group(3) or "").strip() or None
            if os.path.exists(path):
                return WallpaperState(
                    backend="hyprpaper",
                    path=path,
                    output=output,
                    fit_mode=fit_mode,
                    media_kind=media_kind_for_path(path),
                )

        preload = re.search(r"^\s*preload\s*=\s*(.+?)\s*$", data, flags=re.MULTILINE)
        if preload:
            path = os.path.expanduser(preload.group(1).strip())
            if os.path.exists(path):
                return WallpaperState(
                    backend="hyprpaper",
                    path=path,
                    output=self.config.output,
                    media_kind=media_kind_for_path(path),
                )
        return None

    def _detect_swaybg(self) -> Optional[WallpaperState]:
        for pid in self._candidate_pids():
            parts = self._read_cmdline(pid)
            if len(parts) < 2 or os.path.basename(parts[0]) != "swaybg":
                continue
            output = None
            fit_mode = "fill"
            path = None
            index = 1
            while index < len(parts):
                part = parts[index]
                if part == "-o" and index + 1 < len(parts):
                    output = parts[index + 1]
                    index += 2
                    continue
                if part == "-m" and index + 1 < len(parts):
                    fit_mode = parts[index + 1]
                    index += 2
                    continue
                if part == "-i" and index + 1 < len(parts):
                    path = os.path.expanduser(parts[index + 1])
                    index += 2
                    continue
                index += 1

            if path and os.path.exists(path):
                return WallpaperState(
                    backend="swaybg",
                    path=path,
                    output=output,
                    fit_mode=fit_mode,
                    media_kind=media_kind_for_path(path),
                    pid=pid,
                )
        return None

    def _detect_feh(self) -> Optional[WallpaperState]:
        if not os.path.exists(self.config.fehbg_path):
            return None
        try:
            with open(self.config.fehbg_path, "r", encoding="utf-8", errors="ignore") as handle:
                parts = shlex.split(handle.read())
        except (OSError, ValueError):
            return None

        path = _last_existing_path(parts)
        if not path:
            return None

        fit_mode = "fill"
        for part in parts:
            if part.startswith("--bg-"):
                fit_mode = part.removeprefix("--bg-") or "fill"

        return WallpaperState(
            backend="feh",
            path=path,
            fit_mode=fit_mode,
            media_kind=media_kind_for_path(path),
        )

    def _detect_nitrogen(self) -> Optional[WallpaperState]:
        if not os.path.exists(self.config.nitrogen_conf):
            return None

        parser = configparser.ConfigParser()
        try:
            parser.read(self.config.nitrogen_conf, encoding="utf-8")
        except (OSError, configparser.Error):
            return None

        if not parser.has_section("xin_-1"):
            return None

        path = os.path.expanduser(parser.get("xin_-1", "file", fallback="").strip())
        if not path or not os.path.exists(path):
            return None

        return WallpaperState(
            backend="nitrogen",
            path=path,
            fit_mode=parser.get("xin_-1", "mode", fallback="zoom-fill").strip() or "zoom-fill",
            media_kind=media_kind_for_path(path),
        )

    @staticmethod
    def _candidate_pids() -> List[int]:
        try:
            pids = [int(name) for name in os.listdir("/proc") if name.isdigit()]
        except OSError:
            return []
        pids.sort(reverse=True)
        return pids

    @staticmethod
    def _read_cmdline(pid: int) -> List[str]:
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as handle:
                raw = handle.read()
        except OSError:
            return []
        return [part.decode("utf-8", errors="ignore") for part in raw.split(b"\0") if part]


def available_backends() -> List[str]:
    binaries = {
        "swww": shutil.which("swww"),
        "mpvpaper": shutil.which("mpvpaper"),
        "hyprpaper": shutil.which("hyprctl"),
        "swaybg": shutil.which("swaybg"),
        "feh": shutil.which("feh"),
        "nitrogen": shutil.which("nitrogen"),
    }
    return [name for name, path in binaries.items() if path]

