from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from typing import Any, Optional

from .config import AppConfig


def run(cmd: list[str]) -> tuple[int, str]:
    try:
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return 127, ""
    return process.returncode, (process.stdout or "").strip()


def load_json(cmd: list[str]) -> Any:
    code, output = run(cmd)
    if code != 0 or not output:
        return []
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return []


def hyprctl_available() -> bool:
    return shutil.which("hyprctl") is not None


def class_pattern(app_id: str) -> re.Pattern[str]:
    return re.compile(rf"^{re.escape(app_id)}$")


def find_client(app_id: str, include_hidden: bool = False) -> Optional[dict[str, Any]]:
    pattern = class_pattern(app_id)
    for client in load_json(["hyprctl", "-j", "clients"]):
        cls = str(client.get("class") or client.get("initialClass") or "")
        mapped = client.get("mapped", True)
        hidden = client.get("hidden", False)
        if pattern.match(cls) and mapped and (include_hidden or not hidden):
            return client
    return None


def launch_command() -> list[str]:
    binary = shutil.which("lumaq")
    if binary:
        return [binary]
    return [sys.executable, "-m", "lumaq.main"]


def launch_app(config: AppConfig) -> None:
    env = os.environ.copy()
    env["LUMAQ_CONFIG"] = config.config_path
    subprocess.Popen(
        launch_command(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
        env=env,
    )


def close_client(app_id: str) -> None:
    escaped = app_id.replace(".", r"\.")
    run(["hyprctl", "dispatch", "closewindow", f"class:^({escaped})$"])


def select_monitor(config: AppConfig) -> Optional[dict[str, Any]]:
    monitors = load_json(["hyprctl", "-j", "monitors"])
    if not isinstance(monitors, list):
        return None

    if config.output:
        for monitor in monitors:
            if str(monitor.get("name") or "") == config.output:
                return monitor

    for monitor in monitors:
        if monitor.get("focused"):
            return monitor
    return monitors[0] if monitors else None


def anchored_position(config: AppConfig, monitor: dict[str, Any]) -> tuple[int, int]:
    width = config.window.width
    height = config.window.height
    mon_x = int(monitor.get("x") or 0)
    mon_y = int(monitor.get("y") or 0)
    mon_w = int(monitor.get("width") or width)
    mon_h = int(monitor.get("height") or height)
    anchor = config.window.anchor

    horizontal = {
        "top-left": mon_x,
        "left": mon_x,
        "bottom-left": mon_x,
        "top-right": mon_x + mon_w - width,
        "right": mon_x + mon_w - width,
        "bottom-right": mon_x + mon_w - width,
    }
    vertical = {
        "top-left": mon_y,
        "top": mon_y,
        "top-right": mon_y,
        "bottom-left": mon_y + mon_h - height,
        "bottom": mon_y + mon_h - height,
        "bottom-right": mon_y + mon_h - height,
    }

    x = horizontal.get(anchor, mon_x + (mon_w - width) // 2)
    y = vertical.get(anchor, mon_y + (mon_h - height) // 2)
    return x + config.window.margin_x, y + config.window.margin_y


def place_client(address: str, config: AppConfig) -> None:
    monitor = select_monitor(config)
    if monitor is None:
        return

    width = config.window.width
    height = config.window.height
    x, y = anchored_position(config, monitor)

    run(["hyprctl", "dispatch", "resizewindowpixel", "exact", str(width), f"{height},address:{address}"])
    run(["hyprctl", "dispatch", "movewindowpixel", "exact", str(x), f"{y},address:{address}"])


def wait_for_client(app_id: str, timeout: float = 2.0) -> Optional[dict[str, Any]]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        client = find_client(app_id)
        if client is not None:
            return client
        time.sleep(0.05)
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Toggle the Lumaq window on Hyprland")
    parser.add_argument("--config", help="Path to config TOML file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = AppConfig.load(args.config)

    if not hyprctl_available():
        launch_app(config)
        return 0

    visible = find_client(config.app_id)
    if visible is not None:
        close_client(config.app_id)
        return 0

    hidden = find_client(config.app_id, include_hidden=True)
    if hidden is not None:
        launch_app(config)
        return 0

    launch_app(config)
    if not config.window.manage_geometry:
        return 0

    client = wait_for_client(config.app_id)
    if client is None:
        return 0

    address = str(client.get("address") or "")
    if address:
        place_client(address, config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
