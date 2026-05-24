from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText
from typing import Callable, TypeVar

from campus_autologin import __version__
from campus_autologin.config import AppConfig, load_config
from campus_autologin.credentials import CredentialError, read_password_auto
from campus_autologin.gui_support import (
    ConnectionStatus,
    GuiSettings,
    UiOperationResult,
    get_service_status,
    install_autostart,
    probe_connection_status,
    read_windows_proxy,
    restart_autologin,
    save_gui_settings,
    settings_from_config,
    start_autologin,
    stop_autologin,
    tail_watch_log,
    uninstall_autostart,
)
from campus_autologin.logging_setup import setup_logging


T = TypeVar("T")

MANUAL_LOGIN_URL_HINT = "可留空，此项仅提供探测候选参考。"


# ── Design Tokens (xAI Inspired) ─────────────────────────────────────────────


class Palette:
    canvas = "#0a0a0a"
    canvas_soft = "#1a1c20"
    canvas_card = "#191919"
    canvas_mid = "#363a3f"
    hairline = "#212327"
    ink = "#ffffff"
    ink_hover = "#fafaf7"
    body = "#dadbdf"
    body_mid = "#7d8187"
    mute = "#7d8187"
    primary = "#ffffff"
    on_primary = "#0a0a0a"
    accent_sunset = "#ff7a17"
    accent_sunset_soft = "#ffc285"
    accent_dusk = "#7c3aed"
    accent_twilight = "#c4b5fd"
    accent_breeze = "#a0c3ec"
    accent_midnight = "#0d1726"
    accent_ruby = "#ef4444"
    accent_success = "#22c55e"


class Fonts:
    _sans: str | None = None
    _mono: str | None = None

    @classmethod
    def _resolve(cls, candidates: tuple[str, ...], fallback: str) -> str:
        root = tk.Tk()
        root.withdraw()
        families = root.tk.call("font", "families")
        root.destroy()
        for candidate in candidates:
            if candidate in families:
                return candidate
        return fallback

    @classmethod
    def sans_family(cls) -> str:
        if cls._sans is None:
            cls._sans = cls._resolve(
                ("Noto Sans SC", "Source Han Sans SC", "Inter", "Microsoft YaHei UI", "Microsoft YaHei"),
                "Microsoft YaHei",
            )
        return cls._sans

    @classmethod
    def mono_family(cls) -> str:
        if cls._mono is None:
            cls._mono = cls._resolve(
                ("Cascadia Mono", "JetBrains Mono", "Consolas", "Courier New"),
                "Consolas",
            )
        return cls._mono

    @classmethod
    def title(cls) -> tuple[str, int, str]:
        return (cls.sans_family(), 22, "bold")

    @classmethod
    def heading(cls) -> tuple[str, int]:
        return (cls.sans_family(), 16)

    @classmethod
    def body(cls) -> tuple[str, int]:
        return (cls.sans_family(), 13)

    @classmethod
    def body_sm(cls) -> tuple[str, int]:
        return (cls.sans_family(), 12)

    @classmethod
    def caption(cls) -> tuple[str, int]:
        return (cls.sans_family(), 11)

    @classmethod
    def mono(cls) -> tuple[str, int]:
        return (cls.mono_family(), 12)

    @classmethod
    def mono_sm(cls) -> tuple[str, int]:
        return (cls.mono_family(), 11)

    @classmethod
    def mono_label(cls) -> tuple[str, int, str]:
        return (cls.mono_family(), 11, "bold")

    @classmethod
    def button(cls) -> tuple[str, int]:
        return (cls.sans_family(), 13)

    @classmethod
    def button_sm(cls) -> tuple[str, int]:
        return (cls.sans_family(), 12)


# ── Drawing Helpers ───────────────────────────────────────────────────────────


def _rounded_rect(
    canvas: tk.Canvas, x1: int, y1: int, x2: int, y2: int, radius: int, **kwargs
) -> int:
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


def _pill_shape(
    canvas: tk.Canvas, x1: int, y1: int, x2: int, y2: int, **kwargs
) -> int:
    r = (y2 - y1) // 2
    return _rounded_rect(canvas, x1, y1, x2, y2, r, **kwargs)


# ── Custom Widgets ────────────────────────────────────────────────────────────


class RoundedCard(tk.Canvas):
    def __init__(self, parent: tk.Widget, **kwargs):
        bg = kwargs.pop("bg", Palette.canvas_card)
        border = kwargs.pop("bordercolor", Palette.hairline)
        radius = kwargs.pop("radius", 8)
        super().__init__(parent, highlightthickness=0, bd=0, bg=Palette.canvas)
        self._bg = bg
        self._border = border
        self._radius = radius
        self._inner = tk.Frame(self, bg=bg)
        self._win = self.create_window(0, 0, window=self._inner, anchor="nw", tags="inner")
        self.bind("<Configure>", self._on_resize)
        self._inner.bind("<Configure>", self._on_inner_resize)

    def _on_inner_resize(self, event):
        self.configure(height=event.height + 2)

    def _on_resize(self, event):
        w, h = event.width, event.height
        self.delete("bg")
        _rounded_rect(
            self, 1, 1, w - 1, h - 1, self._radius,
            fill=self._bg, outline=self._border, width=1, tags="bg",
        )
        self.tag_lower("bg")
        self.itemconfigure(self._win, width=w - 2)

    @property
    def inner(self) -> tk.Frame:
        return self._inner


class PillButton(tk.Canvas):
    def __init__(
        self,
        parent: tk.Widget,
        text: str,
        command: Callable[[], None],
        *,
        primary: bool = False,
        small: bool = False,
        **kwargs,
    ):
        self._bg_color = Palette.canvas
        super().__init__(
            parent,
            highlightthickness=0,
            bd=0,
            bg=self._bg_color,
            cursor="hand2",
            **kwargs,
        )
        self._command = command
        self._primary = primary
        self._text = text
        self._small = small
        self._fg = Palette.on_primary if primary else Palette.ink
        self._fill = Palette.primary if primary else Palette.canvas
        self._border = Palette.primary if primary else Palette.hairline
        self._hover_fill = Palette.canvas_mid if not primary else Palette.body
        self._pressed = False

        font = Fonts.button_sm() if small else Fonts.button()
        pad_x = 12 if small else 16
        pad_y = 4 if small else 6

        self._label = self.create_text(0, 0, text=text, fill=self._fg, font=font, tags="label")
        bbox = self.bbox(self._label)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        w = tw + pad_x * 2
        h = th + pad_y * 2
        self.configure(width=w, height=h)
        self.coords(self._label, w // 2, h // 2)

        self.bind("<Configure>", self._draw)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _draw(self, event=None):
        w = self.winfo_width()
        h = self.winfo_height()
        self.delete("bg")
        fill = self._hover_fill if self._pressed else self._fill
        _pill_shape(self, 1, 1, w - 1, h - 1, fill=fill, outline=self._border, width=1, tags="bg")
        self.tag_lower("bg")

    def _on_enter(self, e):
        self._pressed = True
        self._draw()

    def _on_leave(self, e):
        self._pressed = False
        self._draw()

    def _on_press(self, e):
        pass

    def _on_release(self, e):
        self._command()

    def set_text(self, text: str):
        self._text = text
        self.itemconfigure(self._label, text=text)


class StatusDot(tk.Canvas):
    """Animated status indicator dot."""

    def __init__(self, parent: tk.Widget, size: int = 10, **kwargs):
        super().__init__(parent, width=size, height=size, highlightthickness=0, bd=0, **kwargs)
        self._size = size
        self._color = Palette.mute
        self._pulse_phase = 0
        self._animating = False
        self._draw()

    def _draw(self):
        self.delete("all")
        s = self._size
        m = 1
        self.create_oval(m, m, s - m, s - m, fill=self._color, outline="")

    def set_color(self, color: str):
        self._color = color
        self._draw()

    def start_pulse(self, color: str):
        self._color = color
        self._animating = True
        self._pulse_phase = 0
        self._animate()

    def stop_pulse(self):
        self._animating = False

    def _animate(self):
        if not self._animating:
            return
        self._pulse_phase = (self._pulse_phase + 1) % 20
        import math
        alpha = 0.4 + 0.6 * abs(math.sin(self._pulse_phase * math.pi / 10))
        r, g, b = int(self._color[1:3], 16), int(self._color[3:5], 16), int(self._color[5:7], 16)
        r2 = int(r * alpha + 10 * (1 - alpha))
        g2 = int(g * alpha + 10 * (1 - alpha))
        b2 = int(b * alpha + 10 * (1 - alpha))
        blended = f"#{r2:02x}{g2:02x}{b2:02x}"
        self.delete("all")
        s = self._size
        self.create_oval(1, 1, s - 1, s - 1, fill=blended, outline="")
        self.after(80, self._animate)


# ── Mono Label (uppercase tracked style) ─────────────────────────────────────


class MonoLabel(tk.Label):
    def __init__(self, parent: tk.Widget, text: str, **kwargs):
        kwargs.setdefault("fg", Palette.mute)
        kwargs.setdefault("bg", Palette.canvas)
        kwargs.setdefault("font", Fonts.mono_label())
        super().__init__(parent, text=text.upper(), **kwargs)


# ── Main Application ─────────────────────────────────────────────────────────


class CampusAutologinApp:
    def __init__(self, root: tk.Tk, config_path: str | None = None):
        self.root = root
        self.config_path = config_path
        self.config = load_config(config_path)
        self.pages: dict[str, tk.Frame] = {}
        self.nav_items: list[tuple[str, str, str]] = [
            ("overview", "总览", "OVERVIEW"),
            ("setup", "账号配置", "ACCOUNT"),
            ("service", "自动重连", "SERVICE"),
            ("logs", "运行日志", "LOGS"),
            ("diagnostics", "诊断", "DIAGNOSTICS"),
        ]
        self._nav_buttons: dict[str, tk.Frame] = {}
        self._nav_indicators: dict[str, tk.Frame] = {}

        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.interval_var = tk.StringVar()
        self.manual_url_var = tk.StringVar()
        self.notifications_var = tk.BooleanVar()
        self.notify_success_var = tk.BooleanVar()

        self._auto_refresh_logs = True
        self._auto_refresh_status = True
        self._connection_dot: StatusDot | None = None
        self._connection_label: tk.Label | None = None

        self.root.title("HUST Campus Autologin")
        self.root.geometry("1100x740")
        self.root.minsize(960, 640)
        self.root.configure(bg=Palette.canvas)
        self.root.option_add("*Background", Palette.canvas)
        self.root.option_add("*Foreground", Palette.ink)

        self._build_shell()
        self._load_settings_into_form()
        self.show_page("overview")
        self.refresh_overview()
        self.refresh_logs()
        self._start_auto_refresh()

    # ── Shell Layout ──────────────────────────────────────────────────────

    def _build_shell(self):
        self.shell = tk.Frame(self.root, bg=Palette.canvas)
        self.shell.pack(fill="both", expand=True)
        self.shell.grid_columnconfigure(1, weight=1)
        self.shell.grid_rowconfigure(0, weight=1)

        self.sidebar = tk.Frame(self.shell, bg=Palette.canvas, width=220)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)

        self.main_area = tk.Frame(self.shell, bg=Palette.canvas)
        self.main_area.grid(row=0, column=1, sticky="nsew")
        self.main_area.grid_rowconfigure(1, weight=1)
        self.main_area.grid_columnconfigure(0, weight=1)

        self._build_sidebar()
        self._build_header()
        self._build_pages()

    def _build_sidebar(self):
        brand = tk.Frame(self.sidebar, bg=Palette.canvas)
        brand.pack(fill="x", padx=20, pady=(28, 24))
        tk.Label(
            brand, text="HUST", fg=Palette.ink, bg=Palette.canvas,
            font=Fonts.title(),
        ).pack(anchor="w")
        tk.Label(
            brand, text="Campus Autologin", fg=Palette.mute, bg=Palette.canvas,
            font=Fonts.caption(),
        ).pack(anchor="w", pady=(2, 0))

        tk.Frame(self.sidebar, bg=Palette.hairline, height=1).pack(fill="x", padx=20, pady=(0, 12))

        nav = tk.Frame(self.sidebar, bg=Palette.canvas)
        nav.pack(fill="x", padx=12)
        for page_id, label, mono_label in self.nav_items:
            row = tk.Frame(nav, bg=Palette.canvas, cursor="hand2")
            row.pack(fill="x", pady=2)

            indicator = tk.Frame(row, bg=Palette.canvas, width=3)
            indicator.pack(side="left", fill="y", padx=(0, 8))

            lbl = tk.Label(
                row, text=label, fg=Palette.body, bg=Palette.canvas,
                font=Fonts.body_sm(), anchor="w", padx=8, pady=8,
            )
            lbl.pack(side="left", fill="x", expand=True)

            for widget in (row, lbl):
                widget.bind("<Button-1>", lambda e, name=page_id: self.show_page(name))
                widget.bind("<Enter>", lambda e, r=row: r.configure(bg=Palette.canvas_soft))
                widget.bind("<Leave>", lambda e, r=row, p=page_id: r.configure(
                    bg=Palette.canvas_soft if self._current_page == p else Palette.canvas
                ))

            self._nav_buttons[page_id] = row
            self._nav_indicators[page_id] = indicator

        version_frame = tk.Frame(self.sidebar, bg=Palette.canvas)
        version_frame.pack(side="bottom", fill="x", padx=20, pady=20)
        tk.Label(
            version_frame, text=f"v{__version__}", fg=Palette.mute, bg=Palette.canvas,
            font=Fonts.mono_sm(),
        ).pack(anchor="w")

        self._current_page = "overview"

    def _build_header(self):
        header = tk.Frame(self.main_area, bg=Palette.canvas)
        header.grid(row=0, column=0, sticky="ew", padx=32, pady=(28, 16))
        header.grid_columnconfigure(0, weight=1)

        title_frame = tk.Frame(header, bg=Palette.canvas)
        title_frame.grid(row=0, column=0, sticky="w")

        self.page_title = tk.Label(
            title_frame, text="总览", fg=Palette.ink, bg=Palette.canvas,
            font=Fonts.title(),
        )
        self.page_title.pack(anchor="w")
        self.page_subtitle = tk.Label(
            title_frame, text="查看配置、自动重连和最近日志", fg=Palette.mute,
            bg=Palette.canvas, font=Fonts.body_sm(),
        )
        self.page_subtitle.pack(anchor="w", pady=(2, 0))

        status_frame = tk.Frame(header, bg=Palette.canvas)
        status_frame.grid(row=0, column=1, sticky="e")

        self._connection_dot = StatusDot(status_frame, size=10, bg=Palette.canvas)
        self._connection_dot.pack(side="left", padx=(0, 8))
        self._connection_label = tk.Label(
            status_frame, text="检测中...", fg=Palette.mute, bg=Palette.canvas,
            font=Fonts.body_sm(),
        )
        self._connection_label.pack(side="left")

        self.status_pill = tk.Label(
            header, text="就绪", fg=Palette.on_primary, bg=Palette.canvas_mid,
            font=Fonts.button_sm(), padx=12, pady=5,
        )
        self.status_pill.grid(row=0, column=2, sticky="e", padx=(16, 0))

    def _build_pages(self):
        self.page_host = tk.Frame(self.main_area, bg=Palette.canvas)
        self.page_host.grid(row=1, column=0, sticky="nsew", padx=32, pady=(0, 32))
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
            frame = tk.Frame(self.page_host, bg=Palette.canvas)
            frame.grid(row=0, column=0, sticky="nsew")
            frame.grid_columnconfigure(0, weight=1)
            self.pages[name] = frame
            builder(frame)

    # ── Pages ─────────────────────────────────────────────────────────────

    def _build_overview_page(self, parent: tk.Frame):
        cards_row = tk.Frame(parent, bg=Palette.canvas)
        cards_row.pack(fill="x", pady=(0, 16))
        for i in range(3):
            cards_row.grid_columnconfigure(i, weight=1)

        self.config_status = self._dark_stat_card(cards_row, "ACCOUNT", "读取中", 0, 0)
        self.credential_status = self._dark_stat_card(cards_row, "CREDENTIAL", "读取中", 0, 1)
        self.service_status = self._dark_stat_card(cards_row, "AUTO RECONNECT", "读取中", 0, 2)

        actions = tk.Frame(parent, bg=Palette.canvas)
        actions.pack(fill="x", pady=(0, 16))
        PillButton(actions, "刷新状态", self.refresh_overview, small=True).pack(side="left")
        PillButton(actions, "测试登录", self.test_login, primary=True, small=True).pack(side="left", padx=(8, 0))
        PillButton(actions, "停止服务", self.stop_service, small=True).pack(side="left", padx=(8, 0))
        PillButton(actions, "重启服务", self.restart_service, small=True).pack(side="left", padx=(8, 0))
        PillButton(actions, "打开配置目录", self.open_config_folder, small=True).pack(side="left", padx=(8, 0))

        log_card = RoundedCard(parent)
        log_card.pack(fill="both", expand=True)
        inner = log_card.inner
        inner.grid_columnconfigure(0, weight=1)
        inner.grid_rowconfigure(1, weight=1)

        MonoLabel(inner, "RECENT LOGS").grid(row=0, column=0, sticky="w", padx=20, pady=(16, 8))
        self.recent_log = self._dark_scrolled_text(inner, height=10)
        self.recent_log.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

    def _build_setup_page(self, parent: tk.Frame):
        card = RoundedCard(parent)
        card.pack(fill="x")
        inner = card.inner
        inner.grid_columnconfigure(1, weight=1)

        MonoLabel(inner, "ACCOUNT & AUTH").grid(row=0, column=0, columnspan=2, sticky="w", padx=24, pady=(20, 12))

        self._dark_field(inner, "校园网账号", self.username_var, 1)
        self._dark_field(inner, "校园网密码", self.password_var, 2, show="*")
        self._dark_field(inner, "手动认证页地址", self.manual_url_var, 3)

        tk.Label(
            inner, text=MANUAL_LOGIN_URL_HINT, fg=Palette.mute, bg=Palette.canvas_card,
            font=Fonts.caption(),
        ).grid(row=4, column=1, sticky="w", padx=24, pady=(0, 4))

        tk.Label(
            inner, text="探测间隔", fg=Palette.body, bg=Palette.canvas_card,
            font=Fonts.body(),
        ).grid(row=5, column=0, sticky="w", padx=24, pady=(12, 4))
        interval = tk.Spinbox(
            inner, from_=5, to=600, increment=5, textvariable=self.interval_var,
            width=12, bd=0, relief="flat", highlightthickness=1,
            highlightbackground=Palette.hairline, highlightcolor=Palette.ink,
            fg=Palette.ink, bg=Palette.canvas_soft, font=Fonts.body(),
            buttonbackground=Palette.canvas_mid, insertbackground=Palette.ink,
        )
        interval.grid(row=5, column=1, sticky="w", padx=24, pady=(12, 4))

        checks = tk.Frame(inner, bg=Palette.canvas_card)
        checks.grid(row=6, column=0, columnspan=2, sticky="ew", padx=24, pady=(12, 4))
        for var, text in [
            (self.notifications_var, "启用桌面通知"),
            (self.notify_success_var, "登录成功时通知"),
        ]:
            cb = tk.Checkbutton(
                checks, text=text, variable=var, bg=Palette.canvas_card,
                fg=Palette.body, activebackground=Palette.canvas_card,
                activeforeground=Palette.ink, selectcolor=Palette.canvas_mid,
                highlightthickness=0, font=Fonts.body(),
            )
            cb.pack(side="left", padx=(0, 20))

        tk.Label(
            inner, text="密码留空时只更新配置，不改已保存密码。",
            fg=Palette.mute, bg=Palette.canvas_card, font=Fonts.caption(),
        ).grid(row=7, column=0, columnspan=2, sticky="w", padx=24, pady=(4, 12))

        btn_row = tk.Frame(inner, bg=Palette.canvas_card)
        btn_row.grid(row=8, column=0, columnspan=2, sticky="w", padx=24, pady=(0, 24))
        PillButton(btn_row, "保存配置", self.save_settings, primary=True).pack(side="left")
        PillButton(btn_row, "按已保存配置重启服务", self.restart_service).pack(side="left", padx=(8, 0))

    def _build_service_page(self, parent: tk.Frame):
        card = RoundedCard(parent)
        card.pack(fill="x")
        inner = card.inner
        inner.grid_columnconfigure(0, weight=1)

        MonoLabel(inner, "AUTO RECONNECT DAEMON").grid(row=0, column=0, sticky="w", padx=24, pady=(20, 12))

        btn_row = tk.Frame(inner, bg=Palette.canvas_card)
        btn_row.grid(row=1, column=0, sticky="w", padx=24, pady=(0, 12))
        for text, cmd in [
            ("安装开机自启", self.install_service),
            ("启动自动重连", self.start_service),
            ("停止自动重连", self.stop_service),
            ("重启自动重连", self.restart_service),
            ("取消开机自启", self.uninstall_service),
            ("查询状态", self.query_service_status),
        ]:
            PillButton(btn_row, text, cmd, small=True).pack(side="left", padx=(0, 6))

        self.service_output = self._dark_scrolled_text(inner, height=14)
        self.service_output.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        inner.grid_rowconfigure(2, weight=1)
        self._write_text(self.service_output, "等待操作。")

    def _build_logs_page(self, parent: tk.Frame):
        actions = tk.Frame(parent, bg=Palette.canvas)
        actions.pack(fill="x", pady=(0, 12))
        PillButton(actions, "刷新日志", self.refresh_logs, primary=True, small=True).pack(side="left")
        PillButton(actions, "打开日志目录", self.open_log_folder, small=True).pack(side="left", padx=(8, 0))
        self._log_auto_btn = PillButton(
            actions, "自动刷新: 开", self._toggle_log_auto_refresh, small=True,
        )
        self._log_auto_btn.pack(side="left", padx=(8, 0))

        card = RoundedCard(parent)
        card.pack(fill="both", expand=True)
        inner = card.inner
        inner.grid_columnconfigure(0, weight=1)
        inner.grid_rowconfigure(0, weight=1)
        self.logs_text = self._dark_scrolled_text(inner)
        self.logs_text.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)

    def _build_diagnostics_page(self, parent: tk.Frame):
        actions = tk.Frame(parent, bg=Palette.canvas)
        actions.pack(fill="x", pady=(0, 12))
        PillButton(actions, "运行诊断", self.run_diagnostics, primary=True, small=True).pack(side="left")

        card = RoundedCard(parent)
        card.pack(fill="both", expand=True)
        inner = card.inner
        inner.grid_columnconfigure(0, weight=1)
        inner.grid_rowconfigure(0, weight=1)
        self.diagnostics_text = self._dark_scrolled_text(inner)
        self.diagnostics_text.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        self._write_text(self.diagnostics_text, "点击「运行诊断」查看当前配置和系统状态。")

    # ── Reusable dark widgets ─────────────────────────────────────────────

    def _dark_stat_card(self, parent: tk.Frame, label: str, value: str, row: int, col: int) -> tk.Label:
        card = RoundedCard(parent)
        card.grid(row=row, column=col, sticky="ew", padx=(0 if col == 0 else 8, 0), pady=4)
        inner = card.inner
        MonoLabel(inner, label).pack(anchor="w", padx=20, pady=(18, 4))
        value_lbl = tk.Label(
            inner, text=value, fg=Palette.ink, bg=Palette.canvas_card,
            font=(Fonts.sans_family(), 18, "bold"),
        )
        value_lbl.pack(anchor="w", padx=20, pady=(0, 18))
        return value_lbl

    def _dark_field(
        self, parent: tk.Frame, label: str, variable: tk.StringVar, row: int,
        show: str | None = None,
    ) -> tk.Entry:
        tk.Label(
            parent, text=label, fg=Palette.body, bg=Palette.canvas_card,
            font=Fonts.body(),
        ).grid(row=row, column=0, sticky="w", padx=24, pady=(10, 4))
        entry = tk.Entry(
            parent, textvariable=variable, show=show or "",
            bd=0, relief="flat", highlightthickness=1,
            highlightbackground=Palette.hairline, highlightcolor=Palette.ink,
            fg=Palette.ink, bg=Palette.canvas_soft, font=Fonts.body(),
            insertbackground=Palette.ink,
        )
        entry.grid(row=row, column=1, sticky="ew", padx=24, pady=(10, 4), ipady=8)
        return entry

    def _dark_scrolled_text(self, parent: tk.Widget, **kwargs) -> ScrolledText:
        kwargs.setdefault("wrap", "word")
        kwargs.setdefault("bd", 0)
        kwargs.setdefault("relief", "flat")
        kwargs.setdefault("bg", Palette.canvas_card)
        kwargs.setdefault("fg", Palette.body)
        kwargs.setdefault("font", Fonts.mono())
        kwargs.setdefault("insertbackground", Palette.ink)
        kwargs.setdefault("selectbackground", Palette.canvas_mid)
        kwargs.setdefault("selectforeground", Palette.ink)
        st = ScrolledText(parent, **kwargs)
        st.configure(state="disabled")
        return st

    # ── Page Navigation ───────────────────────────────────────────────────

    def show_page(self, name: str):
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
        self._current_page = name

        for page_id, _, _ in self.nav_items:
            active = page_id == name
            btn = self._nav_buttons[page_id]
            ind = self._nav_indicators[page_id]
            if active:
                btn.configure(bg=Palette.canvas_soft)
                ind.configure(bg=Palette.accent_sunset)
                for child in btn.winfo_children():
                    if isinstance(child, tk.Label):
                        child.configure(fg=Palette.ink, bg=Palette.canvas_soft)
            else:
                btn.configure(bg=Palette.canvas)
                ind.configure(bg=Palette.canvas)
                for child in btn.winfo_children():
                    if isinstance(child, tk.Label):
                        child.configure(fg=Palette.body, bg=Palette.canvas)

    # ── Data Operations ───────────────────────────────────────────────────

    def _load_settings_into_form(self):
        settings = settings_from_config(self.config)
        self.username_var.set(settings.username)
        self.password_var.set("")
        self.interval_var.set(str(settings.interval_seconds))
        self.manual_url_var.set(settings.manual_login_url)
        self.notifications_var.set(settings.notifications_enabled)
        self.notify_success_var.set(settings.notify_login_success)

    def save_settings(self):
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

        def worker():
            return save_gui_settings(settings, config_path=self.config_path)

        def done(result: UiOperationResult):
            self.set_status(result.message, "ok" if result.ok else "error")
            if result.ok:
                self.config = load_config(self.config_path)
                self.password_var.set("")
                self.refresh_overview()
            else:
                messagebox.showerror("保存失败", result.message)

        self.run_background("正在保存配置", worker, done)

    def refresh_overview(self):
        self.config = load_config(self.config_path)
        self.config_status.configure(
            text="已填写" if self.config.account.username else "未填写",
            fg=Palette.accent_success if self.config.account.username else Palette.accent_sunset,
        )
        try:
            read_password_auto(self.config.account.credential_target)
            self.credential_status.configure(text="已保存", fg=Palette.accent_success)
        except CredentialError:
            self.credential_status.configure(text="未保存", fg=Palette.accent_sunset)

        def worker():
            return get_service_status()

        def done(result: UiOperationResult):
            self.service_status.configure(
                text=_compact_status(result.message),
                fg=Palette.accent_success if result.ok else Palette.accent_sunset,
            )
            self.refresh_recent_log()

        self.run_background("正在刷新状态", worker, done, quiet=True)

    def refresh_recent_log(self):
        lines = tail_watch_log(self.config, lines=20)
        self._write_log_text(self.recent_log, "\n".join(lines) if lines else "暂无日志。")

    def refresh_logs(self):
        self.config = load_config(self.config_path)
        lines = tail_watch_log(self.config, lines=300)
        self._write_log_text(self.logs_text, "\n".join(lines) if lines else "暂无日志。")
        self.set_status("日志已刷新", "ok")

    def test_login(self):
        def worker():
            from campus_autologin.__main__ import run_login

            config = load_config(self.config_path)
            logger = setup_logging(config.log_dir, config.logging.level)
            return run_login(config, logger=logger)

        def done(result):
            message = ("登录成功: " if result.success else "登录失败: ") + result.message
            self.set_status(message, "ok" if result.success else "error")
            if not result.success:
                messagebox.showwarning("测试登录失败", result.message)
            self.refresh_logs()
            self.refresh_overview()

        self.run_background("正在测试登录", worker, done)

    def install_service(self):
        self._service_action("正在安装开机自启", install_autostart)

    def uninstall_service(self):
        self._service_action("正在取消开机自启", uninstall_autostart)

    def start_service(self):
        self._service_action("正在启动自动重连", start_autologin)

    def stop_service(self):
        self._service_action("正在停止自动重连", stop_autologin)

    def restart_service(self):
        self._service_action("正在按已保存配置重启自动重连", restart_autologin)

    def query_service_status(self):
        self._service_action("正在查询自动重连状态", get_service_status)

    def _service_action(self, busy_message: str, action: Callable[[], UiOperationResult]):
        def done(result: UiOperationResult):
            self.set_status(result.message, "ok" if result.ok else "error")
            self._write_text(self.service_output, result.message)
            self.refresh_overview()

        self.run_background(busy_message, action, done)

    def run_diagnostics(self):
        def worker():
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
            proxy = read_windows_proxy()
            if proxy:
                lines.append("Windows proxy:")
                lines.append(proxy)
            return "\n".join(lines)

        def done(text):
            self._write_text(self.diagnostics_text, text)
            self.set_status("诊断完成", "ok")

        self.run_background("正在运行诊断", worker, done)

    def open_config_folder(self):
        self.config = load_config(self.config_path)
        _open_folder(self.config.base_dir)

    def open_log_folder(self):
        self.config = load_config(self.config_path)
        self.config.log_dir.mkdir(parents=True, exist_ok=True)
        _open_folder(self.config.log_dir)

    # ── Background Worker ─────────────────────────────────────────────────

    def run_background(
        self, busy_message: str, worker: Callable[[], T],
        done: Callable[[T], None], *, quiet: bool = False,
    ):
        if not quiet:
            self.set_status(busy_message, "busy")

        def target():
            try:
                result = worker()
            except Exception as exc:
                self.root.after(0, lambda: self._handle_background_error(exc))
                return
            self.root.after(0, lambda: done(result))

        thread = threading.Thread(target=target, daemon=True)
        thread.start()

    def _handle_background_error(self, exc: Exception):
        message = str(exc) or exc.__class__.__name__
        self.set_status(message, "error")
        messagebox.showerror("操作失败", message)

    def set_status(self, message: str, tone: str = "ok"):
        colors = {
            "ok": Palette.canvas_mid,
            "busy": Palette.accent_breeze,
            "error": Palette.accent_ruby,
        }
        self.status_pill.configure(text=message[:60], bg=colors.get(tone, Palette.canvas_mid))

    def _write_text(self, widget: ScrolledText, text: str):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _write_log_text(self, widget: ScrolledText, text: str):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.see("end")
        widget.configure(state="disabled")

    # ── Auto Refresh ──────────────────────────────────────────────────────

    def _start_auto_refresh(self):
        self._schedule_log_refresh()
        self._schedule_status_refresh()

    def _schedule_log_refresh(self):
        if self._auto_refresh_logs and self._current_page in ("overview", "logs"):
            self.refresh_recent_log() if self._current_page == "overview" else self.refresh_logs()
        self.root.after(5000, self._schedule_log_refresh)

    def _schedule_status_refresh(self):
        if self._auto_refresh_status:
            self._probe_status()
        self.root.after(30000, self._schedule_status_refresh)

    def _probe_status(self):
        def worker():
            return probe_connection_status(self.config)

        def done(status: ConnectionStatus):
            status_map = {
                "online": ("在线", Palette.accent_sunset, Palette.accent_sunset),
                "captive_portal": ("需登录", Palette.accent_dusk, Palette.accent_dusk),
                "offline": ("离线", Palette.mute, Palette.mute),
                "not_campus": ("非校园网", Palette.accent_breeze, Palette.accent_breeze),
                "unknown": ("未知", Palette.mute, Palette.mute),
            }
            text, dot_color, _ = status_map.get(status.status, ("未知", Palette.mute, Palette.mute))
            if self._connection_label:
                self._connection_label.configure(text=text)
            if self._connection_dot:
                if status.status == "online":
                    self._connection_dot.start_pulse(dot_color)
                else:
                    self._connection_dot.stop_pulse()
                    self._connection_dot.set_color(dot_color)

        self.run_background("", worker, done, quiet=True)

    def _toggle_log_auto_refresh(self):
        self._auto_refresh_logs = not self._auto_refresh_logs
        state = "开" if self._auto_refresh_logs else "关"
        self._log_auto_btn.set_text(f"自动刷新: {state}")


# ── Helpers ───────────────────────────────────────────────────────────────────


def _compact_status(message: str) -> str:
    if "State" in message:
        for line in message.splitlines():
            if "State" in line:
                return line.split(":", 1)[-1].strip() or "已安装"
    if "失败" in message:
        return "未安装"
    return "已安装"


def _open_folder(path):
    import subprocess

    os.makedirs(path, exist_ok=True)
    if os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
        return
    subprocess.Popen(["xdg-open", str(path)])


def launch_gui(config_path: str | None = None) -> int:
    root = tk.Tk()
    CampusAutologinApp(root, config_path=config_path)
    root.mainloop()
    return 0
