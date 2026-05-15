# HUST Campus Autologin

华中科技大学校园网 eportal 自动重联工具。它会在网络掉到认证态时自动发现认证页并提交登录请求，适合 Windows 日常电脑和 Ubuntu/Linux 服务器长时间运行。

## Features

- 自动探测 captive portal 并重新登录校园网。
- 支持当前 HUST eportal 的加密密码登录流程。
- 程序自己的 HTTP 请求直连，绕过系统代理、环境代理和 Clash Verge。
- 支持 Windows 任务计划程序和 Linux systemd user service。
- 密码不写入配置文件和日志。
- 支持手动配置完整 `eportal/index.jsp?...` URL 作为自动发现失败时的 fallback。

## Quick Start

### Windows

源码运行见 [docs/windows-source.md](docs/windows-source.md)。Windows portable exe 和 NSIS 安装包构建见 [docs/windows-package.md](docs/windows-package.md)。

```powershell
python -m pip install -e ".[test,notify]"
python -m campus_autologin init --username <student-id>
python -m campus_autologin set-credential --username <student-id>
python -m campus_autologin login
python -m campus_autologin install-service
```

### Ubuntu / Linux Server

见 [docs/linux-systemd.md](docs/linux-systemd.md)。

```bash
python3 -m pip install --user -e ".[linux]"
python3 -m campus_autologin init --username <student-id>
python3 -m campus_autologin set-credential --username <student-id>
python3 -m campus_autologin login
python3 -m campus_autologin install-service
```

## Common Commands

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

旧版 Windows 命令 `install-task` 和 `uninstall-task` 仍然保留。

## Manual Portal URL

如果自动发现认证页失败，可以复制浏览器弹出的完整认证页地址：

```bash
python -m campus_autologin init --username <student-id> --manual-login-url "http://172.18.18.61:8080/eportal/index.jsp?..."
```

这个 URL 可能含有当前设备和会话信息，不要公开粘贴。

## Security

Windows 默认使用 Windows Credential Manager 保存密码。Linux 源码版默认使用本地 `secrets.toml`，并在非 Windows 系统上设置为 `0600` 权限。

配置文件和日志不会写入密码。公开 issue、截图和配置示例时，也不要包含自己的完整手动门户 URL。

## Troubleshooting

见 [docs/troubleshooting.md](docs/troubleshooting.md)。

## License

MIT
