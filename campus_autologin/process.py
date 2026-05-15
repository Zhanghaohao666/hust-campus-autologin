from __future__ import annotations

import os
import subprocess
from typing import Any


def run_hidden(command, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(command, **_with_hidden_window(kwargs))


def _with_hidden_window(kwargs: dict[str, Any]) -> dict[str, Any]:
    if os.name != "nt":
        return kwargs
    hidden = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if hidden:
        kwargs["creationflags"] = int(kwargs.get("creationflags", 0)) | hidden
    return kwargs
