"""HTTP 服务：静态资源 + SSE 实时事件流 + 快照接口。

路由
====
- GET /               → web/index.html
- GET /static/*       → web/ 下静态资源（.js/.css 等）
- GET /snapshot       → 全量统计数据 JSON
- GET /stream         → SSE 事件流（实时按键事件）
"""

from __future__ import annotations

import json
import logging
import mimetypes
import queue as queue_mod
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .config import WEB_DIR

log = logging.getLogger("kpeak.server")

SSE_KEEPALIVE = 15.0  # 秒；SSE 心跳间隔


class EventHub:
    """进程内广播：把按键事件推送给所有 SSE 订阅者。"""

    def __init__(self):
        self._subscribers: set[queue_mod.Queue] = set()
        self._lock = threading.Lock()

    def subscribe(self) -> queue_mod.Queue:
        q: queue_mod.Queue = queue_mod.Queue(maxsize=1024)
        with self._lock:
            self._subscribers.add(q)
        return q

    def unsubscribe(self, q: queue_mod.Queue) -> None:
        with self._lock:
            self._subscribers.discard(q)

    def publish(self, event: dict) -> None:
        payload = json.dumps(event, ensure_ascii=False)
        with self._lock:
            subs = list(self._subscribers)
        dead = []
        for q in subs:
            try:
                q.put_nowait(payload)
            except queue_mod.Full:
                dead.append(q)  # 慢消费者：丢弃
        for q in dead:
            with self._lock:
                self._subscribers.discard(q)


class AppHandler(BaseHTTPRequestHandler):
    server_version = "keyboard-peak/1.0"
    protocol_version = "HTTP/1.1"

    # 静默访问日志（避免 stderr 噪声）
    def log_message(self, fmt, *args):
        pass

    # 注入（由 Server 在实例化前设置）
    store = None
    hub: EventHub | None = None
    web_dir: Path = WEB_DIR

    # ------------------------------------------------------------------
    # 连接异常静默处理
    # ------------------------------------------------------------------

    def handle_one_request(self):
        """覆盖：读取请求行阶段的连接异常（浏览器关页/断线）视为正常，不打印 traceback。"""
        try:
            super().handle_one_request()
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            # 客户端主动断开（关闭标签页/刷新/杀进程）——正常现象，静默忽略
            pass

    # ------------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------------

    def _send_json(self, obj: dict, status: int = 200) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, rel_path: str) -> None:
        """只允许 web 目录内的文件。"""
        root = self.web_dir.resolve()
        target = (root / rel_path).resolve()
        if not str(target).startswith(str(root)):
            self.send_error(403, "Forbidden")
            return
        if not target.is_file():
            self.send_error(404, "Not Found")
            return
        mime, _ = mimetypes.guess_type(str(target))
        ctype = mime or "application/octet-stream"
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    # ------------------------------------------------------------------
    # 路由
    # ------------------------------------------------------------------

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        try:
            if path in ("/", "/index.html"):
                self._send_file("index.html")
            elif path == "/snapshot":
                if self.store is None:
                    self._send_json({"error": "store unavailable"}, 500)
                else:
                    self._send_json(self.store.snapshot())
            elif path == "/stream":
                self._handle_sse()
            elif path.startswith("/static/"):
                self._send_file(path[len("/static/"):])
            else:
                self.send_error(404, "Not Found")
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _handle_sse(self) -> None:
        if self.hub is None:
            self.send_error(500)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        q = self.hub.subscribe()
        log.info("SSE client connected: %s", self.client_address)
        try:
            # 初始化事件：建立连接后立即推送当前快照
            self.wfile.write(f"event: init\ndata: {json.dumps(self.store.snapshot(), ensure_ascii=False)}\n\n".encode("utf-8"))
            self.wfile.flush()
            last_beat = time.time()
            while True:
                try:
                    payload = q.get(timeout=1.0)
                    self.wfile.write(f"event: key\ndata: {payload}\n\n".encode("utf-8"))
                    self.wfile.flush()
                except queue_mod.Empty:
                    now = time.time()
                    if now - last_beat >= SSE_KEEPALIVE:
                        self.wfile.write(": keepalive\n\n".encode("utf-8"))
                        self.wfile.flush()
                        last_beat = now
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            self.hub.unsubscribe(q)
            log.info("SSE client disconnected: %s", self.client_address)


class AppServer:
    def __init__(self, store, hub: EventHub, port: int, host: str = "127.0.0.1"):
        self.store = store
        self.hub = hub
        AppHandler.store = store
        AppHandler.hub = hub
        self.httpd = ThreadingHTTPServer((host, port), AppHandler)
        self.port = self.httpd.server_address[1]
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self._thread.start()
        log.info("HTTP server on http://%s:%s", self.httpd.server_address[0], self.port)

    def stop(self) -> None:
        try:
            self.httpd.shutdown()
        except Exception:
            pass

    @property
    def url(self) -> str:
        addr = self.httpd.server_address
        return f"http://{addr[0]}:{addr[1]}"