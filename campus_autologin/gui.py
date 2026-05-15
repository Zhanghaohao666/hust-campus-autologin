from __future__ import annotations

import os
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText
from typing import Callable, TypeVar

from campus_autologin.config import AppConfig, load_config
from campus_autologin.credentials import CredentialError, read_password_auto
from campus_autologin.gui_support import (
    GuiSettings,
    UiOperationResult,
    get_service_status,
    install_autostart,
    save_gui_settings,
    settings_from_config,
    start_autologin,
    stop_autologin,
    tail_watch_log,
    uninstall_autostart,
)
from campus_autologin.logging_setup import setup_logging


T = TypeVar("T")


class Palette:
    primary = "#533afd"
    primary_deep = "#4434d4"
    primary_press = "#2e2b8c"
    brand_dark = "#1c1e54"
    ink = "#0d253d"
    ink_secondary = "#273951"
    ink_mute = "#64748d"
    canvas = "#ffffff"
    canvas_soft = "#f6f9fc"
    hairline = "#e3e8ee"
    input_line = "#a8c3de"
    ruby = "#ea2261"
    success = "#1a7f64"
    warning = "#9b6829"
    on_primary = "#ffffff"


class CampusAutologinApp:
    def __init__(self, root: tk.Tk, config_path: str | None = None):
        self.root = root
        self.config_path = config_path
        self.config = load_config(config_path)
        self.pages: dict[str, tk.Frame] = {}
        self.nav_buttons: dict[str, tk.Button] = {}

        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.interval_var = tk.StringVar()
        self.manual_url_var = tk.StringVar()
        self.notifications_var = tk.BooleanVar()
        self.notify_success_var = tk.BooleanVar()

        self.root.title("HUST Campus Autologin")
        self.root.geometry("1080x720")
        self.root.minsize(940, 620)
        self.root.configure(bg=Palette.canvas_soft)

        self._configure_fonts()
        self._build_shell()
        self._load_settings_into_form()
        self.show_page("overview")
        self.refresh_overview()
        self.refresh_logs()

    def _configure_fonts(self) -> None:
        self.font_title = ("Inter", 24, "normal")
        self.font_heading = ("Inter", 16, "normal")
        self.font_body = ("Inter", 11, "normal")
        self.font_caption = ("Consolas", 10, "normal")
        self.font_button = ("Inter", 10, "normal")

    def _build_shell(self) -> None:
        self.shell = tk.Frame(self.root, bg=Palette.canvas_soft)
        self.shell.pack(fill="both", expand=True)
        self.shell.grid_columnconfigure(1, weight=1)
        self.shell.grid_rowconfigure(0, weight=1)

        self.sidebar = tk.Frame(self.shell, bg=Palette.brand_dark, width=232)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)

        self.main = tk.Frame(self.shell, bg=Palette.canvas_soft)
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_rowconfigure(1, weight=1)
        self.main.grid_columnconfigure(0, weight=1)

        self._build_sidebar()
        self._build_header()
        self._build_pages()

    def _build_sidebar(self) -> None:
        brand = tk.Frame(self.sidebar, bg=Palette.brand_dark)
        brand.pack(fill="x", padx=22, pady=(26, 18))
        tk.Label(
            brand,
            text="HUST",
            fg=Palette.on_primary,
            bg=Palette.brand_dark,
            font=("Inter", 22, "normal"),
        ).pack(anchor="w")
        tk.Label(
            brand,
            text="Campus Autologin",
            fg="#b9b9f9",
            bg=Palette.brand_dark,
            font=self.font_body,
        ).pack(anchor="w", pady=(2, 0))

        nav_items = [
            ("overview", "总览"),
            ("setup", "账号配置"),
            ("service", "自动重连"),
            ("logs", "运行日志"),
            ("diagnostics", "诊断"),
        ]
        nav = tk.Frame(self.sidebar, bg=Palette.brand_dark)
        nav.pack(fill="x", padx=14)
        for page, label in nav_items:
            btn = tk.Button(
                nav,
                text=label,
                anchor="w",
                command=lambda name=page: self.show_page(name),
                relief="flat",
                bd=0,
                padx=14,
                pady=10,
                font=self.font_button,
                cursor="hand2",
            )
            btn.pack(fill="x", pady=3)
            self.nav_buttons[page] = btn

        footer = tk.Frame(self.sidebar, bg=Palette.brand_dark)
        footer.pack(side="bottom", fill="x", padx=22, pady=22)
        tk.Label(
            footer,
            text="v0.2.0 UI Preview",
            fg="#b9b9f9",
            bg=Palette.brand_dark,
            font=("Consolas", 9, "normal"),
        ).pack(anchor="w")

    def _build_header(self) -> None:
        header = tk.Frame(self.main, bg=Palette.canvas_soft)
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 12))
        header.grid_columnconfigure(0, weight=1)

        self.page_title = tk.Label(
            header,
            text="总览",
            fg=Palette.ink,
            bg=Palette.canvas_soft,
            font=self.font_title,
        )
        self.page_title.grid(row=0, column=0, sticky="w")
        self.page_subtitle = tk.Label(
            header,
            text="查看配置、自动重连和最近日志",
            fg=Palette.ink_mute,
            bg=Palette.canvas_soft,
            font=self.font_body,
        )
        self.page_subtitle.grid(row=1, column=0, sticky="w", pady=(4, 0))

        self.status_pill = tk.Label(
            header,
            text="就绪",
            fg=Palette.on_primary,
            bg=Palette.primary,
            font=self.font_button,
            padx=14,
            pady=7,
        )
        self.status_pill.grid(row=0, column=1, rowspan=2, sticky="e")

    def _build_pages(self) -> None:
        self.page_host = tk.Frame(self.main, bg=Palette.canvas_soft)
        self.page_host.grid(row=1, column=0, sticky="nsew", padx=28, pady=(0, 28))
        self.page_host.grid_rowconfigure(0, weight=1)
        self.page_host.grid_columnconfigure(0, weight=1)

        builders = {
            "overview": self._build_overview_page,
            "setup": self._build_setup_page,
            "service": self._build_service_page,
            "logs": self._build_logs_page,
            "diagnostics": self._build_diagnostics_page,
        }
        for name, builder in builders.items():
            frame = tk.Frame(self.page_host, bg=Palette.canvas_soft)
            frame.grid(row=0, column=0, sticky="nsew")
            frame.grid_columnconfigure(0, weight=1)
            self.pages[name] = frame
            builder(frame)

    def _build_overview_page(self, parent: tk.Frame) -> None:
        grid = tk.Frame(parent, bg=Palette.canvas_soft)
        grid.pack(fill="x")
        for column in range(3):
            grid.grid_columnconfigure(column, weight=1)

        self.config_status = self._stat_card(grid, "账号配置", "读取中", 0, 0)
        self.credential_status = self._stat_card(grid, "密码凭据", "读取中", 0, 1)
        self.service_status = self._stat_card(grid, "自动重连", "读取中", 0, 2)

        actions = tk.Frame(parent, bg=Palette.canvas_soft)
        actions.pack(fill="x", pady=(22, 18))
        self._button(actions, "刷新状态", self.refresh_overview).pack(side="left")
        self._button(actions, "测试登录", self.test_login, primary=True).pack(
            side="left", padx=(10, 0)
        )
        self._button(actions, "打开配置目录", self.open_config_folder).pack(
            side="left", padx=(10, 0)
        )

        recent = self._panel(parent)
        recent.pack(fill="both", expand=True)
        tk.Label(
            recent,
            text="最近日志",
            bg=Palette.canvas,
            fg=Palette.ink,
            font=self.font_heading,
        ).pack(anchor="w", padx=20, pady=(18, 8))
        self.recent_log = ScrolledText(
            recent,
            height=10,
            wrap="word",
            bd=0,
            relief="flat",
            bg=Palette.canvas,
            fg=Palette.ink_secondary,
            font=self.font_caption,
        )
        self.recent_log.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self.recent_log.configure(state="disabled")

    def _build_setup_page(self, parent: tk.Frame) -> None:
        panel = self._panel(parent)
        panel.pack(fill="x")
        panel.grid_columnconfigure(1, weight=1)

        self._section_title(panel, "账号与认证", 0)
        self._field(panel, "校园网账号", self.username_var, 1)
        self._field(panel, "校园网密码", self.password_var, 2, show="*")
        self._field(panel, "手动认证页地址", self.manual_url_var, 3)

        tk.Label(
            panel,
            text="探测间隔",
            fg=Palette.ink_secondary,
            bg=Palette.canvas,
            font=self.font_body,
        ).grid(row=4, column=0, sticky="w", padx=20, pady=(10, 4))
        interval = tk.Spinbox(
            panel,
            from_=5,
            to=600,
            increment=5,
            textvariable=self.interval_var,
            width=12,
            bd=1,
            relief="solid",
            highlightthickness=1,
            highlightbackground=Palette.input_line,
            font=self.font_body,
        )
        interval.grid(row=4, column=1, sticky="w", padx=20, pady=(10, 4))

        checks = tk.Frame(panel, bg=Palette.canvas)
        checks.grid(row=5, column=0, columnspan=2, sticky="ew", padx=20, pady=(14, 4))
        tk.Checkbutton(
            checks,
            text="启用桌面通知",
            variable=self.notifications_var,
            bg=Palette.canvas,
            fg=Palette.ink,
            activebackground=Palette.canvas,
            selectcolor=Palette.canvas,
            font=self.font_body,
        ).pack(side="left")
        tk.Checkbutton(
            checks,
            text="登录成功时通知",
            variable=self.notify_success_var,
            bg=Palette.canvas,
            fg=Palette.ink,
            activebackground=Palette.canvas,
            selectcolor=Palette.canvas,
            font=self.font_body,
        ).pack(side="left", padx=(24, 0))

        helper = tk.Label(
            panel,
            text="密码留空时只更新配置，不改已保存密码。",
            fg=Palette.ink_mute,
            bg=Palette.canvas,
            font=("Inter", 9, "normal"),
        )
        helper.grid(row=6, column=0, columnspan=2, sticky="w", padx=20, pady=(4, 12))

        actions = tk.Frame(panel, bg=Palette.canvas)
        actions.grid(row=7, column=0, columnspan=2, sticky="w", padx=20, pady=(0, 20))
        self._button(actions, "保存配置", self.save_settings, primary=True).pack(
            side="left"
        )
        self._button(actions, "重新读取", self.reload_settings).pack(
            side="left", padx=(10, 0)
        )

    def _build_service_page(self, parent: tk.Frame) -> None:
        panel = self._panel(parent)
        panel.pack(fill="x")
        self._section_title(panel, "自动重连守护", 0)
        actions = tk.Frame(panel, bg=Palette.canvas)
        actions.grid(row=1, column=0, sticky="w", padx=20, pady=(4, 18))
        self._button(actions, "安装开机自启", self.install_service, primary=True).pack(
            side="left"
        )
        self._button(actions, "启动自动重连", self.start_service).pack(
            side="left", padx=(10, 0)
        )
        self._button(actions, "停止自动重连", self.stop_service).pack(
            side="left", padx=(10, 0)
        )
        self._button(actions, "取消开机自启", self.uninstall_service).pack(
            side="left", padx=(10, 0)
        )
        self._button(actions, "查询状态", self.query_service_status).pack(
            side="left", padx=(10, 0)
        )

        self.service_output = ScrolledText(
            panel,
            height=14,
            wrap="word",
            bd=0,
            relief="flat",
            bg=Palette.canvas,
            fg=Palette.ink_secondary,
            font=self.font_caption,
        )
        self.service_output.grid(
            row=2, column=0, sticky="nsew", padx=20, pady=(0, 20)
        )
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(2, weight=1)
        self._write_text(self.service_output, "等待操作。")

    def _build_logs_page(self, parent: tk.Frame) -> None:
        actions = tk.Frame(parent, bg=Palette.canvas_soft)
        actions.pack(fill="x", pady=(0, 12))
        self._button(actions, "刷新日志", self.refresh_logs, primary=True).pack(
            side="left"
        )
        self._button(actions, "打开日志目录", self.open_log_folder).pack(
            side="left", padx=(10, 0)
        )

        panel = self._panel(parent)
        panel.pack(fill="both", expand=True)
        self.logs_text = ScrolledText(
            panel,
            wrap="word",
            bd=0,
            relief="flat",
            bg=Palette.canvas,
            fg=Palette.ink_secondary,
            font=self.font_caption,
        )
        self.logs_text.pack(fill="both", expand=True, padx=20, pady=20)
        self.logs_text.configure(state="disabled")

    def _build_diagnostics_page(self, parent: tk.Frame) -> None:
        actions = tk.Frame(parent, bg=Palette.canvas_soft)
        actions.pack(fill="x", pady=(0, 12))
        self._button(actions, "运行诊断", self.run_diagnostics, primary=True).pack(
            side="left"
        )

        panel = self._panel(parent)
        panel.pack(fill="both", expand=True)
        self.diagnostics_text = ScrolledText(
            panel,
            wrap="word",
            bd=0,
            relief="flat",
            bg=Palette.canvas,
            fg=Palette.ink_secondary,
            font=self.font_caption,
        )
        self.diagnostics_text.pack(fill="both", expand=True, padx=20, pady=20)
        self.diagnostics_text.configure(state="disabled")
        self._write_text(self.diagnostics_text, "点击“运行诊断”查看当前配置和系统状态。")

    def _stat_card(
        self, parent: tk.Frame, label: str, value: str, row: int, column: int
    ) -> tk.Label:
        card = self._panel(parent)
        card.grid(row=row, column=column, sticky="ew", padx=(0 if column == 0 else 12, 0))
        tk.Label(
            card,
            text=label,
            bg=Palette.canvas,
            fg=Palette.ink_mute,
            font=self.font_body,
        ).pack(anchor="w", padx=18, pady=(16, 5))
        value_label = tk.Label(
            card,
            text=value,
            bg=Palette.canvas,
            fg=Palette.ink,
            font=("Consolas", 15, "normal"),
        )
        value_label.pack(anchor="w", padx=18, pady=(0, 18))
        return value_label

    def _panel(self, parent: tk.Widget) -> tk.Frame:
        return tk.Frame(
            parent,
            bg=Palette.canvas,
            highlightbackground=Palette.hairline,
            highlightthickness=1,
            bd=0,
        )

    def _section_title(self, parent: tk.Frame, text: str, row: int) -> None:
        tk.Label(
            parent,
            text=text,
            bg=Palette.canvas,
            fg=Palette.ink,
            font=self.font_heading,
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=20, pady=(18, 10))

    def _field(
        self,
        parent: tk.Frame,
        label: str,
        variable: tk.StringVar,
        row: int,
        show: str | None = None,
    ) -> tk.Entry:
        tk.Label(
            parent,
            text=label,
            fg=Palette.ink_secondary,
            bg=Palette.canvas,
            font=self.font_body,
        ).grid(row=row, column=0, sticky="w", padx=20, pady=(8, 4))
        entry = tk.Entry(
            parent,
            textvariable=variable,
            show=show or "",
            bd=1,
            relief="solid",
            highlightthickness=1,
            highlightbackground=Palette.input_line,
            highlightcolor=Palette.primary,
            fg=Palette.ink,
            bg=Palette.canvas,
            font=self.font_body,
        )
        entry.grid(row=row, column=1, sticky="ew", padx=20, pady=(8, 4), ipady=6)
        return entry

    def _button(
        self,
        parent: tk.Widget,
        text: str,
        command: Callable[[], None],
        *,
        primary: bool = False,
    ) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=Palette.primary if primary else Palette.canvas,
            fg=Palette.on_primary if primary else Palette.primary,
            activebackground=Palette.primary_press if primary else Palette.canvas_soft,
            activeforeground=Palette.on_primary if primary else Palette.primary_deep,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=Palette.primary,
            padx=16,
            pady=8,
            font=self.font_button,
            cursor="hand2",
        )

    def show_page(self, name: str) -> None:
        titles = {
            "overview": ("总览", "查看配置、自动重连和最近日志"),
            "setup": ("账号配置", "保存账号、密码、探测间隔和认证页地址"),
            "service": ("自动重连", "管理开机自启和当前守护任务"),
            "logs": ("运行日志", "查看 watch.log 最近输出"),
            "diagnostics": ("诊断", "检查配置、凭据、代理和计划任务"),
        }
        title, subtitle = titles[name]
        self.page_title.configure(text=title)
        self.page_subtitle.configure(text=subtitle)
        self.pages[name].tkraise()
        for page, button in self.nav_buttons.items():
            active = page == name
            button.configure(
                bg=Palette.primary if active else Palette.brand_dark,
                fg=Palette.on_primary if active else "#d7dbff",
                activebackground=Palette.primary_deep,
                activeforeground=Palette.on_primary,
            )

    def _load_settings_into_form(self) -> None:
        settings = settings_from_config(self.config)
        self.username_var.set(settings.username)
        self.password_var.set("")
        self.interval_var.set(str(settings.interval_seconds))
        self.manual_url_var.set(settings.manual_login_url)
        self.notifications_var.set(settings.notifications_enabled)
        self.notify_success_var.set(settings.notify_login_success)

    def reload_settings(self) -> None:
        self.config = load_config(self.config_path)
        self._load_settings_into_form()
        self.set_status("配置已重新读取", "ok")

    def save_settings(self) -> None:
        try:
            interval = int(self.interval_var.get().strip())
        except ValueError:
            self.set_status("探测间隔必须是数字", "error")
            messagebox.showerror("保存失败", "探测间隔必须是数字。")
            return

        settings = GuiSettings(
            username=self.username_var.get(),
            password=self.password_var.get(),
            interval_seconds=interval,
            manual_login_url=self.manual_url_var.get(),
            notifications_enabled=self.notifications_var.get(),
            notify_login_success=self.notify_success_var.get(),
        )

        def worker() -> UiOperationResult:
            return save_gui_settings(settings, config_path=self.config_path)

        def done(result: UiOperationResult) -> None:
            self.set_status(result.message, "ok" if result.ok else "error")
            if result.ok:
                self.config = load_config(self.config_path)
                self.password_var.set("")
                self.refresh_overview()
            else:
                messagebox.showerror("保存失败", result.message)

        self.run_background("正在保存配置", worker, done)

    def refresh_overview(self) -> None:
        self.config = load_config(self.config_path)
        self.config_status.configure(
            text="已填写" if self.config.account.username else "未填写",
            fg=Palette.success if self.config.account.username else Palette.warning,
        )
        try:
            read_password_auto(self.config.account.credential_target)
            credential_text = "已保存"
            credential_color = Palette.success
        except CredentialError:
            credential_text = "未保存"
            credential_color = Palette.warning
        self.credential_status.configure(text=credential_text, fg=credential_color)

        def worker() -> UiOperationResult:
            return get_service_status()

        def done(result: UiOperationResult) -> None:
            self.service_status.configure(
                text=_compact_status(result.message),
                fg=Palette.success if result.ok else Palette.warning,
            )
            self.refresh_recent_log()

        self.run_background("正在刷新状态", worker, done, quiet=True)

    def refresh_recent_log(self) -> None:
        lines = tail_watch_log(self.config, lines=20)
        self._write_text(self.recent_log, "\n".join(lines) if lines else "暂无日志。")

    def refresh_logs(self) -> None:
        self.config = load_config(self.config_path)
        lines = tail_watch_log(self.config, lines=300)
        self._write_text(self.logs_text, "\n".join(lines) if lines else "暂无日志。")
        self.set_status("日志已刷新", "ok")

    def test_login(self) -> None:
        def worker():
            from campus_autologin.__main__ import run_login

            config = load_config(self.config_path)
            logger = setup_logging(config.log_dir, config.logging.level)
            return run_login(config, logger=logger)

        def done(result) -> None:
            message = ("登录成功: " if result.success else "登录失败: ") + result.message
            self.set_status(message, "ok" if result.success else "error")
            if not result.success:
                messagebox.showwarning("测试登录失败", result.message)
            self.refresh_logs()
            self.refresh_overview()

        self.run_background("正在测试登录", worker, done)

    def install_service(self) -> None:
        self._service_action("正在安装开机自启", install_autostart)

    def uninstall_service(self) -> None:
        self._service_action("正在取消开机自启", uninstall_autostart)

    def start_service(self) -> None:
        self._service_action("正在启动自动重连", start_autologin)

    def stop_service(self) -> None:
        self._service_action("正在停止自动重连", stop_autologin)

    def query_service_status(self) -> None:
        self._service_action("正在查询自动重连状态", get_service_status)

    def _service_action(
        self, busy_message: str, action: Callable[[], UiOperationResult]
    ) -> None:
        def done(result: UiOperationResult) -> None:
            self.set_status(result.message, "ok" if result.ok else "error")
            self._write_text(self.service_output, result.message)
            self.refresh_overview()

        self.run_background(busy_message, action, done)

    def run_diagnostics(self) -> None:
        def worker() -> str:
            config = load_config(self.config_path)
            lines = [
                f"Config: {config.config_path}",
                f"Log dir: {config.log_dir}",
                f"Username: {'已填写' if config.account.username else '未填写'}",
                f"Credential target: {config.account.credential_target}",
                f"Interval: {config.watch.interval_seconds}s",
                f"Portal bases: {', '.join(config.portal.base_urls)}",
                f"Manual portal URL: {config.portal.manual_login_url or '(empty)'}",
                f"Notifications: {'enabled' if config.notification.enabled else 'disabled'}",
            ]
            try:
                read_password_auto(config.account.credential_target)
                lines.append("Credential: present")
            except CredentialError:
                lines.append("Credential: missing")
            service = get_service_status()
            lines.append(f"Scheduled task: {service.message}")
            proxy = _read_windows_proxy()
            if proxy:
                lines.append("Windows proxy:")
                lines.append(proxy)
            return "\n".join(lines)

        def done(text: str) -> None:
            self._write_text(self.diagnostics_text, text)
            self.set_status("诊断完成", "ok")

        self.run_background("正在运行诊断", worker, done)

    def open_config_folder(self) -> None:
        self.config = load_config(self.config_path)
        _open_folder(self.config.base_dir)

    def open_log_folder(self) -> None:
        self.config = load_config(self.config_path)
        self.config.log_dir.mkdir(parents=True, exist_ok=True)
        _open_folder(self.config.log_dir)

    def run_background(
        self,
        busy_message: str,
        worker: Callable[[], T],
        done: Callable[[T], None],
        *,
        quiet: bool = False,
    ) -> None:
        if not quiet:
            self.set_status(busy_message, "busy")

        def target() -> None:
            try:
                result = worker()
            except Exception as exc:  # UI boundary: surface unexpected backend errors.
                self.root.after(0, lambda: self._handle_background_error(exc))
                return
            self.root.after(0, lambda: done(result))

        thread = threading.Thread(target=target, daemon=True)
        thread.start()

    def _handle_background_error(self, exc: Exception) -> None:
        message = str(exc) or exc.__class__.__name__
        self.set_status(message, "error")
        messagebox.showerror("操作失败", message)

    def set_status(self, message: str, tone: str = "ok") -> None:
        colors = {
            "ok": Palette.success,
            "busy": Palette.primary,
            "error": Palette.ruby,
        }
        self.status_pill.configure(text=message[:42], bg=colors.get(tone, Palette.primary))

    def _write_text(self, widget: ScrolledText, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")


def _compact_status(message: str) -> str:
    if "State" in message:
        for line in message.splitlines():
            if "State" in line:
                return line.split(":", 1)[-1].strip() or "已安装"
    if "失败" in message:
        return "未安装"
    return "已安装"


def _open_folder(path) -> None:
    os.makedirs(path, exist_ok=True)
    if os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
        return
    subprocess.Popen(["xdg-open", str(path)])


def _read_windows_proxy() -> str:
    if os.name != "nt":
        return ""
    try:
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                "Get-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings' | Select-Object ProxyEnable,ProxyServer | Format-List",
            ],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def launch_gui(config_path: str | None = None) -> int:
    root = tk.Tk()
    CampusAutologinApp(root, config_path=config_path)
    root.mainloop()
    return 0
