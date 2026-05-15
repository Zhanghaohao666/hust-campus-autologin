from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable

from campus_autologin.config import AppConfig, load_config, write_config
from campus_autologin.credentials import store_password_auto
from campus_autologin.logs import tail_lines
from campus_autologin.process import run_hidden
from campus_autologin.scheduler import (
    install_task,
    start_task,
    stop_task,
    task_status,
    uninstall_task,
)


@dataclass(frozen=True)
class GuiSettings:
    username: str
    password: str
    interval_seconds: int
    manual_login_url: str
    notifications_enabled: bool
    notify_login_success: bool


@dataclass(frozen=True)
class UiOperationResult:
    ok: bool
    message: str


StorePassword = Callable[[str, str, str], None]
ProcessRunner = Callable[[], subprocess.CompletedProcess]


def settings_from_config(config: AppConfig) -> GuiSettings:
    return GuiSettings(
        username=config.account.username,
        password="",
        interval_seconds=config.watch.interval_seconds,
        manual_login_url=config.portal.manual_login_url,
        notifications_enabled=config.notification.enabled,
        notify_login_success=config.notification.notify_login_success,
    )


def save_gui_settings(
    settings: GuiSettings,
    *,
    config_path: str | Path | None = None,
    store_password: StorePassword = store_password_auto,
) -> UiOperationResult:
    username = settings.username.strip()
    if not username:
        return UiOperationResult(False, "请填写校园网账号")
    if settings.interval_seconds < 5:
        return UiOperationResult(False, "探测间隔至少为 5 秒")

    config = load_config(config_path)
    updated = AppConfig(
        account=replace(config.account, username=username),
        portal=replace(config.portal, manual_login_url=settings.manual_login_url.strip()),
        watch=replace(config.watch, interval_seconds=settings.interval_seconds),
        logging=config.logging,
        notification=replace(
            config.notification,
            enabled=settings.notifications_enabled,
            notify_login_success=settings.notify_login_success,
        ),
        base_dir=config.base_dir,
        config_path=config.config_path,
    )
    write_config(updated)

    password = settings.password
    if password:
        store_password(updated.account.credential_target, username, password)

    return UiOperationResult(True, f"配置已保存: {updated.config_path}")


def tail_watch_log(config: AppConfig, lines: int = 80) -> list[str]:
    return tail_lines(config.log_dir / "watch.log", lines)


def completed_process_to_result(
    action_label: str, result: subprocess.CompletedProcess
) -> UiOperationResult:
    output = (result.stdout or result.stderr or "").strip()
    if not output:
        output = f"退出码 {result.returncode}"
    if result.returncode == 0:
        return UiOperationResult(True, f"{action_label}成功: {output}")
    if _is_missing_scheduled_task_error(output):
        return UiOperationResult(
            False,
            f"{action_label}失败: 还没有安装自动重连任务，请先点击“安装开机自启”。",
        )
    return UiOperationResult(False, f"{action_label}失败: {output}")


def run_service_action(action_label: str, runner: ProcessRunner) -> UiOperationResult:
    return completed_process_to_result(action_label, runner())


def install_autostart() -> UiOperationResult:
    return run_service_action("安装开机自启", install_task)


def uninstall_autostart() -> UiOperationResult:
    return run_service_action("取消开机自启", uninstall_task)


def start_autologin() -> UiOperationResult:
    return run_service_action("启动自动重连", start_task)


def stop_autologin() -> UiOperationResult:
    return run_service_action("停止自动重连", stop_task)


def get_service_status() -> UiOperationResult:
    return run_service_action("查询自动重连状态", task_status)


def _is_missing_scheduled_task_error(output: str) -> bool:
    return (
        "ScheduledTask" in output
        and ("0x80070002" in output or "找不到指定的文件" in output)
    )


def read_windows_proxy() -> str:
    if os.name != "nt":
        return ""
    try:
        result = run_hidden(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                "Get-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings' | Select-Object ProxyEnable,ProxyServer | Format-List",
            ],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        return result.stdout.strip()
    except Exception:
        return ""


@dataclass(frozen=True)
class ConnectionStatus:
    status: str  # "online", "captive_portal", "offline", "not_campus", "unknown"
    message: str = ""


def probe_connection_status(config: AppConfig) -> ConnectionStatus:
    try:
        from campus_autologin.credentials import CredentialError, read_password_auto
        from campus_autologin.http_client import create_direct_session
        from campus_autologin.network_probe import ProbeStatus, probe_connectivity

        session = create_direct_session()
        try:
            hints: list[str] = []
            try:
                result = run_hidden(
                    ["powershell.exe", "-NoProfile", "-Command",
                     "Get-NetConnectionProfile | Select-Object -ExpandProperty Name"],
                    capture_output=True, text=True, timeout=3, check=False,
                )
                hints.extend(line.strip() for line in result.stdout.splitlines() if line.strip())
            except Exception:
                pass

            probe = probe_connectivity(
                session=session,
                probe_urls=config.portal.probe_urls,
                portal_base_urls=config.portal.base_urls,
                timeout=config.watch.probe_timeout_seconds,
                campus_hints=hints,
                manual_login_url=config.portal.manual_login_url,
            )
            status_map = {
                ProbeStatus.ONLINE: "online",
                ProbeStatus.CAPTIVE_PORTAL: "captive_portal",
                ProbeStatus.PORTAL_REACHABLE: "captive_portal",
                ProbeStatus.NOT_CAMPUS_NETWORK: "not_campus",
                ProbeStatus.OFFLINE: "offline",
            }
            return ConnectionStatus(
                status=status_map.get(probe.status, "unknown"),
                message=probe.message,
            )
        finally:
            session.close()
    except Exception as exc:
        return ConnectionStatus(status="unknown", message=str(exc))
