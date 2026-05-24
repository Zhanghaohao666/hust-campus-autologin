from __future__ import annotations

import argparse
import os
import subprocess

from campus_autologin.config import load_config, write_default_config
from campus_autologin.credentials import (
    CredentialError,
    prompt_and_store_password,
    read_password_auto,
)
from campus_autologin.eportal import EportalClient, LoginResult, QueryStringCache
from campus_autologin.http_client import create_direct_session
from campus_autologin.lock import WatchLock, WatchLockError
from campus_autologin.logging_setup import setup_logging
from campus_autologin.logs import tail_lines
from campus_autologin.network_probe import ProbeStatus, probe_connectivity
from campus_autologin.notifier import Notifier
from campus_autologin.portal_url import parse_portal_url
from campus_autologin.process import run_hidden
from campus_autologin.scheduler import (
    install_task,
    restart_task,
    start_task,
    stop_task,
    uninstall_task,
)
from campus_autologin.watcher import WatchRunner, default_sleep


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="campus-autologin")
    parser.add_argument("--config", default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("gui")
    subparsers.add_parser("doctor")

    init = subparsers.add_parser("init")
    init.add_argument("--username", required=True)
    init.add_argument("--interval", type=int, default=30)
    init.add_argument("--manual-login-url", default="")

    set_credential = subparsers.add_parser("set-credential")
    set_credential.add_argument("--username", required=True)

    subparsers.add_parser("login")
    subparsers.add_parser("watch")
    logs = subparsers.add_parser("logs")
    logs.add_argument("--lines", type=int, default=80)

    subparsers.add_parser("install-service")
    subparsers.add_parser("start-service")
    subparsers.add_parser("stop-service")
    subparsers.add_parser("restart-service")
    subparsers.add_parser("uninstall-service")
    subparsers.add_parser("service-status")
    subparsers.add_parser("install-task")
    subparsers.add_parser("start-task")
    subparsers.add_parser("stop-task")
    subparsers.add_parser("restart-task")
    subparsers.add_parser("uninstall-task")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config(args.config)
    logger = setup_logging(config.log_dir, config.logging.level)

    if args.command == "gui":
        from campus_autologin.gui import launch_gui

        return launch_gui(args.config)
    if args.command == "doctor":
        return run_doctor(config)
    if args.command == "init":
        write_default_config(
            config.config_path,
            username=args.username,
            interval_seconds=args.interval,
            manual_login_url=args.manual_login_url,
        )
        print(f"Config written: {config.config_path}")
        return 0
    if args.command == "set-credential":
        if not config.config_path.exists():
            write_default_config(config.config_path, username=args.username)
        prompt_and_store_password(config.account.credential_target, args.username)
        print("Credential saved.")
        return 0
    if args.command == "login":
        result = run_login(config, logger=logger)
        print(("SUCCESS" if result.success else "FAILED") + f": {result.message}")
        return 0 if result.success else 1
    if args.command == "watch":
        return run_watch(config, logger=logger)
    if args.command == "logs":
        for line in tail_lines(config.log_dir / "watch.log", args.lines):
            print(line)
        return 0
    if args.command in {
        "install-service",
        "start-service",
        "stop-service",
        "restart-service",
        "uninstall-service",
        "service-status",
    }:
        return run_service_command(args.command)
    if args.command == "install-task":
        result = install_task()
        print(result.stdout or result.stderr)
        return result.returncode
    if args.command == "start-task":
        result = start_task()
        print(result.stdout or result.stderr)
        return result.returncode
    if args.command == "stop-task":
        result = stop_task()
        print(result.stdout or result.stderr)
        return result.returncode
    if args.command == "restart-task":
        result = restart_task()
        print(result.stdout or result.stderr)
        return result.returncode
    if args.command == "uninstall-task":
        result = uninstall_task()
        print(result.stdout or result.stderr)
        return result.returncode
    parser.error("unknown command")
    return 2


def run_service_command(command: str) -> int:
    if os.name == "nt":
        if command == "install-service":
            result = install_task()
        elif command == "start-service":
            result = start_task()
        elif command == "stop-service":
            result = stop_task()
        elif command == "restart-service":
            result = restart_task()
        elif command == "uninstall-service":
            result = uninstall_task()
        else:
            result = run_hidden(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-Command",
                    "Get-ScheduledTask -TaskName 'HUST Campus Autologin' | Format-List",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
    else:
        from campus_autologin.linux_service import (
            install_service,
            restart_service,
            service_status,
            start_service,
            stop_service,
            uninstall_service,
        )

        if command == "install-service":
            result = install_service()
        elif command == "start-service":
            result = start_service()
        elif command == "stop-service":
            result = stop_service()
        elif command == "restart-service":
            result = restart_service()
        elif command == "uninstall-service":
            result = uninstall_service()
        else:
            result = service_status()
    print(result.stdout or result.stderr)
    return result.returncode


def run_doctor(config) -> int:
    print(f"Config: {config.config_path}")
    print(f"Username: {config.account.username or '(not set)'}")
    print(f"Credential target: {config.account.credential_target}")
    print(f"Portal bases: {', '.join(config.portal.base_urls)}")
    print(f"Notifications: {'enabled' if config.notification.enabled else 'disabled'}")
    try:
        read_password_auto(config.account.credential_target)
        print("Credential: present")
    except CredentialError:
        print("Credential: missing")

    proxy = _read_windows_proxy()
    if proxy:
        print(proxy)
    return 0


def run_login(config, *, logger) -> LoginResult:
    if not config.account.username:
        return LoginResult(False, "username is not configured")
    try:
        password = read_password_auto(config.account.credential_target)
    except CredentialError as exc:
        return LoginResult(False, str(exc))

    session = create_direct_session()
    probe = probe_connectivity(
        session=session,
        probe_urls=config.portal.probe_urls,
        portal_base_urls=config.portal.base_urls,
        timeout=config.watch.probe_timeout_seconds,
        campus_hints=_collect_campus_hints(config),
        manual_login_url=config.portal.manual_login_url,
    )
    if probe.status is ProbeStatus.ONLINE:
        return LoginResult(True, "already online")
    if probe.status is ProbeStatus.NOT_CAMPUS_NETWORK:
        return LoginResult(False, "not on campus network")

    query_string = probe.query_string
    if not query_string:
        return LoginResult(False, "queryString not found")

    base_url = _base_from_portal_url(probe.portal_url) or config.portal.base_urls[0]
    client = EportalClient(
        session=session,
        base_url=base_url,
        query_cache=QueryStringCache(config.watch.querystring_cache_ttl_seconds),
    )
    return client.login(
        username=config.account.username,
        password=password,
        query_string=query_string,
        timeout=config.watch.login_timeout_seconds,
    )


def run_watch(config, *, logger) -> int:
    notifier = Notifier(enabled=config.notification.enabled)
    session = create_direct_session()
    cache = QueryStringCache(config.watch.querystring_cache_ttl_seconds)
    current_portal_url: dict[str, str | None] = {"value": None}

    def probe():
        result = probe_connectivity(
            session=session,
            probe_urls=config.portal.probe_urls,
            portal_base_urls=config.portal.base_urls,
            timeout=config.watch.probe_timeout_seconds,
            campus_hints=_collect_campus_hints(config),
            manual_login_url=config.portal.manual_login_url,
        )
        current_portal_url["value"] = result.portal_url
        return result

    def login(query_string: str | None):
        if not query_string:
            cached = cache.get()
            query_string = cached
        if not query_string:
            return LoginResult(False, "queryString not found")
        try:
            password = read_password_auto(config.account.credential_target)
        except CredentialError as exc:
            return LoginResult(False, str(exc))
        client = EportalClient(
            session=session,
            base_url=_base_from_portal_url(current_portal_url["value"])
            or config.portal.base_urls[0],
            query_cache=cache,
        )
        return client.login(
            username=config.account.username,
            password=password,
            query_string=query_string,
            timeout=config.watch.login_timeout_seconds,
        )

    try:
        with WatchLock(config.lock_path):
            runner = WatchRunner(
                probe=probe,
                login=login,
                sleep=default_sleep,
                notifier=notifier,
                logger=logger,
                interval_seconds=config.watch.interval_seconds,
                max_backoff_seconds=config.watch.max_backoff_seconds,
                failure_notify_threshold=config.notification.notify_failure_threshold,
            )
            runner.install_signal_handlers()
            runner.run()
            logger.info("watch process exited")
            return 0
    except WatchLockError as exc:
        logger.warning(str(exc))
        return 1


def _base_from_portal_url(portal_url: str | None) -> str | None:
    if not portal_url:
        return None
    try:
        return parse_portal_url(portal_url).base_url
    except ValueError:
        return None


def _collect_campus_hints(config) -> list[str]:
    hints: list[str] = []
    try:
        result = run_hidden(
            ["powershell.exe", "-NoProfile", "-Command", "Get-NetConnectionProfile | Select-Object -ExpandProperty Name"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        hints.extend(line.strip() for line in result.stdout.splitlines() if line.strip())
    except Exception:
        pass
    try:
        result = run_hidden(
            ["ipconfig", "/all"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        hints.append(result.stdout)
    except Exception:
        pass
    return hints


def _read_windows_proxy() -> str:
    from campus_autologin.gui_support import read_windows_proxy

    return read_windows_proxy()


if __name__ == "__main__":
    raise SystemExit(main())
