"""tkinter 控制窗口：显示运行状态，提供操作按钮。

功能
====
- 显示：运行模式 / 端口 / 可视化 URL / 累计按键 / 今日按键 / 实时速率 / 数据文件路径
- 按钮：打开可视化页面 / 打开数据目录 / 退出程序
- 关闭窗口（点 X）→ 最小化到托盘（程序继续后台运行，由托盘「退出」结束）
- 独立线程运行 tkinter 主循环；数据每 1 秒从 store 快照刷新（线程安全）
- 跨线程控制：show()/stop() 通过线程安全队列转发，所有 tk 操作都在 tk 线程内

线程安全说明（重要）
====================
tkinter/Tcl 对象只能在创建它的线程中访问。本窗口在独立线程创建 Tk()，
因此：所有 tk 对象操作（标签更新、窗口显隐）都发生在该线程内；
外部线程（托盘线程）只通过 queue.Queue 发送指令，由 tk 线程用 after()
轮询执行。禁止外部线程直接调用窗口方法触碰 tk 对象。
"""

from __future__ import annotations

import ctypes
import json
import logging
import os
import queue as queue_mod
import threading
import time
import tkinter as tk
from tkinter import ttk

# ---------------------------------------------------------------------------
# 高 DPI 支持：必须在创建任何 Tk 窗口之前调用，否则界面在高分屏上模糊
# ---------------------------------------------------------------------------

def _enable_dpi_awareness() -> None:
    """启用 Windows 高 DPI 感知（Per-Monitor V2），让 tkinter 在高分屏清晰渲染。"""
    if os.name != "nt":
        return
    try:
        # Windows 10 1809+：Per-Monitor V2（最佳）
        ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)  # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
    except Exception:
        try:
            # 旧版 Windows：System DPI Aware
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # PROCESS_SYSTEM_DPI_AWARE
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


_enable_dpi_awareness()

log = logging.getLogger("kpeak.window")

# 暗色主题配色
BG = "#0b0d1e"
CARD = "#141834"
FG = "#e8ecff"
DIM = "#8b93b8"
ACCENT = "#6c8cff"
ACCENT2 = "#00e5ff"

BUTTON_STYLE = {
    "padding": (14, 8),
    "relief": "flat",
    "cursor": "hand2",
}


class ControlWindow:
    def __init__(self, get_snapshot, open_viz=None, open_data=None, on_exit=None,
                 settings=None, export_data=None, import_data=None):
        """get_snapshot: 可调用，返回 {total, today_total, ...}（线程安全）。
        open_viz / open_data / on_exit：按钮回调（在 tk 线程内执行）。
        settings: Settings 对象（通知开关等，可空）。
        export_data / import_data：数据导出/导入回调（在 tk 线程调用）。"""
        self.get_snapshot = get_snapshot
        self.open_viz = open_viz
        self.open_data = open_data
        self.on_exit = on_exit
        self.settings = settings
        self.export_data = export_data
        self.import_data = import_data
        self._cmds: queue_mod.Queue = queue_mod.Queue()
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._stopping = threading.Event()

        self._root: tk.Tk | None = None
        self._vars: dict[str, tk.StringVar] = {}

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True, name="kpeak-window")
        self._thread.start()

    def _run(self) -> None:
        try:
            self._root = tk.Tk()
            self._root.title("keyboard-peak 控制中心")
            self._root.configure(bg=BG)
            self._root.attributes("-topmost", False)
            self._root.resizable(False, False)
            self._build_ui()
            # 关窗 → 隐藏到托盘（不退出）
            self._root.protocol("WM_DELETE_WINDOW", self._hide)
            self._ready.set()
            self._refresh()
            self._poll_cmds()
            self._root.mainloop()
            # mainloop 退出（quit 指令）→ 先释放 tk 对象引用，再销毁窗口
            # 顺序关键：必须先清变量（此时 tk 解释器仍存活），再 destroy，
            # 否则 Variable.__del__ 在 root 销毁后访问已死的 Tcl 会报错
            for v in self._vars.values():
                try:
                    v.get()
                except Exception:
                    pass
            self._vars.clear()
            self._notify_var = None
            self._daily_var = None
            try:
                self._root.destroy()
            except Exception:
                pass
            self._root = None
        except Exception:
            log.exception("control window error")
        finally:
            self._ready.set()

    def _build_ui(self) -> None:
        root = self._root
        style = ttk.Style(root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TFrame", background=BG)
        style.configure("Title.TLabel", background=BG, foreground=FG, font=("Segoe UI", 15, "bold"))
        style.configure("Dim.TLabel", background=BG, foreground=DIM, font=("Microsoft YaHei UI", 9))
        style.configure("Val.TLabel", background=BG, foreground=ACCENT2, font=("Segoe UI", 20, "bold"))
        style.configure("Label.TLabel", background=BG, foreground=DIM, font=("Microsoft YaHei UI", 10))
        style.configure("Accent.TButton", background="#1c2450", foreground=FG,
                        font=("Microsoft YaHei UI", 10), padding=BUTTON_STYLE["padding"],
                        relief="flat")
        style.map("Accent.TButton", background=[("active", "#2a3570")])

        root.columnconfigure(0, weight=1)
        pad = {"padx": 20, "pady": 6}

        tk.Label(root, text="⌨ keyboard·peak 控制中心", bg=BG, fg=FG,
                 font=("Segoe UI", 15, "bold")).grid(row=0, column=0, sticky="w", **pad)

        # 状态卡片
        card = tk.Frame(root, bg=CARD, bd=0, highlightthickness=1,
                        highlightbackground="#1f2650")
        card.grid(row=1, column=0, sticky="ew", padx=16, pady=4)

        def add(label_text, key, row):
            tk.Label(card, text=label_text, bg=CARD, fg=DIM,
                     font=("Microsoft YaHei UI", 9), anchor="w").grid(row=row, column=0, sticky="w", padx=(16, 8), pady=4)
            self._vars[key] = tk.StringVar(value="")
            tk.Label(card, textvariable=self._vars[key], bg=CARD, fg=ACCENT2,
                     font=("Segoe UI", 11, "bold"), anchor="w").grid(row=row, column=1, sticky="w", pady=4)

        tk.Label(card, text="运行状态", bg=CARD, fg=ACCENT,
                 font=("Microsoft YaHei UI", 11, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(12, 4))
        add("累计按键：", "total", 1)
        add("今日按键：", "today", 2)
        add("实时速率：", "rate", 3)
        add("运行模式：", "mode", 4)
        add("可视化地址：", "url", 5)
        add("数据文件：", "data", 6)
        card.grid_columnconfigure(1, weight=1)

        # 按钮行
        btns = tk.Frame(root, bg=BG)
        btns.grid(row=2, column=0, sticky="ew", padx=16, pady=12)
        for i in range(4):
            btns.grid_columnconfigure(i, weight=1)

        b_open = ttk.Button(btns, text="打开可视化页面", style="Accent.TButton",
                            command=lambda: self._safe(self.open_viz))
        b_open.grid(row=0, column=0, sticky="ew", padx=4)

        b_data = ttk.Button(btns, text="打开数据目录", style="Accent.TButton",
                            command=lambda: self._safe(self.open_data))
        b_data.grid(row=0, column=1, sticky="ew", padx=4)

        b_about = ttk.Button(btns, text="关于", style="Accent.TButton",
                             command=self._on_about)
        b_about.grid(row=0, column=2, sticky="ew", padx=4)

        b_exit = ttk.Button(btns, text="退出程序", style="Accent.TButton",
                            command=lambda: self._safe(self.on_exit))
        b_exit.grid(row=0, column=3, sticky="ew", padx=4)

        tk.Label(root, text="关闭本窗口将最小化到托盘（不退出）；如需完全退出请点「退出程序」或托盘右键菜单",
                 bg=BG, fg=DIM, font=("Microsoft YaHei UI", 8)).grid(row=3, column=0, sticky="w", padx=16, pady=(0, 10))

        self._build_settings_section(root, 4)
        self._build_data_section(root, 5)

        # 居中
        root.update_idletasks()
        w, h = root.winfo_reqwidth(), root.winfo_reqheight()
        x = (root.winfo_screenwidth() - w) // 2
        y = (root.winfo_screenheight() - h) // 3
        root.geometry(f"+{x}+{y}")

    # ---------------- 设置区：通知开关 ----------------

    def _build_settings_section(self, root, row) -> None:
        if self.settings is None:
            return
        card = tk.Frame(root, bg=CARD, bd=0, highlightthickness=1, highlightbackground="#1f2650")
        card.grid(row=row, column=0, sticky="ew", padx=16, pady=4)
        tk.Label(card, text="设置", bg=CARD, fg=ACCENT,
                 font=("Microsoft YaHei UI", 11, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(12, 2))

        self._notify_var = tk.BooleanVar(value=bool(self.settings.get("notify_enabled", True)))
        self._daily_var = tk.BooleanVar(value=bool(self.settings.get("notify_daily", False)))
        # 统一登记到 _vars，便于退出时一次性清理（避免主线程 GC 触发 __del__ 报错）
        self._vars["notify"] = self._notify_var
        self._vars["daily"] = self._daily_var
        tk.Checkbutton(card, text="右下角通知推送（启动 / 停止 / 暂停通知）",
                       variable=self._notify_var, bg=CARD, fg=FG, activebackground=CARD,
                       activeforeground=FG, selectcolor="#1c2450", font=("Microsoft YaHei UI", 9),
                       command=self._on_notify_toggle).grid(row=1, column=0, columnspan=2, sticky="w", padx=16, pady=3)

        tk.Checkbutton(card, text="每日统计摘要通知",
                       variable=self._daily_var, bg=CARD, fg=FG, activebackground=CARD,
                       activeforeground=FG, selectcolor="#1c2450", font=("Microsoft YaHei UI", 9),
                       command=self._on_daily_toggle).grid(row=2, column=0, columnspan=2, sticky="w", padx=16, pady=3)
        card.grid_columnconfigure(1, weight=1)

    def _on_notify_toggle(self) -> None:
        if self.settings is not None:
            self.settings.set("notify_enabled", bool(self._notify_var.get()))

    def _on_daily_toggle(self) -> None:
        if self.settings is not None:
            self.settings.set("notify_daily", bool(self._daily_var.get()))

    # ---------------- 数据区：导出 / 导入 ----------------

    def _build_data_section(self, root, row) -> None:
        if self.export_data is None and self.import_data is None:
            return
        card = tk.Frame(root, bg=CARD, bd=0, highlightthickness=1, highlightbackground="#1f2650")
        card.grid(row=row, column=0, sticky="ew", padx=16, pady=4)
        tk.Label(card, text="数据", bg=CARD, fg=ACCENT,
                 font=("Microsoft YaHei UI", 11, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(12, 4))

        btns = tk.Frame(card, bg=CARD)
        btns.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 10))
        btns.grid_columnconfigure(0, weight=1)
        btns.grid_columnconfigure(1, weight=1)

        ttk.Button(btns, text="导出数据…", style="Accent.TButton",
                   command=self._on_export).grid(row=0, column=0, sticky="ew", padx=4)
        ttk.Button(btns, text="导入数据…", style="Accent.TButton",
                   command=self._on_import).grid(row=0, column=1, sticky="ew", padx=4)

    def _on_export(self) -> None:
        from tkinter import filedialog
        try:
            path = filedialog.asksaveasfilename(
                title="导出键盘统计数据",
                defaultextension=".json",
                initialfile=f"keyboard-peak-{time.strftime('%Y%m%d-%H%M%S')}.json",
                filetypes=[("JSON 数据", "*.json"), ("所有文件", "*.*")],
            )
        except Exception:
            return
        if not path:
            return
        try:
            payload = self.export_data() if self.export_data else {}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            self._notice(f"已导出到：\n{path}")
        except Exception as e:
            self._notice(f"导出失败：{e}", error=True)

    def _on_import(self) -> None:
        from tkinter import filedialog, messagebox
        try:
            path = filedialog.askopenfilename(
                title="导入键盘统计数据",
                filetypes=[("JSON 数据", "*.json"), ("所有文件", "*.*")],
            )
        except Exception:
            return
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception as e:
            self._notice(f"读取文件失败：{e}", error=True)
            return
        # 询问合并 or 覆盖
        merge = messagebox.askyesno(
            "导入方式",
            "选择导入方式：\n\n「是」= 合并到现有数据（累加）\n「否」= 覆盖现有数据",
        )
        try:
            if self.import_data:
                result = self.import_data(payload, merge=merge)
                self._notice(result.get("message", "导入完成"), error=not result.get("ok", True))
        except Exception as e:
            self._notice(f"导入失败：{e}", error=True)

    def _notice(self, text: str, error: bool = False) -> None:
        """底部提示（非模态，不阻塞窗口）。"""
        try:
            from tkinter import messagebox
            if error:
                messagebox.showerror("keyboard-peak", text, parent=self._root)
            else:
                messagebox.showinfo("keyboard-peak", text, parent=self._root)
        except Exception:
            pass

    def _on_about(self) -> None:
        """关于对话框：版本 / 说明 / 仓库。"""
        try:
            import kpeak
            from tkinter import messagebox
            ver = getattr(kpeak, "__version__", "?")
            msg = (
                "keyboard-peak 键盘按键三维可视化\n"
                f"\n版本：{ver}\n"
                "功能：后台记录每一次键盘按键，\n"
                "      以 3D 立体键盘 + 数据柱实时可视化。\n"
                "\n三种显示模式：经典柱 / 覆盖柱 / 热力图\n"
                "托盘右键可暂停采集、打开页面或退出。\n"
                "\nGitHub：github.com/dboycht/keyboard-peak\n"
                "\n© 2026 Mizuki"
            )
            messagebox.showinfo("关于 keyboard-peak", msg, parent=self._root)
        except Exception:
            log.exception("about dialog failed")

    # ------------------------------------------------------------------
    # 状态刷新（tk 线程内）
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        if self._root is None or self._stopping.is_set():
            return
        try:
            snap = self.get_snapshot() if self.get_snapshot else {}
        except Exception:
            snap = {}
        try:
            self._vars["total"].set(f"{snap.get('total', 0):,}")
            self._vars["today"].set(f"{snap.get('today_total', 0):,}")
            rate = snap.get("rate", 0)
            self._vars["rate"].set(f"{rate:.1f} 键/分")
            if "mode" in snap:
                self._vars["mode"].set(snap["mode"])
            if "url" in snap:
                self._vars["url"].set(snap["url"])
            if "data" in snap:
                self._vars["data"].set(snap["data"])
        except Exception:
            pass
        if self._root is not None:
            self._root.after(1000, self._refresh)

    # ------------------------------------------------------------------
    # 指令轮询（实现跨线程 show/hide/quit）
    # ------------------------------------------------------------------

    def _poll_cmds(self) -> None:
        if self._root is None:
            return
        # 注意：不因 _stopping 提前 return —— 必须消费队列中的 quit 指令
        try:
            while True:
                cmd = self._cmds.get_nowait()
                self._exec_cmd(cmd)
        except queue_mod.Empty:
            pass
        if self._stopping.is_set():
            return  # 已处理 quit（_exec_cmd 会调用 root.quit()）
        self._root.after(150, self._poll_cmds)

    def _exec_cmd(self, cmd) -> None:
        if cmd == "show":
            self._show()
        elif cmd == "hide":
            self._hide()
        elif cmd == "quit":
            self._stopping.set()
            try:
                self._root.quit()  # 让 mainloop 返回（在 tk 线程内调用）
            except Exception:
                pass

    # ------------------------------------------------------------------
    # 外部线程调用的接口（线程安全：只往队列发指令）
    # ------------------------------------------------------------------

    def show(self) -> None:
        """显示并置顶窗口（可从托盘线程调用）。"""
        self._cmds.put("show")

    def hide(self) -> None:
        self._cmds.put("hide")

    def stop(self) -> None:
        """完全关闭窗口线程。

        通过命令队列发 'quit'，由 tk 线程在轮询时自行退出 —— 不做跨线程
        after 调用（跨线程 after 会注册 Tcl async handler，退出时触发
        "Tcl_AsyncDelete: async handler deleted by the wrong thread"）。
        """
        self._stopping.set()
        self._cmds.put("quit")
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    def _show(self) -> None:
        if self._root is None:
            return
        try:
            self._root.deiconify()
            self._root.lift()
            self._root.focus_force()
        except Exception:
            pass

    def _hide(self) -> None:
        if self._root is None:
            return
        try:
            self._root.withdraw()
        except Exception:
            pass

    @staticmethod
    def _safe(fn) -> None:
        if fn is None:
            return
        try:
            fn()
        except Exception:
            log.exception("window button callback failed")