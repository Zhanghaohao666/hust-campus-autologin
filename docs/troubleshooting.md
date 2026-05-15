# Troubleshooting

## 登录密码必须加密

当前华科 eportal 会先通过 `pageInfo` 返回是否需要加密、RSA 指数和模数。程序会按页面脚本流程生成 `password + ">" + mac`，反转后用门户 RSA 公钥加密，再提交 `passwordEncrypt=true`。

如果日志里仍然出现这个错误，请更新到最新代码后重新运行：

```bash
python -m campus_autologin login
```

## 用户不存在或者密码错误

先重写本机保存的凭据：

```bash
python -m campus_autologin set-credential --username <student-id>
python -m campus_autologin login
```

确认账号可以在浏览器认证页手动登录。若账号被挤占、欠费或不在可上网时段，程序不会绕过学校的认证规则。

## 开着 Clash 时打不开认证页

程序自己的探测和登录请求会直连，显式绕过系统代理和环境代理。它不会关闭 Clash Verge，也不会修改 Windows 系统代理。

如果浏览器被代理影响打不开认证页，可以让程序通过 `watch` 自动发现；自动发现失败时再使用手动门户 URL。

## Manual Portal URL

打开浏览器弹出的完整 `eportal/index.jsp?...` URL，然后写入配置：

```bash
python -m campus_autologin init --username <student-id> --manual-login-url "<copied-url>"
```

这个 URL 可能包含当前设备、接入点和内网 IP 信息。不要把自己的完整 URL 发到公开 issue、README 或截图里。

## Not On Campus Network

程序会先检查网络环境提示，避免在家庭网络下反复请求 `172.18.18.60/61`。如果你确定机器在校园网内，但日志一直显示不在校园网，可以检查：

```bash
python -m campus_autologin doctor
```

有线、路由器桥接、服务器环境可能缺少明显的 SSID 信息。此时可以配置 `manual_login_url` 作为 fallback。

## 看日志

```bash
python -m campus_autologin logs --lines 80
```

常见成功日志：

```text
campus login success
campus network online
```
