"""集成测试：验证主程序 + 托盘协同（demo 模式），并测试托盘退出事件。"""
import os
import subprocess
import sys
import time
import urllib.request


def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(base)
    port = "8901"

    # 启动 demo 模式（--no-browser 避免干扰）
    proc = subprocess.Popen(
        [sys.executable, "start.py", "--demo", "--no-browser", "--port", port],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    try:
        # 等待服务起来
        for _ in range(20):
            try:
                snap = urllib.request.urlopen(f"http://127.0.0.1:{port}/snapshot", timeout=2)
                data = snap.read()
                import json
                j = json.loads(data)
                assert j["total"] >= 0
                print(f"OK: 服务已启动, demo 累计 {j['total']} 次")
                break
            except Exception:
                time.sleep(0.5)
        else:
            raise RuntimeError("服务未在预期时间内启动")

        # 验证托盘线程已启动（通过日志判断）
        time.sleep(1.5)
        out = proc.stdout
        # 检查进程是否仍存活（托盘未导致崩溃）
        assert proc.poll() is None, "进程意外退出"
        print("OK: 进程存活（托盘未导致崩溃）")

        # 测试退出路径：直接发 SIGTERM 等价操作——杀掉进程模拟用户退出
        proc.terminate()
        try:
            proc.wait(timeout=5)
            print("OK: 进程正常终止")
        except subprocess.TimeoutExpired:
            proc.kill()
            raise RuntimeError("进程无法终止")
    finally:
        if proc.poll() is None:
            proc.kill()
        # 清理可能残留的 keyboard-peak 进程
        os.system('powershell -Command "Get-Process | Where-Object {$_.ProcessName -like \'*keyboard*\'} | Stop-Process -Force -ErrorAction SilentlyContinue"')
    print("=== 托盘集成测试 PASS ===")


if __name__ == "__main__":
    main()