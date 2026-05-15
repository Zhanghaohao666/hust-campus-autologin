# Ubuntu / Linux Server Usage

Linux 版适合宿舍服务器、软路由旁路机、迷你主机等需要长期挂校园网业务的环境。

## Requirements

- Python 3.11+
- `systemd --user`
- 机器已经通过 Wi-Fi、有线或上级路由接入校园网

程序不会创建 Wi-Fi 或拨号连接，只处理校园网 eportal 认证步骤。

## Quick Start

```bash
python3 -m pip install --user -e ".[linux]"
python3 -m campus_autologin init --username <student-id> --interval 30
python3 -m campus_autologin set-credential --username <student-id>
python3 -m campus_autologin login
python3 -m campus_autologin install-service
```

也可以在项目目录运行：

```bash
bash scripts/install-linux.sh
```

## Service Commands

```bash
python3 -m campus_autologin service-status
python3 -m campus_autologin logs --lines 80
python3 -m campus_autologin uninstall-service
```

对应的 systemd 命令：

```bash
systemctl --user status hust-campus-autologin.service
systemctl --user restart hust-campus-autologin.service
systemctl --user stop hust-campus-autologin.service
```

## File Locations

默认路径遵循 XDG 目录：

```text
配置：~/.config/hust-campus-autologin/config.toml
日志：~/.local/share/hust-campus-autologin/logs/watch.log
本地凭据：~/.local/share/hust-campus-autologin/secrets.toml
服务：~/.config/systemd/user/hust-campus-autologin.service
```

Linux 源码版默认使用本地 `secrets.toml` 保存密码，并在非 Windows 系统上设置为 `0600` 权限。

## Manual Portal URL

如果服务器没有桌面浏览器，建议先在同一网络下的浏览器复制完整认证页地址，再写入配置：

```bash
python3 -m campus_autologin init --username <student-id> --manual-login-url "http://172.18.18.61:8080/eportal/index.jsp?..."
```

如果校园网给服务器或路由器分配了新的内网 IP，这个 URL 可能需要重新获取。
