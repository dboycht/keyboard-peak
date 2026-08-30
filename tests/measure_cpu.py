"""精确测量优化后稳定期 idle CPU（20 秒采样，剔除启动期）。"""
import os
import subprocess
import sys
import time


def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    port = "8922"
    proc = subprocess.Popen(
        [sys.executable, "start.py", "--no-browser", "--port", port],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=base,
    )
    try:
        time.sleep(10)  # 等完全稳定
        import psutil
        p = psutil.Process(proc.pid)
        samples = []
        for _ in range(40):  # 20 秒
            samples.append(p.cpu_percent(interval=0.5))
        avg = sum(samples) / len(samples)
        p95 = sorted(samples)[int(len(samples) * 0.95)]
        print(f"稳定期 idle CPU: 平均 {avg:.2f}%  中位 {sorted(samples)[len(samples)//2]:.2f}%  95分位 {p95:.2f}%  峰值 {max(samples):.2f}%")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    main()