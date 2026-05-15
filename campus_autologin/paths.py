from __future__ import annotations

import os
from pathlib import Path


APP_DIR_NAME = "hust-campus-autologin"
WINDOWS_DIR_NAME = ".campus-autologin"
_NATIVE_PATH = type(Path.cwd())


def user_home() -> Path:
    value = os.environ.get("USERPROFILE") or os.environ.get("HOME")
    return _NATIVE_PATH(value) if value else Path.home()


def default_base_dir() -> Path:
    if os.name == "nt":
        return user_home() / WINDOWS_DIR_NAME
    config_home = os.environ.get("XDG_CONFIG_HOME")
    return (_NATIVE_PATH(config_home) if config_home else user_home() / ".config") / APP_DIR_NAME


def default_data_dir() -> Path:
    if os.name == "nt":
        return default_base_dir()
    data_home = os.environ.get("XDG_DATA_HOME")
    return (
        _NATIVE_PATH(data_home) if data_home else user_home() / ".local" / "share"
    ) / APP_DIR_NAME


def default_config_path() -> Path:
    return default_base_dir() / "config.toml"


def default_log_dir() -> Path:
    return default_data_dir() / "logs"


def default_secret_path() -> Path:
    return default_data_dir() / "secrets.toml"
