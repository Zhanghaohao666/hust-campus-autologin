# Windows Source Usage

Windows 源码版适合先验证流程、二次开发，或者在打包版发布前自己运行。

## Requirements

- Python 3.11+
- 已连接校园网 Wi-Fi 或有线网
- 能在浏览器认证页正常登录的校园网账号

## Quick Start

```powershell
python -m pip install -e ".[test,notify]"
python -m campus_autologin gui
python -m campus_autologin init --username <student-id>
python -m campus_autologin set-credential --username <student-id>
python -m campus_autologin login
python -m campus_autologin install-service
python -m campus_autologin start-service
python -m campus_autologin stop-service
python -m campus_autologin restart-service
```

`install-service` 在 Windows 上会注册任务计划程序，等价于旧命令 `install-task`。

如果想用桌面 UI，不需要手动编辑配置文件，直接运行：

```powershell
python -m campus_autologin gui
```

## Manual Portal URL

如果自动发现认证页失败，可以先打开浏览器弹出的完整 `eportal/index.jsp?...` 地址，然后写入配置：

```powershell
python -m campus_autologin init --username <student-id> --manual-login-url "http://172.18.18.61:8080/eportal/index.jsp?..."
```

这个地址里的参数可能会过期。它只是自动发现失败时的 fallback，不建议公开粘贴到 issue 或截图里。

## Logs

```powershell
python -m campus_autologin logs --lines 80
python -m campus_autologin doctor
```

默认日志位置：

```text
%USERPROFILE%\.campus-autologin\logs\watch.log
```

## Uninstall

```powershell
python -m campus_autologin uninstall-service
```

旧命令仍然保留：

```powershell
python -m campus_autologin uninstall-task
```
