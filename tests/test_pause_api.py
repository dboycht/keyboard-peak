"""测试：/api/pause-toggle 暂停接口。"""
import http.client
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kpeak.server import AppServer, EventHub, AppHandler
from kpeak.store import KeyStore

state = {"paused": False}


def toggle():
    state["paused"] = not state["paused"]
    return state["paused"]


def main():
    AppHandler.pause_callback = staticmethod(toggle)
    with tempfile.TemporaryDirectory() as td:
        store = KeyStore(os.path.join(td, "k.json"))
        store.record("A")
        hub = EventHub()
        srv = AppServer(store, hub, port=0)
        srv.start()

        conn = http.client.HTTPConnection("127.0.0.1", srv.port, timeout=5)
        conn.request("POST", "/api/pause-toggle", body=b"")
        resp = conn.getresponse()
        data = resp.read().decode()
        print("1st:", resp.status, data)
        assert resp.status == 200 and '"paused": true' in data, data
        conn.close()

        conn = http.client.HTTPConnection("127.0.0.1", srv.port, timeout=5)
        conn.request("POST", "/api/pause-toggle", body=b"")
        resp2 = conn.getresponse()
        data2 = resp2.read().decode()
        print("2nd:", resp2.status, data2)
        assert '"paused": false' in data2, data2
        conn.close()

        # 快照应反映暂停状态
        import urllib.request, json
        snap = json.loads(urllib.request.urlopen(srv.url + "/snapshot", timeout=5).read())
        print("snapshot paused:", snap["paused"])
        assert snap["paused"] is False
        srv.stop()
        print("=== pause-toggle PASS ===")


if __name__ == "__main__":
    main()