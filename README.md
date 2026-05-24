# HUST Campus Autologin

[中文](#中文) | [English](#english)

---

<a id="中文"></a>

## 中文

华中科技大学校园网 eportal 自动重联工具。它用于解决校园网登录时间过长、网络波动、被挤占下线后需要手动打开认证页重新登录的问题，尤其适合需要长期在线的 Windows 电脑、宿舍服务器、软路由旁路机和 Ubuntu/Linux 主机。

如果你正在使用 Clash Verge、代理或 VPN，本工具不会关闭或修改它们。程序自己的探测和登录请求会直连校园网认证地址，绕过系统代理和环境代理，尽量做到“代理开着也能自动重联校园网”。

### 功能作用

- 自动检测当前网络是否在线、是否进入校园网认证态。
- 自动发现 `eportal/index.jsp?...` 认证页并提取动态 `queryString`。
- 支持 HUST eportal 当前的加密密码登录流程。
- 直连认证接口，绕过系统代理、环境代理和 Clash Verge。
- 提供 Windows 桌面 UI，可填写账号、密码、认证页 URL、探测间隔并查看日志。
- 支持 Windows 便携版 exe、Windows NSIS 安装包、Windows 源码运行。
- 支持 Ubuntu/Linux 源码运行和 `systemd --user` 常驻服务。
- 支持手动填写完整认证页 URL 作为自动发现失败时的 fallback。
- 使用锁文件防止 watch 常驻进程多开。
- 支持查看日志、诊断配置、安装/卸载后台服务。
- 密码不写入配置文件和日志。

### 实现思路

工具的核心流程是：

1. 使用多个直连 HTTP 探测地址判断网络状态。
2. 如果请求被校园网劫持到 `eportal/index.jsp?...`，从响应 URL 或 HTML 中提取完整认证页地址。
3. 从认证页地址中解析 `queryString`，并根据地址推导认证接口基址，例如 `http://172.18.18.61:8080/eportal`。
4. 调用 `InterFace.do?method=pageInfo` 获取登录参数。如果门户要求加密密码，则按照页面脚本逻辑生成 `password + ">" + mac`，反转后使用门户下发的 RSA 公钥加密。
5. 调用 `InterFace.do?method=login` 提交用户名、加密密码和当前 `queryString`。
6. `watch` 常驻循环会定时探测；断联后自动登录，成功后继续低频探测。

Windows 上的密码默认保存在 Windows Credential Manager。Linux 源码版默认使用本地 `secrets.toml`，并在非 Windows 系统上设置为 `0600` 权限。

### Windows 直接下载使用

到 [GitHub Releases](https://github.com/Zhanghaohao666/hust-campus-autologin/releases) 下载：

- `HUSTCampusAutologinSetup-0.2.3.exe`：安装包，推荐普通用户使用。
- `HUSTCampusAutologin-0.2.3-windows-portable.zip`：便携版压缩包，解压即可运行。
- `HUSTCampusAutologin.exe`：桌面 UI，双击即可配置和操作。
- `HUSTCampusAutologinCLI.exe`：命令行程序，适合高级用户和排障。

安装包是 per-user 安装，不需要管理员权限。默认安装到：

```text
%LOCALAPPDATA%\HUST Campus Autologin
```

安装包安装后，从开始菜单打开 **HUST Campus Autologin**。便携版解压后双击 `HUSTCampusAutologin.exe`。在 UI 中填写账号和密码，点击“保存配置”，再点击“测试登录”或“安装开机自启”。

如果要使用命令行，在 PowerShell 中进入目录运行：

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

`install-service` 会注册 Windows 任务计划程序，让工具开机后自动后台运行：

```text
HUSTCampusAutologin.exe watch
```

查看日志：

```powershell
.\HUSTCampusAutologinCLI.exe logs --lines 80
```

卸载后台任务：

```powershell
.\HUSTCampusAutologinCLI.exe uninstall-service
```

### Windows 源码运行

源码运行见 [docs/windows-source.md](docs/windows-source.md)。

```powershell
python -m pip install -e ".[test,notify]"
python -m campus_autologin gui
python -m campus_autologin init --username <student-id>
python -m campus_autologin set-credential --username <student-id>
python -m campus_autologin login
python -m campus_autologin install-service
```

Windows portable exe 和 NSIS 安装包的构建说明见 [docs/windows-package.md](docs/windows-package.md)。

### Ubuntu / Linux 服务器运行

Linux 使用说明见 [docs/linux-systemd.md](docs/linux-systemd.md)。

```bash
python3 -m pip install --user -e ".[linux]"
python3 -m campus_autologin init --username <student-id>
python3 -m campus_autologin set-credential --username <student-id>
python3 -m campus_autologin login
python3 -m campus_autologin install-service
```

也可以运行一键脚本：

```bash
bash scripts/install-linux.sh
```

### 常用命令

```bash
python -m campus_autologin doctor
python -m campus_autologin init --username <student-id> --interval 30
python -m campus_autologin set-credential --username <student-id>
python -m campus_autologin login
python -m campus_autologin watch
python -m campus_autologin logs --lines 80
python -m campus_autologin install-service
python -m campus_autologin service-status
python -m campus_autologin uninstall-service
```

### 手动认证页 URL

如果自动发现认证页失败，可以复制浏览器弹出的完整认证页地址：

```bash
python -m campus_autologin init --username <student-id> --manual-login-url "http://172.18.18.61:8080/eportal/index.jsp?..."
```

这个 URL 可能含有当前设备、接入点、内网 IP 和会话信息，不要公开粘贴到 issue、README 或截图中。

### 安全说明

- 密码不会写入配置文件或日志。
- Windows 默认使用 Windows Credential Manager 保存密码。
- Linux 源码版默认使用本地 `secrets.toml` 保存密码，并设置为 `0600` 权限。
- 本工具只自动提交你本来可以在浏览器页面手动提交的校园网认证请求，不绕过学校认证规则。
- 如果账号密码错误、账号受限、欠费、非上网时段或学校认证服务不可用，工具不会强行联网。

### 排障

常见问题见 [docs/troubleshooting.md](docs/troubleshooting.md)。

---

<a id="english"></a>

## English

HUST Campus Autologin is an auto-reconnect helper for the HUST campus network eportal. It is designed for machines that need to stay online for a long time, such as Windows desktops, dorm servers, mini PCs, routers, and Ubuntu/Linux hosts.

If you use Clash Verge, a proxy, or a VPN, this tool does not turn them off or change their settings. Its own HTTP probes and login requests bypass system and environment proxies, so campus authentication can still run while your proxy is enabled.

### What It Does

- Detects whether the network is online or stuck behind the campus captive portal.
- Discovers `eportal/index.jsp?...` and extracts the dynamic `queryString`.
- Supports the current HUST eportal encrypted password flow.
- Sends authentication requests directly, bypassing system proxies and Clash Verge.
- Provides a Windows desktop UI for account setup, password storage, manual portal URL, interval selection, and logs.
- Supports Windows portable exe, Windows NSIS installer, and Windows source usage.
- Supports Ubuntu/Linux source usage and `systemd --user` service.
- Supports a manually provided full portal URL as a fallback.
- Uses a lock file to prevent duplicate watcher processes.
- Provides commands for logs, diagnostics, service install, and service uninstall.
- Keeps passwords out of config files and logs.

### How It Works

The core flow is:

1. Probe several HTTP endpoints directly to determine network state.
2. If the request is redirected to `eportal/index.jsp?...`, extract the full portal URL from the response URL or HTML.
3. Parse the `queryString` from the portal URL and infer the eportal base URL, such as `http://172.18.18.61:8080/eportal`.
4. Call `InterFace.do?method=pageInfo` to get login parameters. If encrypted passwords are required, generate `password + ">" + mac`, reverse it, and encrypt it using the RSA public key returned by the portal.
5. Call `InterFace.do?method=login` with the username, encrypted password, and current `queryString`.
6. The `watch` loop keeps probing at intervals and automatically logs in again when the network falls back to the captive portal state.

On Windows, passwords are stored in Windows Credential Manager. On Linux source installs, passwords are stored in a local `secrets.toml` file with `0600` permissions.

### Windows Download

Download from [GitHub Releases](https://github.com/Zhanghaohao666/hust-campus-autologin/releases):

- `HUSTCampusAutologinSetup-0.2.3.exe`: installer, recommended for most Windows users.
- `HUSTCampusAutologin-0.2.3-windows-portable.zip`: portable zip.
- `HUSTCampusAutologin.exe`: desktop UI; double-click to configure and operate.
- `HUSTCampusAutologinCLI.exe`: command-line executable for advanced users and troubleshooting.

The installer is per-user and does not require administrator privileges. It installs to:

```text
%LOCALAPPDATA%\HUST Campus Autologin
```

After installation, open **HUST Campus Autologin** from the Start Menu. For the portable zip, extract it and double-click `HUSTCampusAutologin.exe`. Enter the username and password in the UI, save settings, then test login or install autostart.

For command-line usage, open PowerShell in the extracted directory and run:

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

`install-service` registers Windows Task Scheduler to run:

```text
HUSTCampusAutologin.exe watch
```

View logs:

```powershell
.\HUSTCampusAutologinCLI.exe logs --lines 80
```

Remove the background task:

```powershell
.\HUSTCampusAutologinCLI.exe uninstall-service
```

### Windows Source Usage

See [docs/windows-source.md](docs/windows-source.md).

```powershell
python -m pip install -e ".[test,notify]"
python -m campus_autologin gui
python -m campus_autologin init --username <student-id>
python -m campus_autologin set-credential --username <student-id>
python -m campus_autologin login
python -m campus_autologin install-service
```

For packaging instructions, see [docs/windows-package.md](docs/windows-package.md).

### Ubuntu / Linux Server Usage

See [docs/linux-systemd.md](docs/linux-systemd.md).

```bash
python3 -m pip install --user -e ".[linux]"
python3 -m campus_autologin init --username <student-id>
python3 -m campus_autologin set-credential --username <student-id>
python3 -m campus_autologin login
python3 -m campus_autologin install-service
```

Or run:

```bash
bash scripts/install-linux.sh
```

### Common Commands

```bash
python -m campus_autologin doctor
python -m campus_autologin init --username <student-id> --interval 30
python -m campus_autologin set-credential --username <student-id>
python -m campus_autologin login
python -m campus_autologin watch
python -m campus_autologin logs --lines 80
python -m campus_autologin install-service
python -m campus_autologin service-status
python -m campus_autologin uninstall-service
```

### Manual Portal URL

If automatic portal discovery fails, copy the full portal URL from your browser and save it:

```bash
python -m campus_autologin init --username <student-id> --manual-login-url "http://172.18.18.61:8080/eportal/index.jsp?..."
```

This URL may contain device, access point, internal IP, and session information. Do not publish it in issues, screenshots, or documentation.

### Security Notes

- Passwords are never written to config files or logs.
- Windows uses Windows Credential Manager by default.
- Linux source installs use a local `secrets.toml` file with `0600` permissions.
- This tool only automates the same campus authentication request that you can submit manually in the browser.
- It does not bypass school network policy. Wrong credentials, restricted accounts, billing issues, offline hours, or unavailable campus auth services still need to be handled normally.

### Troubleshooting

See [docs/troubleshooting.md](docs/troubleshooting.md).

## License

MIT
