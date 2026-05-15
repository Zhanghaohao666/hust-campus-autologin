from pathlib import Path

from campus_autologin.config import (
    AccountConfig,
    AppConfig,
    NotificationConfig,
    PortalConfig,
    WatchConfig,
    default_config_path,
    load_config,
    write_config,
    write_default_config,
)


def test_default_config_uses_user_home_and_notifications_enabled(tmp_path, monkeypatch):
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    config = AppConfig.default()

    assert config.base_dir == tmp_path / ".campus-autologin"
    assert config.config_path == tmp_path / ".campus-autologin" / "config.toml"
    assert config.account.username == ""
    assert config.account.credential_target == "hust-campus-autologin"
    assert "http://connect.rom.miui.com/generate_204" in config.portal.probe_urls
    assert "http://wifi.vivo.com.cn/generate_204" in config.portal.probe_urls
    assert config.notification.enabled is True
    assert config.notification.notify_login_success is True


def test_load_config_merges_toml_with_defaults(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
[account]
username = "<student-id>"

[portal]
base_urls = ["http://172.18.18.60:8080/eportal", "http://172.18.18.61:8080/eportal"]

[watch]
interval_seconds = 12
login_timeout_seconds = 9

[notification]
enabled = false
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.account.username == "<student-id>"
    assert config.portal.base_urls == [
        "http://172.18.18.60:8080/eportal",
        "http://172.18.18.61:8080/eportal",
    ]
    assert config.watch.interval_seconds == 12
    assert config.watch.probe_timeout_seconds == 5
    assert config.watch.login_timeout_seconds == 9
    assert config.notification.enabled is False
    assert config.notification.notify_login_success is True


def test_load_config_supports_manual_portal_url_and_cached_query(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
[portal]
manual_login_url = "http://172.18.18.61:8080/eportal/index.jsp?wlanuserip=abc&mac=def"
last_query_string = "wlanuserip=old&mac=old"
last_query_string_updated_at = "2026-05-15T11:46:03+08:00"
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.portal.manual_login_url.endswith("mac=def")
    assert config.portal.last_query_string == "wlanuserip=old&mac=old"
    assert config.portal.last_query_string_updated_at == "2026-05-15T11:46:03+08:00"


def test_write_default_config_creates_directory_and_never_writes_password(tmp_path):
    target = tmp_path / ".campus-autologin" / "config.toml"

    write_default_config(target, username="<student-id>")

    content = target.read_text(encoding="utf-8")
    assert target.exists()
    assert 'username = "<student-id>"' in content
    assert "password" not in content.lower()
    assert 'enabled = true' in content
    assert 'notify_login_success = true' in content


def test_write_default_config_accepts_interval_and_manual_login_url(tmp_path):
    target = tmp_path / "config.toml"
    manual_url = "http://172.18.18.61:8080/eportal/index.jsp?wlanuserip=abc"

    write_default_config(
        target,
        username="<student-id>",
        interval_seconds=15,
        manual_login_url=manual_url,
    )

    config = load_config(target)

    assert config.account.username == "<student-id>"
    assert config.watch.interval_seconds == 15
    assert config.portal.manual_login_url == manual_url


def test_default_config_path_uses_userprofile(tmp_path, monkeypatch):
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    assert default_config_path() == Path(tmp_path) / ".campus-autologin" / "config.toml"


def test_write_config_roundtrips_ui_editable_values(tmp_path):
    target = tmp_path / "config.toml"
    config = AppConfig(
        account=AccountConfig(username="<student-id>", credential_target="campus-test"),
        portal=PortalConfig(
            base_urls=["http://172.18.18.60:8080/eportal"],
            probe_urls=["http://connect.rom.miui.com/generate_204"],
            campus_ssid_patterns=["HUST_WIRELESS"],
            manual_login_url="http://172.18.18.61:8080/eportal/index.jsp?wlanuserip=abc",
            last_query_string="wlanuserip=abc",
            last_query_string_updated_at="2026-05-15T14:10:00+08:00",
        ),
        watch=WatchConfig(
            interval_seconds=45,
            max_backoff_seconds=180,
            probe_timeout_seconds=4,
            login_timeout_seconds=11,
            querystring_cache_ttl_seconds=20,
        ),
        notification=NotificationConfig(
            enabled=False,
            notify_login_success=False,
            notify_failure_threshold=5,
        ),
        base_dir=tmp_path,
        config_path=target,
    )

    write_config(config)
    loaded = load_config(target)
    content = target.read_text(encoding="utf-8")

    assert loaded.account.username == "<student-id>"
    assert loaded.account.credential_target == "campus-test"
    assert loaded.portal.base_urls == ["http://172.18.18.60:8080/eportal"]
    assert loaded.portal.probe_urls == ["http://connect.rom.miui.com/generate_204"]
    assert loaded.portal.campus_ssid_patterns == ["HUST_WIRELESS"]
    assert loaded.portal.manual_login_url.endswith("wlanuserip=abc")
    assert loaded.portal.last_query_string == "wlanuserip=abc"
    assert loaded.watch.interval_seconds == 45
    assert loaded.watch.max_backoff_seconds == 180
    assert loaded.watch.probe_timeout_seconds == 4
    assert loaded.watch.login_timeout_seconds == 11
    assert loaded.watch.querystring_cache_ttl_seconds == 20
    assert loaded.notification.enabled is False
    assert loaded.notification.notify_login_success is False
    assert loaded.notification.notify_failure_threshold == 5
    assert "password" not in content.lower()
