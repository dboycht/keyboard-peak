"""测试：完整程序退出（demo 模式）时无 tkinter 告警。"""
import os
import signal
import subprocess
import sys
import time
import urllib.request
import json


def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    port = "8910"
    proc = subprocess.Popen(
        [sys.executable, "start.py", "--demo", "--no-browser", "--port", port],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
        errors="replace", cwd=base,
    )
    try:
        # 等服务起来
        for _ in range(24):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/snapshot", timeout=2).read()
                break
            except Exception:
                time.sleep(0.5)
        time.sleep(2.5)
        # 正常退出（模拟托盘/控制窗口退出 → 主循环 quit → cleanup）
        proc.terminate()
        try:
            out, _ = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, _ = proc.communicate()
        print("=== 程序输出 ===")
        print(out[-1500:])
        bad = ("Tcl_AsyncDelete" in out
               or "main thread is not in main loop" in out
               or "Exception ignored" in out)
        print("退出含 tkinter 告警:", bad)
        assert not bad, "完整程序退出仍有 tkinter 告警！"
        print("=== 完整程序退出无告警 PASS ===")
    finally:
        if proc.poll() is None:
            proc.kill()


if __name__ == "__main__":
    main()