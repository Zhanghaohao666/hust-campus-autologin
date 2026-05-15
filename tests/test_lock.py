import os

from campus_autologin.lock import WatchLock, WatchLockError


def test_watch_lock_creates_and_removes_lock_file(tmp_path):
    lock_path = tmp_path / "watch.lock"

    with WatchLock(lock_path):
        assert lock_path.exists()
        assert f"pid={os.getpid()}" in lock_path.read_text(encoding="utf-8")

    assert not lock_path.exists()


def test_watch_lock_rejects_active_pid(tmp_path):
    lock_path = tmp_path / "watch.lock"
    lock_path.write_text(f"pid={os.getpid()}\nstarted_at=x\nhostname=y\n", encoding="utf-8")

    try:
        with WatchLock(lock_path):
            raise AssertionError("should not acquire active lock")
    except WatchLockError as exc:
        assert "already running" in str(exc)


def test_watch_lock_takes_over_stale_pid(tmp_path):
    lock_path = tmp_path / "watch.lock"
    lock_path.write_text("pid=99999999\nstarted_at=x\nhostname=y\n", encoding="utf-8")

    with WatchLock(lock_path):
        assert f"pid={os.getpid()}" in lock_path.read_text(encoding="utf-8")
