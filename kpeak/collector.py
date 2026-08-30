"""全局键盘监听：pynput 钩子 → 归一化 → KeyStore → SSE 广播。

- 使用 pynput.keyboard.Listener（低层挂钩，全系统生效，即使焦点在其他窗口）。
- on_press 回调通过 keymap.normalize_key 归一化，忽略无法识别的键与自动重复。
"""

from __future__ import annotations

import logging
import threading

from pynput import keyboard

from .keymap import normalize_key

log = logging.getLogger("kpeak.collector")


class KeyCollector:
    def __init__(self, store, on_key=None):
        """store: KeyStore；on_key: 可选回调，收到新按键时调用 on_key(key_id)。"""
        self.store = store
        self.on_key = on_key
        self._listener: keyboard.Listener | None = None
        self._running = threading.Event()
        self._paused = False
        self._pause_lock = threading.Lock()

    # ------------------------------------------------------------------

    def _on_press(self, key) -> None:
        if self._paused:
            return  # 暂停采集：跳过记录与推送
        key_id = normalize_key(key)
        if key_id is None:
            return
        try:
            self.store.record(key_id)
        except Exception:  # 记录失败不应影响监听
            log.exception("record failed for %r", key)
        if self.on_key is not None:
            try:
                self.on_key(key_id)
            except Exception:
                log.exception("on_key callback failed")

    def set_paused(self, paused: bool) -> bool:
        """暂停/恢复采集。返回切换后的状态。"""
        with self._pause_lock:
            self._paused = bool(paused)
            self.store.set_paused(self._paused)
            return self._paused

    @property
    def paused(self) -> bool:
        return self._paused

    def start(self) -> None:
        """启动全局监听（阻塞线程内运行）。"""
        self._running.set()
        self._listener = keyboard.Listener(on_press=self._on_press)
        self._listener.daemon = True
        self._listener.start()
        log.info("keyboard listener started")

    def stop(self) -> None:
        self._running.clear()
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
        log.info("keyboard listener stopped")

    @property
    def running(self) -> bool:
        return self._running.is_set()