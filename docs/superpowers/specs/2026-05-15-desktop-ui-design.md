# HUST Campus Autologin Desktop UI Design

## Goal

Build a Windows-friendly desktop UI so users can configure and operate HUST Campus Autologin without editing TOML files or using PowerShell commands.

## Visual Direction

The UI follows `C:\Users\10951\Downloads\DESIGN (1).md`:

- Deep navy app shell (`#0d253d`, `#1c1e54`) for the left navigation and status header.
- White and cool off-white work surfaces (`#ffffff`, `#f6f9fc`) for forms, logs, and diagnostics.
- Indigo (`#533afd`) as the primary action color for save, login, and start actions.
- Pill buttons, 6 px inputs, 8 px spacing rhythm, and tabular numeric text for intervals, timestamps, and counters.
- Product-console layout rather than a marketing page: the first screen is the usable dashboard.

## User Experience

The installed app opens a UI by default. Users can:

- Fill campus network username and password.
- Save configuration without touching `config.toml`.
- Optionally paste a browser-captured portal URL.
- Choose probe interval and notification behavior.
- Test login immediately.
- Install, uninstall, start, and stop automatic reconnect.
- View recent logs in the UI.
- Run a diagnostic check that reports config, credential, proxy, and service status.

## Architecture

The UI is a thin desktop wrapper over the existing package. It does not duplicate campus login logic.

- `campus_autologin.gui` owns the window, layout, background worker threads, and user-facing status messages.
- `campus_autologin.gui_support` owns UI-safe operations: save config, save credential, read logs, run login, and manage service state.
- `campus_autologin.config` gains a general config writer so the UI can update existing values without dropping defaults.
- `packaging/windows/gui_entrypoint.py` starts the GUI for double-click users.
- The existing CLI remains available for source and advanced users.

## Data Flow

1. UI loads `AppConfig` from the default config path.
2. User edits fields.
3. Save action writes TOML config and stores the password in the existing credential backend.
4. Test login action calls the existing direct-session login path, which still bypasses Clash/proxy.
5. Service actions call the existing Windows scheduled-task helpers.
6. Logs panel tails `watch.log`.

## Error Handling

- Long actions run in background threads so the window stays responsive.
- Credential/config errors are shown as short status messages.
- Passwords are never written to logs or visible in diagnostics.
- Failed login/service commands display the returned message and keep the current form contents intact.

## Testing

Automated tests cover UI support behavior that can be tested without opening a desktop window:

- Saving a complete UI settings model writes expected config fields.
- Empty passwords do not overwrite existing credentials.
- Log tailing returns recent log lines.
- Service command wrappers expose command result status for UI display.

Manual verification covers the actual window launch and packaged executable behavior.
