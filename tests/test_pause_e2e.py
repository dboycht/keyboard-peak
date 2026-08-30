"""端到端：demo 模式下网页暂停生效（暂停后 total 不再增长）。"""
import json
import os
import subprocess
import sys
import time
import urllib.request


def get(url):
    return json.loads(urllib.request.urlopen(url, timeout=5).read())


def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    port = "8912"
    proc = subprocess.Popen(
        [sys.executable, "start.py", "--demo", "--no-browser", "--port", port],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=base,
    )
    try:
        base_url = f"http://127.0.0.1:{port}"
        for _ in range(24):
            try:
                get(base_url + "/snapshot")
                break
            except Exception:
                time.sleep(0.5)

        # 记录基准
        t0 = get(base_url + "/snapshot")["total"]
        time.sleep(2.0)
        t1 = get(base_url + "/snapshot")["total"]
        assert t1 > t0, f"demo 未增长 {t0}->{t1}"
        print(f"OK demo 运行中 total {t0} -> {t1}")

        # 暂停
        req = urllib.request.Request(base_url + "/api/pause-toggle", method="POST", data=b"")
        resp = json.loads(urllib.request.urlopen(req, timeout=5).read())
        assert resp["paused"] is True, resp
        print("OK 已暂停:", resp)

        # 暂停后 2 秒 total 应基本不变
        p0 = get(base_url + "/snapshot")["total"]
        time.sleep(2.0)
        p1 = get(base_url + "/snapshot")["total"]
        assert p1 == p0, f"暂停后仍增长 {p0}->{p1}"
        print(f"OK 暂停生效 total 稳定 {p0}")

        # 恢复
        req = urllib.request.Request(base_url + "/api/pause-toggle", method="POST", data=b"")
        resp2 = json.loads(urllib.request.urlopen(req, timeout=5).read())
        assert resp2["paused"] is False
        time.sleep(1.5)
        r1 = get(base_url + "/snapshot")["total"]
        assert r1 > p1, f"恢复后未增长 {p1}->{r1}"
        print(f"OK 恢复生效 total {p1} -> {r1}")

        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("=== demo 暂停端到端 PASS ===")
    finally:
        if proc.poll() is None:
            proc.kill()


if __name__ == "__main__":
    main()