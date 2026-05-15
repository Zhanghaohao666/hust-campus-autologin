import subprocess

from campus_autologin import process


def test_run_hidden_adds_create_no_window_on_windows(monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(process.os, "name", "nt")
    monkeypatch.setattr(process.subprocess, "run", fake_run)

    result = process.run_hidden(["powershell.exe"], capture_output=True, text=True)

    assert result.returncode == 0
    assert calls == [
        (
            ["powershell.exe"],
            {
                "capture_output": True,
                "text": True,
                "creationflags": subprocess.CREATE_NO_WINDOW,
            },
        )
    ]


def test_run_hidden_preserves_existing_creationflags(monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(kwargs)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(process.os, "name", "nt")
    monkeypatch.setattr(process.subprocess, "run", fake_run)

    process.run_hidden(["cmd"], creationflags=0x1)

    assert calls[0]["creationflags"] == (0x1 | subprocess.CREATE_NO_WINDOW)
