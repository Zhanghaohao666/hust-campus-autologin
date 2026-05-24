from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path


class WatchLockError(RuntimeError):
    pass


class WatchLock:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._acquired = False

    def __enter__(self) -> "WatchLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            pid = _read_pid(self.path)
            if pid is not None and _pid_is_running(pid):
                raise WatchLockError(f"watch already running with pid {pid}")
        self.path.write_text(
            "\n".join(
                [
                    f"pid={os.getpid()}",
                    f"started_at={datetime.now().isoformat(timespec='seconds')}",
                    f"hostname={os.environ.get('COMPUTERNAME', 'unknown')}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        self._acquired = True

    def release(self) -> None:
        if not self._acquired:
            return
        try:
            if self.path.exists() and _read_pid(self.path) == os.getpid():
                self.path.unlink()
        finally:
            self._acquired = False


def _read_pid(path: Path) -> int | None:
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("pid="):
                return int(line.split("=", 1)[1])
    except (OSError, ValueError):
        return None
    return None


def _pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform.startswith("win"):
        return _pid_is_running_windows(pid)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _pid_is_running_windows(pid: int) -> bool:
    import ctypes
    from ctypes import wintypes

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259
    handle = ctypes.windll.kernel32.OpenProcess(
        PROCESS_QUERY_LIMITED_INFORMATION, False, wintypes.DWORD(pid)
    )
    if not handle:
        return False
    try:
        exit_code = wintypes.DWORD()
        if not ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return False
        return exit_code.value == STILL_ACTIVE
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)
