import subprocess
import sys
from pathlib import Path

from campus_autologin.scheduler import (
    build_install_command,
    build_start_command,
    build_status_command,
    build_stop_command,
    build_stop_watch_processes_command,
    build_uninstall_command,
    build_watch_action,
    install_task,
    restart_task,
    start_task,
    stop_task,
    uninstall_task,
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


def test_build_stop_watch_processes_command_targets_existing_watchers():
    command = build_stop_watch_processes_command()

    assert command[:3] == ["powershell.exe", "-NoProfile", "-Command"]
    script = command[3]
    assert "Get-CimInstance Win32_Process" in script
    assert "HUSTCampusAutologin" in script
    assert "campus_autologin watch" in script
    assert "Stop-Process" in script


def test_install_task_uses_hidden_subprocess_runner(monkeypatch):
    calls = []

    def fake_run_hidden(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    monkeypatch.setattr("campus_autologin.scheduler.run_hidden", fake_run_hidden)

    result = install_task("HUST Campus Autologin")

    assert result.returncode == 0
    scripts = [call[0][3] for call in calls]
    assert scripts[0].startswith("Stop-ScheduledTask")
    assert "Stop-Process" in scripts[1]
    assert "Register-ScheduledTask" in scripts[2]
    assert calls[2][1] == {"capture_output": True, "text": True}


def test_uninstall_task_stops_old_watchers_before_unregister(monkeypatch):
    calls = []

    def fake_run_hidden(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    monkeypatch.setattr("campus_autologin.scheduler.run_hidden", fake_run_hidden)

    result = uninstall_task("HUST Campus Autologin")

    assert result.returncode == 0
    scripts = [call[0][3] for call in calls]
    assert scripts[0].startswith("Stop-ScheduledTask")
    assert "Stop-Process" in scripts[1]
    assert scripts[2].startswith("Unregister-ScheduledTask")


def test_start_task_stops_old_watchers_before_starting(monkeypatch):
    calls = []

    def fake_run_hidden(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    monkeypatch.setattr("campus_autologin.scheduler.run_hidden", fake_run_hidden)

    result = start_task("HUST Campus Autologin")

    assert result.returncode == 0
    scripts = [call[0][3] for call in calls]
    assert scripts[0].startswith("Stop-ScheduledTask")
    assert "Stop-Process" in scripts[1]
    assert scripts[2].startswith("Start-ScheduledTask")


def test_stop_task_stops_scheduled_task_and_old_watchers(monkeypatch):
    calls = []

    def fake_run_hidden(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    monkeypatch.setattr("campus_autologin.scheduler.run_hidden", fake_run_hidden)

    result = stop_task("HUST Campus Autologin")

    assert result.returncode == 0
    scripts = [call[0][3] for call in calls]
    assert scripts[0].startswith("Stop-ScheduledTask")
    assert "Stop-Process" in scripts[1]


def test_restart_task_stops_old_watchers_then_starts(monkeypatch):
    calls = []

    def fake_run_hidden(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    monkeypatch.setattr("campus_autologin.scheduler.run_hidden", fake_run_hidden)

    result = restart_task("HUST Campus Autologin")

    assert result.returncode == 0
    scripts = [call[0][3] for call in calls]
    assert scripts[0].startswith("Stop-ScheduledTask")
    assert "Stop-Process" in scripts[1]
    assert scripts[2].startswith("Start-ScheduledTask")
