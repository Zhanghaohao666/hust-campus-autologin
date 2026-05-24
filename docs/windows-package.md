# Windows Portable And Installer Builds

This document describes the Windows distribution artifacts for maintainers.

## Artifacts

The build script creates:

- `dist/windows-portable/HUSTCampusAutologin.exe`
- `dist/windows-portable/HUSTCampusAutologinCLI.exe`
- `dist/HUSTCampusAutologin-0.2.4-windows-portable.zip`
- `dist/HUSTCampusAutologinSetup-0.2.4.exe`

`HUSTCampusAutologin.exe` is the desktop UI. Double-clicking it opens the configuration and operations window.

`HUSTCampusAutologinCLI.exe` is the console application. It supports the same commands as the source version:

```powershell
.\HUSTCampusAutologinCLI.exe doctor
.\HUSTCampusAutologinCLI.exe init --username <student-id>
.\HUSTCampusAutologinCLI.exe set-credential --username <student-id>
.\HUSTCampusAutologinCLI.exe login
.\HUSTCampusAutologinCLI.exe install-service
.\HUSTCampusAutologinCLI.exe start-service
.\HUSTCampusAutologinCLI.exe stop-service
.\HUSTCampusAutologinCLI.exe restart-service
```

When run from the packaged UI, `install-service` registers Windows Task Scheduler to launch:

```text
HUSTCampusAutologin.exe watch
```

## Build Requirements

- Python 3.11+
- PyInstaller
- NSIS, available through `makensis.exe`

Install Python build dependencies:

```powershell
python -m pip install -e ".[build,notify]"
```

Build both artifacts:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build-windows.ps1
```

Build only the portable exe and zip:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build-windows.ps1 -SkipInstaller
```

## Installer Behavior

The NSIS installer is per-user and does not require administrator privileges. It installs under:

```text
%LOCALAPPDATA%\HUST Campus Autologin
```

It creates Start Menu shortcuts for the desktop UI and uninstall. During uninstall it also calls `uninstall-service` to remove the scheduled task if present.
