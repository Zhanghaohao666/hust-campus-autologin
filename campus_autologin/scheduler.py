from __future__ import annotations

import subprocess
import sys
import getpass
from pathlib import Path


DEFAULT_TASK_NAME = "HUST Campus Autologin"


def build_install_command(task_name: str = DEFAULT_TASK_NAME) -> list[str]:
    project_dir = Path(__file__).resolve().parents[1]
    user = _escape_ps_single_quoted(getpass.getuser())
    task = _escape_ps_single_quoted(task_name)
    python = _escape_ps_single_quoted(sys.executable)
    cwd = _escape_ps_single_quoted(str(project_dir))
    script = (
        f"$action = New-ScheduledTaskAction -Execute '{python}' "
        f"-Argument '-m campus_autologin watch' -WorkingDirectory '{cwd}'; "
        f"$trigger = New-ScheduledTaskTrigger -AtLogOn -User '{user}'; "
        "$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries "
        "-DontStopIfGoingOnBatteries; "
        f"Register-ScheduledTask -TaskName '{task}' -Action $action "
        "-Trigger $trigger -Settings $settings "
        "-Description 'Auto login HUST campus network without changing system proxy.' "
        "-Force | Out-Null"
    )
    return [
        "powershell.exe",
        "-NoProfile",
        "-Command",
        script,
    ]


def build_uninstall_command(task_name: str = DEFAULT_TASK_NAME) -> list[str]:
    task = _escape_ps_single_quoted(task_name)
    return [
        "powershell.exe",
        "-NoProfile",
        "-Command",
        f"Unregister-ScheduledTask -TaskName '{task}' -Confirm:$false -ErrorAction SilentlyContinue",
    ]


def install_task(task_name: str = DEFAULT_TASK_NAME) -> subprocess.CompletedProcess:
    return subprocess.run(build_install_command(task_name), capture_output=True, text=True)


def uninstall_task(task_name: str = DEFAULT_TASK_NAME) -> subprocess.CompletedProcess:
    return subprocess.run(
        build_uninstall_command(task_name), capture_output=True, text=True
    )


def _escape_ps_single_quoted(value: str) -> str:
    return value.replace("'", "''")
