"""1.0.3 全功能集成测试：demo 模式启动 → 快照含新字段 → 设置/通知 → 退出。"""
import json
import os
import subprocess
import sys
import time
import urllib.request


def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(base)
    sys.path.insert(0, base)
    port = "8906"

    proc = subprocess.Popen(
        [sys.executable, "start.py", "--demo", "--no-browser", "--port", port],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    try:
        snap = None
        for _ in range(24):
            try:
                snap = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/snapshot", timeout=2).read())
                break
            except Exception:
                time.sleep(0.5)
        assert snap is not None, "服务未启动"
        print(f"OK 服务启动 total={snap['total']} paused={snap['paused']}")
        assert "paused" in snap, "快照缺 paused 字段"

        time.sleep(2.5)
        assert proc.poll() is None, "进程崩溃（控制窗口/托盘/通知）"
        print("OK 控制窗口+托盘+通知初始化未崩溃")

        # 模拟设置持久化
        from kpeak.settings import Settings
        from kpeak.config import DATA_DIR
        st = Settings(DATA_DIR / "settings.json")
        st.set("notify_enabled", False)
        st2 = Settings(DATA_DIR / "settings.json")
        assert st2.get("notify_enabled") is False
        print("OK 设置持久化")
        os.remove(DATA_DIR / "settings.json")

        proc.terminate()
        proc.wait(timeout=6)
        print("OK 正常终止")
    finally:
        if proc.poll() is None:
            proc.kill()
    print("=== 1.0.3 集成测试 PASS ===")


if __name__ == "__main__":
    main()