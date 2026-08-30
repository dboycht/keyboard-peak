"""测试：控制窗口完整生命周期退出时无 tkinter 告警。"""
import os
import subprocess
import sys


def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    code = """
import sys, time
sys.path.insert(0, {base!r})
from kpeak.window import ControlWindow
win = ControlWindow(
    get_snapshot=lambda: {{"total": 1, "today_total": 1, "rate": 0,
                          "mode": "t", "url": "http://x", "data": "d"}},
    settings=None,
)
win.start()
time.sleep(2.0)
win.stop()
time.sleep(0.5)
print("WINDOW LIFECYCLE OK")
""".format(base=base)
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=30)
    out = r.stdout.strip()
    err = r.stderr.strip()
    print("stdout:", out)
    bad = ("Tcl_AsyncDelete" in err
           or "main thread is not in main loop" in err
           or "Exception ignored" in err)
    print("stderr 含 tkinter 告警:", bad)
    if err:
        print("stderr 前 600 字:")
        print(err[:600])
    assert not bad, "退出仍有 tkinter 告警！"
    print("=== 退出无告警 PASS ===")


if __name__ == "__main__":
    main()