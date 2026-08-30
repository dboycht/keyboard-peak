"""联调测试：验证 pynput 全局钩子能捕获注入的真实按键。"""
import sys
import tempfile
import time
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kpeak.store import KeyStore
from kpeak.collector import KeyCollector
from pynput import keyboard


def main():
    with tempfile.TemporaryDirectory() as td:
        data = os.path.join(td, "t.json")
        store = KeyStore(data)
        col = KeyCollector(store)
        col.start()
        time.sleep(0.5)

        controller = keyboard.Controller()
        for key in ["p", "y", "n", "u", "t", "p", " "]:
            controller.press(key)
            controller.release(key)
            time.sleep(0.06)
        time.sleep(0.8)
        col.stop()

        print("recorded:", dict(store.counts))
        print("total:", store.total)
        assert store.counts.get("P", 0) >= 2, "P 键未被捕获"
        assert store.counts.get("SPACE", 0) >= 1, "空格未被捕获"
        print("LISTENER OK: 真实按键被全局钩子捕获")


if __name__ == "__main__":
    main()