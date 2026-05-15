# Desktop UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a double-clickable desktop UI that lets users configure, test, run, and inspect HUST Campus Autologin without editing config files.

**Architecture:** Add a small GUI layer over the existing CLI/service/login modules. Keep campus authentication, proxy bypass, dynamic portal discovery, and scheduled-task logic in the current backend modules.

**Tech Stack:** Python 3.11, Tkinter standard library, existing `requests` backend, PyInstaller for Windows packaging, pytest for support-module tests.

---

### Task 1: Config Writer Support

**Files:**
- Modify: `campus_autologin/config.py`
- Test: `tests/test_config.py`

- [ ] Add a failing test that loads a config with UI-provided username, interval, manual portal URL, notification settings, and preserved portal defaults.
- [ ] Run `pytest tests/test_config.py -v` and confirm the new test fails because a general writer does not exist.
- [ ] Implement `render_config(config: AppConfig) -> str` and `write_config(config: AppConfig, path: str | Path | None = None) -> Path`.
- [ ] Run `pytest tests/test_config.py -v` and confirm it passes.

### Task 2: UI Support Layer

**Files:**
- Create: `campus_autologin/gui_support.py`
- Test: `tests/test_gui_support.py`

- [ ] Add failing tests for `GuiSettings`, `save_gui_settings`, `tail_watch_log`, and service command result formatting.
- [ ] Run `pytest tests/test_gui_support.py -v` and confirm failures are for missing module/functions.
- [ ] Implement the support layer with dependency injection for credential storage, config loading, config writing, and service command execution.
- [ ] Run `pytest tests/test_gui_support.py -v` and confirm it passes.

### Task 3: Desktop Window

**Files:**
- Create: `campus_autologin/gui.py`
- Modify: `campus_autologin/__main__.py`

- [ ] Implement a Tkinter app using the `DESIGN (1).md` palette: navy sidebar, off-white canvas, indigo primary pill buttons, compact forms, and tabular log/status text.
- [ ] Add pages for Overview, Setup, Service, Logs, and Diagnostics.
- [ ] Add a `gui` CLI command that launches the app.
- [ ] Ensure long-running actions use background threads.

### Task 4: Windows Packaging

**Files:**
- Create: `packaging/windows/gui_entrypoint.py`
- Modify: Windows build scripts/docs that reference the PyInstaller entrypoint.
- Modify: `docs/windows-package.md`
- Modify: `README.md`

- [ ] Add a GUI entrypoint for windowed PyInstaller builds.
- [ ] Keep the CLI entrypoint documented for advanced users.
- [ ] Update installer/portable docs so double-click users launch the GUI first.

### Task 5: Verification

**Files:**
- Test: `tests/*`

- [ ] Run `pytest`.
- [ ] Run `python -m campus_autologin gui` on Windows to verify the window opens.
- [ ] Run packaging commands if PyInstaller/NSIS are available locally.
- [ ] Check `git diff` for accidental password, local-only path, or unrelated file changes.
