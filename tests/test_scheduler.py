import subprocess
import sys

from campus_autologin.scheduler import build_install_command, build_uninstall_command


def test_build_install_command_uses_powershell_scheduledtasks_api():
    command = build_install_command("HUST Campus Autologin")

    assert command[:3] == ["powershell.exe", "-NoProfile", "-Command"]
    script = command[3]
    assert "New-ScheduledTaskAction" in script
    assert "Register-ScheduledTask" in script
    assert sys.executable in script
    assert "-m campus_autologin watch" in script
    assert "HUST Campus Autologin" in script


def test_build_uninstall_command_deletes_task():
    assert build_uninstall_command("HUST Campus Autologin") == [
        "powershell.exe",
        "-NoProfile",
        "-Command",
        "Unregister-ScheduledTask -TaskName 'HUST Campus Autologin' -Confirm:$false -ErrorAction SilentlyContinue",
    ]
