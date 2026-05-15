import subprocess
import sys
from pathlib import Path

from campus_autologin.scheduler import (
    build_install_command,
    build_start_command,
    build_status_command,
    build_stop_command,
    build_uninstall_command,
    build_watch_action,
)


def test_build_install_command_uses_powershell_scheduledtasks_api():
    command = build_install_command("HUST Campus Autologin")

    assert command[:3] == ["powershell.exe", "-NoProfile", "-Command"]
    script = command[3]
    assert "New-ScheduledTaskAction" in script
    assert "Register-ScheduledTask" in script
    assert sys.executable in script
    assert "-m campus_autologin watch" in script
    assert "HUST Campus Autologin" in script


def test_build_watch_action_uses_module_invocation_for_source_python(tmp_path):
    action = build_watch_action(
        executable_path="C:/Python/python.exe",
        project_dir=tmp_path,
        frozen=False,
    )

    assert action.execute == str(Path("C:/Python/python.exe"))
    assert action.argument == "-m campus_autologin watch"
    assert action.working_directory == str(tmp_path)


def test_build_watch_action_uses_direct_exe_for_frozen_app():
    exe_path = Path("C:/Program Files/HUST Campus Autologin/HUSTCampusAutologin.exe")

    action = build_watch_action(
        executable_path=exe_path,
        project_dir=Path("C:/ignored/source"),
        frozen=True,
    )

    assert action.execute == str(exe_path)
    assert action.argument == "watch"
    assert action.working_directory == str(exe_path.parent)


def test_build_uninstall_command_deletes_task():
    assert build_uninstall_command("HUST Campus Autologin") == [
        "powershell.exe",
        "-NoProfile",
        "-Command",
        "Unregister-ScheduledTask -TaskName 'HUST Campus Autologin' -Confirm:$false -ErrorAction SilentlyContinue",
    ]


def test_build_start_stop_and_status_commands_target_task_name():
    assert build_start_command("HUST Campus Autologin") == [
        "powershell.exe",
        "-NoProfile",
        "-Command",
        "Start-ScheduledTask -TaskName 'HUST Campus Autologin'",
    ]
    assert build_stop_command("HUST Campus Autologin") == [
        "powershell.exe",
        "-NoProfile",
        "-Command",
        "Stop-ScheduledTask -TaskName 'HUST Campus Autologin' -ErrorAction SilentlyContinue",
    ]
    assert build_status_command("HUST Campus Autologin") == [
        "powershell.exe",
        "-NoProfile",
        "-Command",
        "Get-ScheduledTask -TaskName 'HUST Campus Autologin' | Select-Object TaskName,State | Format-List",
    ]
