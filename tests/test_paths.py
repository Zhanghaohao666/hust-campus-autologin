from campus_autologin.paths import (
    default_base_dir,
    default_config_path,
    default_log_dir,
)


def test_windows_paths_use_userprofile(monkeypatch, tmp_path):
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setattr("campus_autologin.paths.os.name", "nt")

    assert default_base_dir() == tmp_path / ".campus-autologin"
    assert default_config_path() == tmp_path / ".campus-autologin" / "config.toml"
    assert default_log_dir() == tmp_path / ".campus-autologin" / "logs"


def test_linux_paths_use_xdg(monkeypatch, tmp_path):
    monkeypatch.delenv("USERPROFILE", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("campus_autologin.paths.os.name", "posix")

    assert default_base_dir() == tmp_path / ".config" / "hust-campus-autologin"
    assert (
        default_config_path()
        == tmp_path / ".config" / "hust-campus-autologin" / "config.toml"
    )
    assert (
        default_log_dir()
        == tmp_path / ".local" / "share" / "hust-campus-autologin" / "logs"
    )
