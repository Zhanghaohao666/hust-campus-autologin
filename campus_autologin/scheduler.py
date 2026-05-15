from __future__ import annotations

import subprocess
import sys
import getpass
from dataclasses import dataclass
from pathlib import Path


DEFAULT_TASK_NAME = "HUST Campus Autologin"


@dataclass(frozen=True)
class TaskAction:
    execute: str
    argument: str
    working_directory: str


def build_watch_action(
    *,
    executable_path: str | Path | None = None,
    project_dir: str | Path | None = None,
    frozen: bool | None = None,
) -> TaskAction:
    is_frozen = bool(getattr(sys, "frozen", False)) if frozen is None else frozen
    executable = Path(executable_path) if executable_path is not None else Path(sys.executable)
    if is_frozen:
        return TaskAction(
            execute=str(executable),
            argument="watch",
            working_directory=str(executable.parent),
        )

    source_dir = Path(project_dir) if project_dir is not None else Path(__file__).resolve().parents[1]
    return TaskAction(
        execute=str(executable),
        argument="-m campus_autologin watch",
        working_directory=str(source_dir),
    )


def build_install_command(task_name: str = DEFAULT_TASK_NAME) -> list[str]:
    action = build_watch_action()
    user = _escape_ps_single_quoted(getpass.getuser())
    task = _escape_ps_single_quoted(task_name)
    execute = _escape_ps_single_quoted(action.execute)
    argument = _escape_ps_single_quoted(action.argument)
    cwd = _escape_ps_single_quoted(action.working_directory)
    script = (
        f"$action = New-ScheduledTaskAction -Execute '{execute}' "
        f"-Argument '{argument}' -WorkingDirectory '{cwd}'; "
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
