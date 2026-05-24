!ifndef APP_VERSION
!define APP_VERSION "0.2.4"
!endif

!ifndef SOURCE_EXE
!define SOURCE_EXE "..\..\dist\windows-portable\HUSTCampusAutologin.exe"
!endif

!ifndef SOURCE_CLI_EXE
!define SOURCE_CLI_EXE "..\..\dist\windows-portable\HUSTCampusAutologinCLI.exe"
!endif

!ifndef OUT_FILE
!define OUT_FILE "..\..\dist\HUSTCampusAutologinSetup-${APP_VERSION}.exe"
!endif

!define APP_NAME "HUST Campus Autologin"
!define COMPANY_NAME "HUST Campus Autologin contributors"
!define EXE_NAME "HUSTCampusAutologin.exe"
!define CLI_EXE_NAME "HUSTCampusAutologinCLI.exe"
!define UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\HUSTCampusAutologin"

Name "${APP_NAME}"
OutFile "${OUT_FILE}"
InstallDir "$LOCALAPPDATA\HUST Campus Autologin"
RequestExecutionLevel user
Unicode true
SetCompressor /SOLID lzma

Page directory
Page instfiles

UninstPage uninstConfirm
UninstPage instfiles

Section "Install"
  SetOutPath "$INSTDIR"
  File "${SOURCE_EXE}"
  File "${SOURCE_CLI_EXE}"
  File "..\..\README.md"
  File "..\..\config.example.toml"

  SetOutPath "$INSTDIR\docs"
  File "..\..\docs\windows-source.md"
  File "..\..\docs\windows-package.md"
  File "..\..\docs\troubleshooting.md"
  File "..\..\docs\linux-systemd.md"

  SetOutPath "$INSTDIR"
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  CreateDirectory "$SMPROGRAMS\${APP_NAME}"
  CreateShortCut "$SMPROGRAMS\${APP_NAME}\HUST Campus Autologin.lnk" "$INSTDIR\${EXE_NAME}"
  CreateShortCut "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk" "$INSTDIR\Uninstall.exe"

  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayName" "${APP_NAME}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "Publisher" "${COMPANY_NAME}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoRepair" 1
SectionEnd

Section "Uninstall"
  IfFileExists "$INSTDIR\${EXE_NAME}" 0 +2
    ExecWait '"$INSTDIR\${EXE_NAME}" uninstall-service'

  Delete "$SMPROGRAMS\${APP_NAME}\HUST Campus Autologin.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk"
  RMDir "$SMPROGRAMS\${APP_NAME}"

  Delete "$INSTDIR\docs\windows-source.md"
  Delete "$INSTDIR\docs\windows-package.md"
  Delete "$INSTDIR\docs\troubleshooting.md"
  Delete "$INSTDIR\docs\linux-systemd.md"
  RMDir "$INSTDIR\docs"

  Delete "$INSTDIR\README.md"
  Delete "$INSTDIR\config.example.toml"
  Delete "$INSTDIR\${EXE_NAME}"
  Delete "$INSTDIR\${CLI_EXE_NAME}"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"

  DeleteRegKey HKCU "${UNINSTALL_KEY}"
SectionEnd
