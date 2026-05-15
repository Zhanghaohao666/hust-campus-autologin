from __future__ import annotations

import getpass
import os
import subprocess
import tomllib
from pathlib import Path


_NATIVE_PATH = type(Path.cwd())


class CredentialError(RuntimeError):
    pass


def build_cmdkey_command(target: str, username: str, password: str) -> list[str]:
    return [
        "cmdkey.exe",
        f"/generic:{target}",
        f"/user:{username}",
        f"/pass:{password}",
    ]


def parse_powershell_secret(stdout: str) -> str | None:
    value = stdout.strip()
    return value or None


def store_password(target: str, username: str, password: str) -> None:
    command = build_cmdkey_command(target, username, password)
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise CredentialError(result.stderr.strip() or result.stdout.strip())


def prompt_and_store_password(target: str, username: str) -> None:
    password = getpass.getpass("校园网密码: ")
    store_password_auto(target, username, password)


def read_password(target: str) -> str:
    script = rf"""
$signature = @'
using System;
using System.Runtime.InteropServices;
using System.Text;

public static class CredMan {{
  [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
  public struct CREDENTIAL {{
    public UInt32 Flags;
    public UInt32 Type;
    public string TargetName;
    public string Comment;
    public System.Runtime.InteropServices.ComTypes.FILETIME LastWritten;
    public UInt32 CredentialBlobSize;
    public IntPtr CredentialBlob;
    public UInt32 Persist;
    public UInt32 AttributeCount;
    public IntPtr Attributes;
    public string TargetAlias;
    public string UserName;
  }}

  [DllImport("advapi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
  public static extern bool CredRead(string target, UInt32 type, UInt32 reservedFlag, out IntPtr credentialPtr);

  [DllImport("advapi32.dll", SetLastError=true)]
  public static extern void CredFree(IntPtr buffer);
}}
'@
Add-Type -TypeDefinition $signature -ErrorAction SilentlyContinue | Out-Null
$ptr = [IntPtr]::Zero
if ([CredMan]::CredRead("{target}", 1, 0, [ref]$ptr)) {{
  try {{
    $cred = [Runtime.InteropServices.Marshal]::PtrToStructure($ptr, [type][CredMan+CREDENTIAL])
    if ($cred.CredentialBlobSize -gt 0) {{
      [Runtime.InteropServices.Marshal]::PtrToStringUni($cred.CredentialBlob, [int]($cred.CredentialBlobSize / 2))
    }}
  }} finally {{
    [CredMan]::CredFree($ptr)
  }}
}}
"""
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise CredentialError(result.stderr.strip())
    password = parse_powershell_secret(result.stdout)
    if password is None:
        raise CredentialError(f"credential not found: {target}")
    return password


def store_local_secret(
    path: str | Path, target: str, username: str, password: str
) -> None:
    secret_path = _coerce_path(path)
    secret_path.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, dict[str, str]] = {}
    if secret_path.exists() and secret_path.read_text(encoding="utf-8").strip():
        loaded = tomllib.loads(secret_path.read_text(encoding="utf-8"))
        data = {
            str(key): {
                "username": str(value.get("username", "")),
                "password": str(value.get("password", "")),
            }
            for key, value in loaded.items()
            if isinstance(value, dict)
        }

    data[target] = {"username": username, "password": password}
    lines: list[str] = []
    for key, value in data.items():
        lines.append(f'["{_toml_escape(key)}"]')
        lines.append(f'username = "{_toml_escape(value.get("username", ""))}"')
        lines.append(f'password = "{_toml_escape(value.get("password", ""))}"')
        lines.append("")

    secret_path.write_text("\n".join(lines), encoding="utf-8")
    if os.name != "nt":
        os.chmod(secret_path, 0o600)


def read_local_secret(path: str | Path, target: str) -> str:
    secret_path = _coerce_path(path)
    if not secret_path.exists():
        raise CredentialError(f"credential not found: {target}")
    content = secret_path.read_text(encoding="utf-8")
    data = tomllib.loads(content) if content.strip() else {}
    section = data.get(target)
    if not isinstance(section, dict) or not section.get("password"):
        raise CredentialError(f"credential not found: {target}")
    return str(section["password"])


def store_password_auto(
    target: str,
    username: str,
    password: str,
    *,
    secret_path: str | Path | None = None,
) -> None:
    if os.name == "nt":
        store_password(target, username, password)
        return
    if secret_path is None:
        from campus_autologin.paths import default_secret_path

        secret_path = default_secret_path()
    store_local_secret(secret_path, target, username, password)


def read_password_auto(
    target: str,
    *,
    secret_path: str | Path | None = None,
) -> str:
    if os.name == "nt":
        return read_password(target)
    if secret_path is None:
        from campus_autologin.paths import default_secret_path

        secret_path = default_secret_path()
    return read_local_secret(secret_path, target)


def _coerce_path(path: str | Path) -> Path:
    if isinstance(path, Path):
        return path
    return _NATIVE_PATH(path)


def _toml_escape(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"')
