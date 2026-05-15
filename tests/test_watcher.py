from campus_autologin.eportal import LoginResult
from campus_autologin.network_probe import ProbeResult, ProbeStatus
from campus_autologin.watcher import WatchRunner


class FakeNotifier:
    def __init__(self):
        self.messages = []

    def notify(self, title, message):
        self.messages.append((title, message))
        return True


class FakeLogger:
    def __init__(self):
        self.infos = []
        self.warnings = []

    def info(self, message, *args):
        self.infos.append(message % args if args else message)

    def warning(self, message, *args):
        self.warnings.append(message % args if args else message)


def test_watch_runner_skips_not_campus_network():
    calls = {"login": 0}
    runner = WatchRunner(
        probe=lambda: ProbeResult(ProbeStatus.NOT_CAMPUS_NETWORK),
        login=lambda query: calls.__setitem__("login", calls["login"] + 1),
        sleep=lambda seconds: None,
        notifier=FakeNotifier(),
        logger=FakeLogger(),
        interval_seconds=30,
    )

    runner.run_once()

    assert calls["login"] == 0


def test_watch_runner_logs_in_on_captive_portal_and_notifies_success():
    notifier = FakeNotifier()
    runner = WatchRunner(
        probe=lambda: ProbeResult(ProbeStatus.CAPTIVE_PORTAL, query_string="wlanuserip=abc"),
        login=lambda query: LoginResult(True, "ok"),
        sleep=lambda seconds: None,
        notifier=notifier,
        logger=FakeLogger(),
        interval_seconds=30,
    )

    runner.run_once()

    assert notifier.messages == [("校园网已自动重联", "ok")]


def test_watch_runner_backs_off_after_failure_and_notifies_threshold():
    notifier = FakeNotifier()
    sleeps = []
    runner = WatchRunner(
        probe=lambda: ProbeResult(ProbeStatus.CAPTIVE_PORTAL, query_string="wlanuserip=abc"),
        login=lambda query: LoginResult(False, "bad password"),
        sleep=sleeps.append,
        notifier=notifier,
        logger=FakeLogger(),
        interval_seconds=30,
        max_backoff_seconds=300,
        failure_notify_threshold=2,
    )

    runner.run_once()
    runner.run_once()

    assert runner.failure_count == 2
    assert sleeps == [30, 60]
    assert notifier.messages == [("校园网自动重联失败", "bad password")]


def test_watch_runner_stops_when_stop_event_is_set():
    count = {"runs": 0}
    runner = WatchRunner(
        probe=lambda: ProbeResult(ProbeStatus.ONLINE),
        login=lambda query: LoginResult(True, "ok"),
        sleep=lambda seconds: None,
        notifier=FakeNotifier(),
        logger=FakeLogger(),
        interval_seconds=30,
    )

    def run_once_and_stop():
        count["runs"] += 1
        runner.stop()

    runner.run_once = run_once_and_stop
    runner.run()

    assert count["runs"] == 1
