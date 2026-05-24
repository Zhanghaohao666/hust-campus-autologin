from pathlib import Path


def test_windows_installer_offers_unchecked_desktop_shortcut_option():
    script = Path("installer/windows/HUSTCampusAutologin.nsi").read_text(encoding="utf-8")

    assert "Page components" in script
    assert 'Section /o "创建桌面快捷方式" SEC_DESKTOP' in script
    assert 'CreateShortCut "$DESKTOP\\${APP_NAME}.lnk" "$INSTDIR\\${EXE_NAME}"' in script
    assert 'Delete "$DESKTOP\\${APP_NAME}.lnk"' in script
