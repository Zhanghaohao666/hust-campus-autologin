from __future__ import annotations

from pathlib import Path


def tail_lines(path: str | Path, count: int) -> list[str]:
    log_path = Path(path)
    if not log_path.exists():
        return []
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    return lines[-count:]
