"""系统托盘图标（纯 ctypes 实现，零第三方依赖）。

功能
====
- 常驻系统托盘（Windows Shell 通知区域）
- 右键菜单：打开可视化页面 / 打开数据目录 / 退出
- 双击托盘图标：打开可视化页面
- 气泡提示实时显示累计按键数

实现要点
========
- 用 ctypes 调 Shell_NotifyIconW / CreatePopupMenuW / TrackPopupMenu 等 Win32 API
- 需要一个隐藏窗口接收托盘回调消息（WM_APP+1 自定义消息）
- 菜单命令通过 WM_COMMAND 分发
- 图标：运行时用纯字节生成一个 32x32 ICO（键盘柱状图），LoadImageW 加载
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import logging
import os
import struct
import tempfile
import threading
import webbrowser
from pathlib import Path

log = logging.getLogger("kpeak.tray")

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
WM_USER = 0x0400
WM_APP = 0x8000
WM_TRAYICON = WM_APP + 1          # 托盘回调消息
NIM_ADD = 0x0
NIM_MODIFY = 0x1
NIM_DELETE = 0x2
NIF_MESSAGE = 0x1
NIF_ICON = 0x2
NIF_TIP = 0x4
NIF_INFO = 0x10
NIS_HIDDEN = 0x1

WM_RBUTTONUP = 0x0005
WM_LBUTTONDBLCLK = 0x0203
WM_COMMAND = 0x0111
WM_DESTROY = 0x0002
WM_CLOSE = 0x0010
WM_QUIT = 0x0012

MF_STRING = 0x0
MF_SEPARATOR = 0x800
TPM_RIGHTBUTTON = 0x2
TPM_RETURNCMD = 0x100
TPM_NONOTIFY = 0x80

CW_USEDEFAULT = 0x80000000
WS_POPUP = 0x80000000
SW_SHOW = 5
SW_HIDE = 0

ID_OPEN = 40001
ID_DATA = 40002
ID_EXIT = 40003

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)


# ---------------------------------------------------------------------------
# 结构定义（必须先于 argtypes 引用）
# ---------------------------------------------------------------------------

# __stdcall 回调
WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_longlong, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wt.UINT),
        ("style", wt.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wt.HINSTANCE),
        ("hIcon", wt.HICON),
        ("hCursor", wt.HANDLE),
        ("hbrBackground", wt.HBRUSH),
        ("lpszMenuName", wt.LPCWSTR),
        ("lpszClassName", wt.LPCWSTR),
        ("hIconSm", wt.HICON),
    ]


class NOTIFYICONDATAW(ctypes.Structure):
    """Windows 10/11 的 NOTIFYICONDATA（64 位）布局。"""
    _fields_ = [
        ("cbSize", wt.DWORD),
        ("hWnd", wt.HWND),
        ("uID", wt.UINT),
        ("uFlags", wt.UINT),
        ("uCallbackMessage", wt.UINT),
        ("hIcon", wt.HICON),
        ("szTip", ctypes.c_wchar * 128),
        ("dwState", wt.DWORD),
        ("dwStateMask", wt.DWORD),
        ("szInfo", ctypes.c_wchar * 256),
        ("uTimeout", wt.UINT),
        ("szInfoTitle", ctypes.c_wchar * 64),
        ("dwInfoFlags", wt.DWORD),
        ("guidItem", ctypes.c_byte * 16),
        ("hBalloonIcon", wt.HICON),
    ]


# 设置关键函数签名，避免 64 位指针/句柄被截断
user32.DefWindowProcW.restype = ctypes.c_longlong
user32.DefWindowProcW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.PostMessageW.restype = wt.BOOL
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wt.MSG)]
user32.DispatchMessageW.restype = ctypes.c_longlong
user32.TranslateMessage.argtypes = [ctypes.POINTER(wt.MSG)]
user32.GetMessageW.argtypes = [ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT]
user32.GetMessageW.restype = ctypes.c_int
user32.CreateWindowExW.argtypes = [
    wt.DWORD, wt.LPCWSTR, wt.LPCWSTR, wt.DWORD,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wt.HWND, wt.HMENU, wt.HINSTANCE, wt.LPVOID,
]
user32.CreateWindowExW.restype = wt.HWND
user32.RegisterClassExW.argtypes = [ctypes.POINTER(WNDCLASSEXW)]
user32.RegisterClassExW.restype = wt.ATOM
user32.TrackPopupMenu.argtypes = [
    wt.HMENU, wt.UINT, ctypes.c_int, ctypes.c_int,
    ctypes.c_int, wt.HWND, ctypes.c_void_p,
]
user32.TrackPopupMenu.restype = wt.UINT
user32.CreatePopupMenu.restype = wt.HMENU
user32.AppendMenuW.argtypes = [wt.HMENU, wt.UINT, ctypes.c_size_t, wt.LPCWSTR]
user32.AppendMenuW.restype = wt.BOOL
user32.DestroyMenu.argtypes = [wt.HMENU]
user32.GetCursorPos.argtypes = [ctypes.POINTER(wt.POINT)]
user32.GetCursorPos.restype = wt.BOOL
user32.SetForegroundWindow.argtypes = [wt.HWND]
user32.SetForegroundWindow.restype = wt.BOOL
user32.DestroyWindow.argtypes = [wt.HWND]
user32.DestroyWindow.restype = wt.BOOL
user32.LoadIconW.argtypes = [wt.HINSTANCE, wt.LPCWSTR]
user32.LoadIconW.restype = wt.HICON
user32.LoadImageW.argtypes = [wt.HINSTANCE, wt.LPCWSTR, wt.UINT, ctypes.c_int, ctypes.c_int, wt.UINT]
user32.LoadImageW.restype = wt.HANDLE
shell32.Shell_NotifyIconW.argtypes = [wt.DWORD, ctypes.POINTER(NOTIFYICONDATAW)]
shell32.Shell_NotifyIconW.restype = wt.BOOL
kernel32.GetModuleHandleW.argtypes = [wt.LPCWSTR]
kernel32.GetModuleHandleW.restype = wt.HINSTANCE


# ---------------------------------------------------------------------------
# 图标生成：手写 32x32 32bpp ICO（蓝底 + 键帽 + 数据柱）
# ---------------------------------------------------------------------------

def _build_icon_bytes() -> bytes:
    """生成一个 32x32 的 ICO 文件字节：键盘剪影 + 一根高耸数据柱。"""
    W = H = 32
    # 背景透明
    px = bytearray(W * H * 4)  # BGRA
    for y in range(H):
        for x in range(W):
            # 键盘底座（深蓝圆角矩形）
            in_base = 2 <= x <= 29 and 22 <= y <= 28
            in_base = in_base and not (x <= 3 and y >= 26)
            if in_base:
                px[(y * W + x) * 4 + 0] = 60     # B
                px[(y * W + x) * 4 + 1] = 80     # G
                px[(y * W + x) * 4 + 2] = 140    # R
                px[(y * W + x) * 4 + 3] = 255    # A
            # 键帽（小方块）
            if 4 <= x <= 8 and 14 <= y <= 20:
                px[(y * W + x) * 4 + 0] = 200; px[(y * W + x) * 4 + 1] = 220
                px[(y * W + x) * 4 + 2] = 255; px[(y * W + x) * 4 + 3] = 255
            if 10 <= x <= 14 and 14 <= y <= 20:
                px[(y * W + x) * 4 + 0] = 200; px[(y * W + x) * 4 + 1] = 220
                px[(y * W + x) * 4 + 2] = 255; px[(y * W + x) * 4 + 3] = 255
            if 16 <= x <= 20 and 14 <= y <= 20:
                px[(y * W + x) * 4 + 0] = 200; px[(y * W + x) * 4 + 1] = 220
                px[(y * W + x) * 4 + 2] = 255; px[(y * W + x) * 4 + 3] = 255
            if 22 <= x <= 26 and 14 <= y <= 20:
                px[(y * W + x) * 4 + 0] = 200; px[(y * W + x) * 4 + 1] = 220
                px[(y * W + x) * 4 + 2] = 255; px[(y * W + x) * 4 + 3] = 255
            # 数据柱（从键帽顶到屏幕顶，红橙色，向右上倾斜）
            if 16 <= x <= 19 and 4 <= y <= 13:
                px[(y * W + x) * 4 + 0] = 60; px[(y * W + x) * 4 + 1] = 90
                px[(y * W + x) * 4 + 2] = 255; px[(y * W + x) * 4 + 3] = 255
            if 20 <= x <= 23 and 4 <= y <= 13:
                px[(y * W + x) * 4 + 0] = 100; px[(y * W + x) * 4 + 1] = 160
                px[(y * W + x) * 4 + 2] = 255; px[(y * W + x) * 4 + 3] = 255

    # --- 组装 ICO ---
    # ICONDIR
    header = struct.pack("<HHH", 0, 1, 1)  # reserved, type=icon, count=1
    # ICONDIRENTRY
    bmp_size = 40 + W * H * 4
    entry = struct.pack("<BBBBHHII", 32, 32, 0, 0, 1, 32, bmp_size, 22)
    # BITMAPINFOHEADER
    bih = struct.pack(
        "<IiiHHIIiiII",
        40, W, H * 2, 1, 32, 0, W * H * 4, 0, 0, 0, 0
    )
    return header + entry + bih + bytes(px)


# 全局缓存图标文件路径（进程内只生成一次）
_icon_path = None


def _ensure_icon() -> str:
    global _icon_path
    if _icon_path and os.path.exists(_icon_path):
        return _icon_path
    fd, path = tempfile.mkstemp(suffix=".ico", prefix="kpeak-")
    with os.fdopen(fd, "wb") as f:
        f.write(_build_icon_bytes())
    _icon_path = path
    return path


# ---------------------------------------------------------------------------
# 托盘图标
# ---------------------------------------------------------------------------

class TrayIcon:
    def __init__(self, on_open: object, on_quit: object, on_data: object | None = None):
        """on_open/on_quit/on_data：菜单回调（无参或单参函数）。"""
        self.on_open = on_open
        self.on_quit = on_quit
        self.on_data = on_data
        self._hwnd = None
        self._icon = None
        self._nid = None
        self._thread: threading.Thread | None = None
        self._active = threading.Event()
        self._menu_open = ID_OPEN
        self._menu_data = ID_DATA
        self._menu_exit = ID_EXIT
        # 重要：ctypes 回调对象必须常驻，否则窗口消息到达时指向已释放的内存会崩溃
        self._wnd_proc_cb = WNDPROC(self._wnd_proc)

    # ---------------- 消息循环 ----------------

    def _wnd_proc(self, hwnd, msg, wparam, lparam) -> int:
        if msg == WM_TRAYICON:
            if lparam == WM_RBUTTONUP:
                self._show_menu()
                return 0
            if lparam == WM_LBUTTONDBLCLK:
                self._call(self.on_open)
                return 0
        elif msg == WM_COMMAND:
            cmd = wparam & 0xFFFF
            if cmd == ID_OPEN:
                self._call(self.on_open)
            elif cmd == ID_DATA:
                self._call(self.on_data)
            elif cmd == ID_EXIT:
                self._call(self.on_quit)
            return 0
        elif msg == WM_CLOSE:
            # 停止：通知消息循环退出
            user32.PostQuitMessage(0)
            return 0
        elif msg == WM_DESTROY:
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    @staticmethod
    def _call(fn) -> None:
        if fn is None:
            return
        try:
            fn()
        except Exception:
            log.exception("tray callback failed")

    def _register_class(self) -> int:
        wc = WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(wc)
        wc.lpfnWndProc = self._wnd_proc_cb
        wc.hInstance = kernel32.GetModuleHandleW(None)
        wc.lpszClassName = "kpeak_tray_cls"
        return user32.RegisterClassExW(ctypes.byref(wc))

    def _create_window(self) -> None:
        self._register_class()
        self._hwnd = user32.CreateWindowExW(
            0, "kpeak_tray_cls", "keyboard-peak tray", WS_POPUP,
            0, 0, 0, 0, None, None, kernel32.GetModuleHandleW(None), None
        )

    def _add_notify(self) -> None:
        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(nid)
        nid.hWnd = self._hwnd
        nid.uID = 1
        nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        nid.uCallbackMessage = WM_TRAYICON
        nid.hIcon = self._icon
        nid.szTip = "keyboard-peak · 键盘按键三维可视化"
        shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))
        self._nid = nid

    def _show_menu(self) -> None:
        """弹出右键菜单。"""
        hMenu = user32.CreatePopupMenu()
        user32.AppendMenuW(hMenu, MF_STRING, ID_OPEN, "打开可视化页面")
        user32.AppendMenuW(hMenu, MF_STRING, ID_DATA, "打开数据目录")
        user32.AppendMenuW(hMenu, MF_SEPARATOR, 0, None)
        user32.AppendMenuW(hMenu, MF_STRING, ID_EXIT, "退出")

        pt = wt.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        # 设置前景窗口以确保菜单正常显示
        user32.SetForegroundWindow(self._hwnd)
        cmd = user32.TrackPopupMenu(
            hMenu, TPM_RIGHTBUTTON | TPM_RETURNCMD | TPM_NONOTIFY,
            pt.x, pt.y, 0, self._hwnd, None
        )
        user32.PostMessageW(self._hwnd, WM_COMMAND, cmd, 0)
        user32.DestroyMenu(hMenu)

    # ---------------- 对外 API ----------------

    def start(self) -> None:
        if self._active.is_set():
            return
        self._active.set()
        self._thread = threading.Thread(target=self._run, daemon=True, name="tray")
        self._thread.start()

    def _run(self) -> None:
        try:
            self._icon = user32.LoadImageW(
                None, _ensure_icon(), 1, 32, 32, 0x10  # LR_LOADFROMFILE
            )
            if not self._icon:
                # 退化为系统默认应用图标
                self._icon = user32.LoadIconW(None, 32512)
            self._create_window()
            self._add_notify()
            log.info("tray icon added")
            msg = wt.MSG()
            while True:
                r = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if r <= 0:
                    break  # WM_QUIT 或错误
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        except Exception:
            log.exception("tray thread error")
        finally:
            # 清理：删除通知图标 + 销毁窗口
            if self._nid is not None:
                try:
                    shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self._nid))
                except Exception:
                    pass
                self._nid = None
            if self._hwnd:
                try:
                    user32.DestroyWindow(self._hwnd)
                except Exception:
                    pass
                self._hwnd = None
            self._active.clear()
            log.info("tray icon removed")

    def set_tooltip(self, text: str) -> None:
        """更新气泡提示文本（NIM_MODIFY）。"""
        if self._nid is None or not self._active.is_set():
            return
        try:
            nid = self._nid
            nid.uFlags = NIF_TIP | NIF_INFO
            nid.szInfoTitle = "keyboard-peak"
            nid.dwInfoFlags = 0
            truncated = text[:120]
            nid.szTip = truncated
            nid.szInfo = truncated
            shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(nid))
        except Exception:
            pass

    def stop(self) -> None:
        self._active.clear()
        # 投递 WM_CLOSE 唤醒消息循环（在托盘线程内执行清理，避免跨线程销毁）
        try:
            if self._hwnd:
                user32.PostMessageW(self._hwnd, WM_CLOSE, 0, 0)
        except Exception:
            pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)