from __future__ import annotations

from typing import Callable


class Notifier:
    def __init__(
        self,
        *,
        enabled: bool,
        importer: Callable[[str], object] | None = None,
    ) -> None:
        self.enabled = enabled
        self._importer = importer or __import__

    def notify(self, title: str, message: str) -> bool:
        if not self.enabled:
            return False
        try:
            module = self._importer("winotify")
            toast = module.Notification(
                app_id="HUST Campus Autologin",
                title=title,
                msg=message,
            )
            toast.show()
            return True
        except Exception:
            return False
