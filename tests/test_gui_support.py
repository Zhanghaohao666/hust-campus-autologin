import subprocess

from campus_autologin.config import AppConfig, load_config, write_default_config
from campus_autologin.gui_support import (
    GuiSettings,
    completed_process_to_result,
    run_service_action,
    save_gui_settings,
    tail_watch_log,
)


def test_save_gui_settings_writes_config_and_stores_non_empty_password(tmp_path):
    target = tmp_path / "config.toml"
    calls = []
    settings = GuiSettings(
        username="<student-id>",
        password="secret-password",
        interval_seconds=45,
        manual_login_url="http://172.18.18.61:8080/eportal/index.jsp?wlanuserip=abc",
        notifications_enabled=False,
        notify_login_success=False,
    )

    result = save_gui_settings(
        settings,
        config_path=target,
        store_password=lambda credential_target, username, password: calls.append(
            (credential_target, username, password)
        ),
    )
    loaded = load_config(target)
    content = target.read_text(encoding="utf-8")

    assert result.ok is True
    assert loaded.account.username == "<student-id>"
    assert loaded.watch.interval_seconds == 45
    assert loaded.portal.manual_login_url.endswith("wlanuserip=abc")
    assert loaded.notification.enabled is False
    assert loaded.notification.notify_login_success is False
    assert calls == [("hust-campus-autologin", "<student-id>", "secret-password")]
    assert "secret-password" not in content


def test_save_gui_settings_does_not_overwrite_password_when_empty(tmp_path):
    target = tmp_path / "config.toml"
    write_default_config(target, username="<old-id>")
    calls = []
    settings = GuiSettings(
        username="<new-id>",
        password="",
        interval_seconds=30,
        manual_login_url="",
        notifications_enabled=True,
        notify_login_success=True,
    )

    result = save_gui_settings(
        settings,
        config_path=target,
        store_password=lambda credential_target, username, password: calls.append(
            (credential_target, username, password)
        ),
    )
    loaded = load_config(target)

    assert result.ok is True
    assert loaded.account.username == "<new-id>"
    assert calls == []


def test_tail_watch_log_reads_recent_lines_from_config_log_dir(tmp_path):
    config = AppConfig(base_dir=tmp_path, config_path=tmp_path / "config.toml")
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "watch.log").write_text("one\ntwo\nthree\n", encoding="utf-8")

    assert tail_watch_log(config, lines=2) == ["two", "three"]


def test_completed_process_to_result_prefers_stdout_and_marks_returncode():
    ok_result = completed_process_to_result(
        "安装开机自启",
        subprocess.CompletedProcess(["cmd"], 0, stdout="created\n", stderr=""),
    )
    failed_result = completed_process_to_result(
        "安装开机自启",
        subprocess.CompletedProcess(["cmd"], 1, stdout="", stderr="denied\n"),
    )

    assert ok_result.ok is True
    assert ok_result.message == "安装开机自启成功: created"
    assert failed_result.ok is False
    assert failed_result.message == "安装开机自启失败: denied"


def test_completed_process_to_result_explains_missing_scheduled_task():
    raw_error = (
        "Start-ScheduledTask : 系统找不到指定的文件。\n"
        "+ Start-ScheduledTask -TaskName 'HUST Campus Autologin'\n"
        "+ FullyQualifiedErrorId : HRESULT 0x80070002,Start-ScheduledTask"
    )

    result = completed_process_to_result(
        "启动自动重连",
        subprocess.CompletedProcess(["cmd"], 1, stdout="", stderr=raw_error),
    )

    assert result.ok is False
    assert result.message == "启动自动重连失败: 还没有安装自动重连任务，请先点击“安装开机自启”。"


def test_run_service_action_uses_injected_runner():
    calls = []

    def runner():
        calls.append("called")
        return subprocess.CompletedProcess(["cmd"], 0, stdout="running\n", stderr="")

    result = run_service_action("启动自动重连", runner)

    assert calls == ["called"]
    assert result.ok is True
    assert result.message == "启动自动重连成功: running"
