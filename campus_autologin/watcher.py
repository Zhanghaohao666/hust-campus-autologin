from __future__ import annotations

import logging
import signal
import time
from collections.abc import Callable

from campus_autologin.eportal import LoginResult
from campus_autologin.network_probe import ProbeResult, ProbeStatus


class WatchRunner:
    def __init__(
        self,
        *,
        probe: Callable[[], ProbeResult],
        login: Callable[[str | None], LoginResult],
        sleep: Callable[[int], None],
        notifier,
        logger: logging.Logger | object,
        interval_seconds: int,
        max_backoff_seconds: int = 300,
        failure_notify_threshold: int = 3,
    ) -> None:
        self._probe = probe
        self._login = login
        self._sleep = sleep
        self._notifier = notifier
        self._logger = logger
        self._interval_seconds = interval_seconds
        self._max_backoff_seconds = max_backoff_seconds
        self._failure_notify_threshold = failure_notify_threshold
        self._stopped = False
        self.failure_count = 0

    def install_signal_handlers(self) -> None:
        def handler(signum, frame):
            self.stop()

        signal.signal(signal.SIGINT, handler)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, handler)

    def stop(self) -> None:
        self._stopped = True

    def run(self) -> None:
        while not self._stopped:
            self.run_once()

    def run_once(self) -> None:
        result = self._probe()
        if result.status is ProbeStatus.ONLINE:
            self.failure_count = 0
            self._logger.info("campus network online")
            self._sleep(self._interval_seconds)
            return

        if result.status is ProbeStatus.NOT_CAMPUS_NETWORK:
            self._logger.info("not on campus network; skipping login")
            self._sleep(self._interval_seconds)
            return

        if result.status in {ProbeStatus.CAPTIVE_PORTAL, ProbeStatus.PORTAL_REACHABLE}:
            login_result = self._login(result.query_string)
            if login_result.success:
                self.failure_count = 0
                self._logger.info("campus login success: %s", login_result.message)
                self._notifier.notify("校园网已自动重联", login_result.message or "登录成功")
                self._sleep(10)
                return
            self.failure_count += 1
            self._logger.warning("campus login failed: %s", login_result.message)
            if self.failure_count >= self._failure_notify_threshold:
                self._notifier.notify("校园网自动重联失败", login_result.message)
            self._sleep(self._backoff_seconds())
            return

        self._logger.warning("network probe status: %s", result.status.value)
        self._sleep(self._backoff_seconds())

    def _backoff_seconds(self) -> int:
        if self.failure_count <= 0:
            return self._interval_seconds
        return min(
            self._interval_seconds * (2 ** (self.failure_count - 1)),
            self._max_backoff_seconds,
        )


def default_sleep(seconds: int) -> None:
    time.sleep(seconds)
