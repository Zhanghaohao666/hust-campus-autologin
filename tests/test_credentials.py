import subprocess

from campus_autologin.credentials import (
    CredentialError,
    build_cmdkey_command,
    parse_powershell_secret,
    read_password,
    read_password_auto,
    read_local_secret,
    store_local_secret,
    store_password_auto,
)


def test_build_cmdkey_command_contains_target_user_and_password():
    command = build_cmdkey_command("target", "user", "secret")

    assert command == [
        "cmdkey.exe",
        "/generic:target",
        "/user:user",
        "/pass:secret",
    ]


def test_parse_powershell_secret_returns_none_for_empty_output():
    assert parse_powershell_secret("") is None
    assert parse_powershell_secret("  \r\n") is None
    assert parse_powershell_secret("secret\r\n") == "secret"


def test_read_password_raises_when_credential_missing(monkeypatch):
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    try:
        read_password("missing")
    except CredentialError as exc:
        assert "missing" in str(exc)
    else:
        raise AssertionError("expected CredentialError")


def test_local_secret_roundtrip_sets_private_permissions(tmp_path):
    secret_path = tmp_path / "secrets.toml"

    store_local_secret(secret_path, "hust-campus-autologin", "<student-id>", "secret")

    assert read_local_secret(secret_path, "hust-campus-autologin") == "secret"
    assert secret_path.exists()


def test_read_local_secret_raises_for_missing_target(tmp_path):
    secret_path = tmp_path / "secrets.toml"
    secret_path.write_text("", encoding="utf-8")

    try:
        read_local_secret(secret_path, "missing")
    except CredentialError as exc:
        assert "missing" in str(exc)
    else:
        raise AssertionError("expected CredentialError")


def test_auto_password_uses_local_secret_on_non_windows(monkeypatch, tmp_path):
    secret_path = tmp_path / "secrets.toml"
    monkeypatch.setattr("campus_autologin.credentials.os.name", "posix")

    store_password_auto("target", "user", "secret", secret_path=secret_path)

    assert read_password_auto("target", secret_path=secret_path) == "secret"
