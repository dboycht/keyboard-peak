"""联调测试：验证 HTTP 服务（静态资源 / 快照 / SSE）。"""
import json
import os
import sys
import tempfile
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import urllib.request

from kpeak.store import KeyStore
from kpeak.server import AppServer, EventHub


def check(url, path, expect_type):
    req = urllib.request.Request(url + path)
    resp = urllib.request.urlopen(req, timeout=5)
    body = resp.read()
    ctype = resp.headers.get("Content-Type", "")
    assert expect_type in ctype, f"{path}: type {ctype} != {expect_type}"
    assert len(body) > 0, f"{path}: empty body"
    print(f"OK {path} [{ctype}] {len(body)}B")
    resp.close()


def main():
    with tempfile.TemporaryDirectory() as td:
        data = os.path.join(td, "k.json")
        store = KeyStore(data)
        for _ in range(50):
            store.record("A")
        store.record("ENTER")
        store.flush()

        hub = EventHub()
        server = AppServer(store, hub, port=0)
        server.start()
        url = server.url

        check(url, "/", "text/html")
        check(url, "/static/js/main.js", "javascript")
        check(url, "/static/css/style.css", "text/css")
        check(url, "/static/vendor/three.module.min.js", "javascript")

        snap = json.loads(urllib.request.urlopen(url + "/snapshot", timeout=5).read())
        assert snap["total"] == 51, snap["total"]
        assert snap["counts"]["A"] == 50
        print(f"OK /snapshot total={snap['total']} spark={len(snap['spark'])}")

        # SSE 握手 + 事件
        import http.client
        conn = http.client.HTTPConnection("127.0.0.1", server.port, timeout=8)
        conn.request("GET", "/stream")
        resp = conn.getresponse()
        assert resp.status == 200
        assert "text/event-stream" in resp.getheader("Content-Type", "")
        # 读取 init 事件（含结束空行）
        line1 = resp.readline().decode("utf-8", "replace")
        line2 = resp.readline().decode("utf-8", "replace")
        blank = resp.readline().decode("utf-8", "replace")
        assert "event: init" in line1, line1
        assert '"total": 51' in line2, line2
        assert blank.strip() == "", repr(blank)
        # 推送一个事件并读取（同样含结束空行）
        hub.publish({"key": "B", "ts": 123.0})
        ev = resp.readline().decode("utf-8", "replace")
        assert "event: key" in ev, ev
        data = resp.readline().decode("utf-8", "replace")
        assert '"key": "B"' in data, data
        end = resp.readline().decode("utf-8", "replace")
        assert end.strip() == "", repr(end)
        print("OK /stream SSE init+key")
        conn.close()
        server.stop()
        print("SERVER TEST OK")


if __name__ == "__main__":
    main()