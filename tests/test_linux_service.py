import subprocess

from campus_autologin.linux_service import (
    build_service_text,
    restart_service,
    service_path,
    start_service,
    stop_service,
)


def test_build_service_text_uses_python_module_and_working_directory(tmp_path):
    text = build_service_text(
        python_executable="/usr/bin/python3",
        project_dir=tmp_path,
    )

    assert "Description=HUST Campus Autologin" in text
    assert f"WorkingDirectory={tmp_path}" in text
    assert "ExecStart=/usr/bin/python3 -m campus_autologin watch" in text
    assert "Restart=always" in text


def test_service_path_uses_config_home(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))

    assert (
        service_path()
        == tmp_path / ".config" / "systemd" / "user" / "hust-campus-autologin.service"
    )


def test_service_control_commands_delegate_to_systemctl(monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    monkeypatch.setattr("campus_autologin.linux_service.subprocess.run", fake_run)

    start_service()
    stop_service()
    restart_service()

    assert calls[0][0] == ["systemctl", "--user", "start", "hust-campus-autologin.service"]
    assert calls[2][0] == ["systemctl", "--user", "stop", "hust-campus-autologin.service"]
    assert calls[4][0] == ["systemctl", "--user", "restart", "hust-campus-autologin.service"]
    assert all(
        call[0] == ["systemctl", "--user", "status", "hust-campus-autologin.service", "--no-pager"]
        for call in (calls[1], calls[3], calls[5])
    )
