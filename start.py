"""keyboard-peak 一键启动入口。

用法
====
    python start.py                  # 默认端口 8765，自动打开浏览器
    python start.py --port 9000      # 指定端口
    python start.py --no-browser     # 不自动打开浏览器
    python start.py --data D:\\x\\keylog.json   # 指定数据文件
    python start.py --demo           # 演示模式：模拟按键，不监听真实键盘

流程
====
1. 创建 KeyStore（自动加载历史数据，跨会话累积）
2. 创建 EventHub + AppServer（SSE 实时推送）
3. 启动全局键盘监听（pynput），或演示模式的按键模拟器
4. 自动打开浏览器访问可视化页面
5. Ctrl+C 退出时：停止监听、强制落盘、关闭服务
"""

from __future__ import annotations

import argparse
import atexit
import logging
import random
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Windows 控制台默认 GBK，切换 UTF-8 保证中文日志正常显示
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from kpeak.collector import KeyCollector
from kpeak.config import DEFAULT_PORT, DATA_FILE, DATA_DIR, HOST
from kpeak.server import AppServer, EventHub
from kpeak.store import KeyStore
from kpeak.tray import TrayIcon
from kpeak.window import ControlWindow

# 日志：控制台显示 INFO，简洁格式
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("kpeak.start")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="keyboard-peak",
        description="后台记录每一个键盘按键并三维可视化展示",
    )
    p.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"可视化页面端口（默认 {DEFAULT_PORT}）")
    p.add_argument("--host", type=str, default=HOST, help=f"监听地址（默认 {HOST}）")
    p.add_argument("--data", type=str, default=str(DATA_FILE), help="数据文件路径")
    p.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    p.add_argument("--demo", action="store_true", help="演示模式：模拟按键，不启动全局监听")
    return p.parse_args()


# ---------------------------------------------------------------------------
# 演示模式：模拟真实打字节奏的按键事件（用于无键盘环境下展示可视化）
# ---------------------------------------------------------------------------

# 常见按键出现概率（近似真实打字分布）
_DEMO_WEIGHTS = {
    "A": 8, "B": 1.5, "C": 2.8, "D": 4.3, "E": 12.7, "F": 2.2, "G": 2.0,
    "H": 6.1, "I": 7.0, "J": 0.15, "K": 0.8, "L": 4.0, "M": 2.4, "N": 6.7,
    "O": 7.5, "P": 1.9, "Q": 0.1, "R": 6.0, "S": 6.3, "T": 9.1, "U": 2.8,
    "V": 1.0, "W": 2.4, "X": 0.15, "Y": 2.0, "Z": 0.1,
    "SPACE": 18.0, "ENTER": 2.8, "BACKSPACE": 1.7, "TAB": 0.4,
    "1": 1.4, "2": 0.6, "3": 0.7, "4": 0.3, "5": 0.4, "6": 0.4,
    "7": 0.3, "8": 0.4, "9": 0.3, "0": 0.4,
    "COMMA": 1.2, "PERIOD": 1.1, "SLASH": 0.3, "SEMICOLON": 0.2,
    "MINUS": 0.2, "EQUAL": 0.1, "QUOTE": 0.2, "LBRACKET": 0.1, "RBRACKET": 0.1,
    "LSHIFT": 2.0, "RSHIFT": 0.8, "LCTRL": 0.5, "RCTRL": 0.05, "LALT": 0.2,
    "CAPSLOCK": 0.03, "F1": 0.01, "F5": 0.05, "DELETE": 0.3, "BACKSPACE": 0.5,
    "NUMPAD_0": 0.08, "NUMPAD_1": 0.06, "NUMPAD_5": 0.05, "NUMPAD_ENTER": 0.03,
    "ESC": 0.02, "HOME": 0.01, "END": 0.01, "UP": 0.05, "DOWN": 0.06,
    "LEFT": 0.08, "RIGHT": 0.08, "PAGEUP": 0.01, "PAGEDOWN": 0.01,
}


def _demo_gen():
    """生成符合分布的按键序列（无限）。"""
    keys = list(_DEMO_WEIGHTS.keys())
    weights = list(_DEMO_WEIGHTS.values())
    while True:
        yield random.choices(keys, weights=weights, k=1)[0]


def _run_demo(store, hub, stop_event: threading.Event) -> None:
    """演示模式线程：按打字节奏发布随机按键事件。"""
    gen = _demo_gen()
    # 有间歇的节奏：平均约 90 键/分
    while not stop_event.is_set():
        key = next(gen)
        store.record(key)
        hub.publish({"key": key, "ts": time.time()})
        # 80% 概率快速连打（0.05~0.25s），20% 概率停顿（0.3~1.2s）
        if random.random() < 0.8:
            delay = random.uniform(0.05, 0.25)
        else:
            delay = random.uniform(0.3, 1.2)
        stop_event.wait(delay)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main() -> int:
    args = _parse_args()

    if args.demo:
        # 演示模式使用独立数据文件，避免污染真实数据
        args.data = str(DATA_DIR / "demo_keylog.json")
        log.info("演示模式：使用独立数据文件 %s", args.data)

    store = KeyStore(args.data)
    hub = EventHub()
    server = AppServer(store, hub, port=args.port, host=args.host)

    stop_demo = threading.Event()

    if args.demo:
        collector = None
        demo_thread = threading.Thread(
            target=_run_demo, args=(store, hub, stop_demo), daemon=True
        )
        demo_thread.start()
    else:
        collector = KeyCollector(store, on_key=lambda kid: hub.publish({"key": kid, "ts": time.time()}))

    # ---------- 系统托盘 + 控制窗口 ----------
    quit_event = threading.Event()
    tooltip_interval = 5.0
    url = server.url
    data_dir = store.data_file.parent
    mode = "演示模式（模拟按键）" if args.demo else "全局监听模式"

    def _open_viz():
        webbrowser.open(url)

    def _open_data():
        try:
            os.startfile(str(data_dir))  # 资源管理器打开数据目录
        except Exception:
            log.exception("cannot open data dir")

    def _exit_app():
        quit_event.set()

    def _window_snapshot() -> dict:
        """为控制窗口提供增强快照（含模式/URL/数据路径）。"""
        snap = store.snapshot()
        snap["mode"] = mode
        snap["url"] = url
        snap["data"] = str(store.data_file)
        snap["rate"] = compute_rate()
        return snap

    def compute_rate() -> float:
        """近 60 秒实时速率（键/分）：从 recent 时间戳计算。"""
        now = time.time()
        recent = store.recent
        # store.recent 是 deque[(id, ts)]
        cutoff = now - 60.0
        n = sum(1 for _, ts in recent if ts >= cutoff)
        return n

    ctrl_win = ControlWindow(
        get_snapshot=_window_snapshot,
        open_viz=_open_viz,
        open_data=_open_data,
        on_exit=_exit_app,
    )
    tray = TrayIcon(
        on_open=_open_viz,
        on_quit=_exit_app,
        on_data=_open_data,
        on_show=ctrl_win.show,  # 双击托盘 / 菜单「显示控制窗口」→ 弹出控制窗口
    )

    def _cleanup():
        log.info("shutting down ...")
        if collector is not None:
            collector.stop()
        stop_demo.set()
        ctrl_win.stop()
        tray.stop()
        store.flush()
        server.stop()

    atexit.register(_cleanup)

    server.start()
    if collector is not None:
        collector.start()
    ctrl_win.start()
    tray.start()
    log.info("数据文件: %s", store.data_file)
    log.info("历史累计按键: %d 次（%d 种按键）", store.total, len(store.counts))
    log.info("可视化页面: %s", server.url)
    log.info("控制窗口 + 系统托盘已就绪：托盘右键「显示控制窗口」或双击图标")

    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(server.url)).start()

    print()
    print("=" * 58)
    print("  keyboard-peak · 键盘按键三维可视化")
    print(f"  模式: {mode}")
    print(f"  可视化页面: {server.url}")
    print("  托盘图标已常驻：右键「显示控制窗口」/ 打开页面 / 退出")
    print("  源码运行按 Ctrl+C 停止；打包版从托盘或控制窗口退出")
    print("=" * 58)
    print()

    try:
        last_tip = 0.0
        while not quit_event.is_set():
            time.sleep(0.5)
            if collector is not None and collector.running is False:
                log.warning("listener stopped unexpectedly")
            # 周期落盘（flush 内部有 dirty 检查，非脏时零开销）
            store.flush()
            # 定期更新托盘提示（累计按键数）
            now = time.time()
            if now - last_tip >= tooltip_interval:
                last_tip = now
                tip = f"keyboard-peak · 已记录 {store.total:,} 次按键"
                tray.set_tooltip(tip)
    except KeyboardInterrupt:
        log.info("收到 Ctrl+C")
    finally:
        _cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())