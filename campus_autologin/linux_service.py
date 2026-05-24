from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


SERVICE_NAME = "hust-campus-autologin.service"
_NATIVE_PATH = type(Path.cwd())


def service_path() -> Path:
    config_home = os.environ.get("XDG_CONFIG_HOME")
    base = _NATIVE_PATH(config_home) if config_home else Path.home() / ".config"
    return base / "systemd" / "user" / SERVICE_NAME


def build_service_text(
    *,
    python_executable: str | None = None,
    project_dir: str | Path | None = None,
) -> str:
    python = python_executable or sys.executable
    cwd = _coerce_path(project_dir) if project_dir is not None else Path.cwd()
    return f"""[Unit]
Description=HUST Campus Autologin
After=network-online.target

[Service]
Type=simple
WorkingDirectory={cwd}
ExecStart={python} -m campus_autologin watch
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
"""


def install_service() -> subprocess.CompletedProcess:
    target = service_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(build_service_text(), encoding="utf-8")
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
    subprocess.run(["systemctl", "--user", "enable", "--now", SERVICE_NAME], check=False)
    return service_status()


def uninstall_service() -> subprocess.CompletedProcess:
    subprocess.run(["systemctl", "--user", "disable", "--now", SERVICE_NAME], check=False)
    target = service_path()
    if target.exists():
        target.unlink()
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
    return service_status()


def start_service() -> subprocess.CompletedProcess:
    subprocess.run(["systemctl", "--user", "start", SERVICE_NAME], check=False)
    return service_status()


def stop_service() -> subprocess.CompletedProcess:
    subprocess.run(["systemctl", "--user", "stop", SERVICE_NAME], check=False)
    return service_status()


def restart_service() -> subprocess.CompletedProcess:
    subprocess.run(["systemctl", "--user", "restart", SERVICE_NAME], check=False)
    return service_status()


def service_status() -> subprocess.CompletedProcess:
    return subprocess.run(
        ["systemctl", "--user", "status", SERVICE_NAME, "--no-pager"],
        capture_output=True,
        text=True,
        check=False,
    )


def _coerce_path(path: str | Path) -> Path:
    if isinstance(path, Path):
        return path
    return _NATIVE_PATH(path)
