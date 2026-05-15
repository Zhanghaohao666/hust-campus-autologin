from campus_autologin.linux_service import build_service_text, service_path


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
