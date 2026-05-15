from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from campus_autologin.paths import default_base_dir, default_config_path, default_log_dir


DEFAULT_CREDENTIAL_TARGET = "hust-campus-autologin"
DEFAULT_PORTAL_BASE_URLS = [
    "http://172.18.18.60:8080/eportal",
    "http://172.18.18.61:8080/eportal",
]
DEFAULT_PROBE_URLS = [
    "http://www.msftconnecttest.com/connecttest.txt",
    "http://edge-http.microsoft.com/captiveportal/generate_204",
    "http://connect.rom.miui.com/generate_204",
    "http://wifi.vivo.com.cn/generate_204",
]
DEFAULT_CAMPUS_SSID_PATTERNS = ["HUST_WIRELESS", "HUST_WIRELESS_2.4G"]


@dataclass(frozen=True)
class AccountConfig:
    username: str = ""
    credential_target: str = DEFAULT_CREDENTIAL_TARGET


@dataclass(frozen=True)
class PortalConfig:
    base_urls: list[str] = field(default_factory=lambda: list(DEFAULT_PORTAL_BASE_URLS))
    probe_urls: list[str] = field(default_factory=lambda: list(DEFAULT_PROBE_URLS))
    campus_ssid_patterns: list[str] = field(
        default_factory=lambda: list(DEFAULT_CAMPUS_SSID_PATTERNS)
    )
    manual_login_url: str = ""
    last_query_string: str = ""
    last_query_string_updated_at: str = ""


@dataclass(frozen=True)
class WatchConfig:
    interval_seconds: int = 30
    max_backoff_seconds: int = 300
    probe_timeout_seconds: int = 5
    login_timeout_seconds: int = 10
    querystring_cache_ttl_seconds: int = 30


@dataclass(frozen=True)
class LoggingConfig:
    level: str = "INFO"


@dataclass(frozen=True)
class NotificationConfig:
    enabled: bool = True
    notify_login_success: bool = True
    notify_failure_threshold: int = 3


@dataclass(frozen=True)
class AppConfig:
    account: AccountConfig = field(default_factory=AccountConfig)
    portal: PortalConfig = field(default_factory=PortalConfig)
    watch: WatchConfig = field(default_factory=WatchConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    notification: NotificationConfig = field(default_factory=NotificationConfig)
    base_dir: Path = field(default_factory=default_base_dir)
    config_path: Path = field(default_factory=default_config_path)

    @classmethod
    def default(cls) -> "AppConfig":
        return cls()

    @property
    def log_dir(self) -> Path:
        if self.config_path == default_config_path():
            return default_log_dir()
        return self.base_dir / "logs"

    @property
    def lock_path(self) -> Path:
        return self.base_dir / "watch.lock"


def _section(data: dict[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name)
    return value if isinstance(value, dict) else {}


def load_config(path: str | Path | None = None) -> AppConfig:
    config_path = Path(path) if path is not None else default_config_path()
    base_dir = config_path.parent
    data: dict[str, Any] = {}
    if config_path.exists():
        data = tomllib.loads(config_path.read_text(encoding="utf-8"))

    account_data = _section(data, "account")
    portal_data = _section(data, "portal")
    watch_data = _section(data, "watch")
    logging_data = _section(data, "logging")
    notification_data = _section(data, "notification")

    defaults = AppConfig.default()
    return AppConfig(
        account=AccountConfig(
            username=str(account_data.get("username", defaults.account.username)),
            credential_target=str(
                account_data.get(
                    "credential_target", defaults.account.credential_target
                )
            ),
        ),
        portal=PortalConfig(
            base_urls=list(portal_data.get("base_urls", defaults.portal.base_urls)),
            probe_urls=list(portal_data.get("probe_urls", defaults.portal.probe_urls)),
            campus_ssid_patterns=list(
                portal_data.get(
                    "campus_ssid_patterns", defaults.portal.campus_ssid_patterns
                )
            ),
            manual_login_url=str(
                portal_data.get("manual_login_url", defaults.portal.manual_login_url)
            ),
            last_query_string=str(
                portal_data.get("last_query_string", defaults.portal.last_query_string)
            ),
            last_query_string_updated_at=str(
                portal_data.get(
                    "last_query_string_updated_at",
                    defaults.portal.last_query_string_updated_at,
                )
            ),
        ),
        watch=WatchConfig(
            interval_seconds=int(
                watch_data.get("interval_seconds", defaults.watch.interval_seconds)
            ),
            max_backoff_seconds=int(
                watch_data.get(
                    "max_backoff_seconds", defaults.watch.max_backoff_seconds
                )
            ),
            probe_timeout_seconds=int(
                watch_data.get(
                    "probe_timeout_seconds", defaults.watch.probe_timeout_seconds
                )
            ),
            login_timeout_seconds=int(
                watch_data.get(
                    "login_timeout_seconds", defaults.watch.login_timeout_seconds
                )
            ),
            querystring_cache_ttl_seconds=int(
                watch_data.get(
                    "querystring_cache_ttl_seconds",
                    defaults.watch.querystring_cache_ttl_seconds,
                )
            ),
        ),
        logging=LoggingConfig(
            level=str(logging_data.get("level", defaults.logging.level))
        ),
        notification=NotificationConfig(
            enabled=bool(notification_data.get("enabled", defaults.notification.enabled)),
            notify_login_success=bool(
                notification_data.get(
                    "notify_login_success", defaults.notification.notify_login_success
                )
            ),
            notify_failure_threshold=int(
                notification_data.get(
                    "notify_failure_threshold",
                    defaults.notification.notify_failure_threshold,
                )
            ),
        ),
        base_dir=base_dir,
        config_path=config_path,
    )


def render_default_config(
    username: str = "",
    interval_seconds: int = 30,
    manual_login_url: str = "",
) -> str:
    username_line = username.replace("\\", "\\\\").replace('"', '\\"')
    manual_login_url_line = manual_login_url.replace("\\", "\\\\").replace('"', '\\"')
    return f"""[account]
username = "{username_line}"
credential_target = "{DEFAULT_CREDENTIAL_TARGET}"

[portal]
base_urls = [
  "http://172.18.18.60:8080/eportal",
  "http://172.18.18.61:8080/eportal"
]
probe_urls = [
  "http://www.msftconnecttest.com/connecttest.txt",
  "http://edge-http.microsoft.com/captiveportal/generate_204",
  "http://connect.rom.miui.com/generate_204",
  "http://wifi.vivo.com.cn/generate_204"
]
campus_ssid_patterns = [
  "HUST_WIRELESS",
  "HUST_WIRELESS_2.4G"
]
manual_login_url = "{manual_login_url_line}"
last_query_string = ""
last_query_string_updated_at = ""

[watch]
interval_seconds = {interval_seconds}
max_backoff_seconds = 300
probe_timeout_seconds = 5
login_timeout_seconds = 10
querystring_cache_ttl_seconds = 30

[logging]
level = "INFO"

[notification]
enabled = true
notify_login_success = true
notify_failure_threshold = 3
"""


def write_default_config(
    path: str | Path | None = None,
    username: str = "",
    interval_seconds: int = 30,
    manual_login_url: str = "",
) -> Path:
    config_path = Path(path) if path is not None else default_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        render_default_config(
            username,
            interval_seconds=interval_seconds,
            manual_login_url=manual_login_url,
        ),
        encoding="utf-8",
    )
    return config_path
