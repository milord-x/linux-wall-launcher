from __future__ import annotations

import hashlib
import os
from typing import Optional

from .backends import VIDEO_EXTS, WallpaperState, run
from .config import AppConfig


def _thumb_dir(config: AppConfig) -> str:
    path = os.path.join(config.cache_dir, "thumbs")
    os.makedirs(path, exist_ok=True)
    return path


def _video_thumb_path(config: AppConfig, path: str) -> str:
    stat = os.stat(path)
    key = f"{path}:{stat.st_mtime_ns}:{stat.st_size}".encode()
    digest = hashlib.sha256(key).hexdigest()[:24]
    return os.path.join(_thumb_dir(config), f"{digest}.jpg")


def _generate_video_thumb(path: str, out_path: str) -> bool:
    rc, _ = run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            "00:00:01",
            "-i",
            path,
            "-frames:v",
            "1",
            "-vf",
            "thumbnail,scale=960:-1",
            out_path,
        ]
    )
    return rc == 0 and os.path.exists(out_path)


def resolve_preview_path(config: AppConfig, state: Optional[WallpaperState], generate: bool = True) -> Optional[str]:
    if state is None or not state.path or not os.path.exists(state.path):
        return None

    if state.media_kind != "video" and not state.path.lower().endswith(VIDEO_EXTS):
        return state.path

    out_path = _video_thumb_path(config, state.path)
    if os.path.exists(out_path):
        return out_path

    if generate and _generate_video_thumb(state.path, out_path):
        return out_path
    return None
