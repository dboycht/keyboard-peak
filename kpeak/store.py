"""数据模型与持久化：跨会话累积的按键统计，自动落盘 JSON。

内存模型
========
- counts: dict[str, int]          全部历史按键次数（跨会话累计）
- daily:  dict[str, dict[str, int]] 按天累计 {YYYY-MM-DD: {key_id: n}}
- recent: deque[(key_id, ts)]      最近的按键（限长）
- minutes: deque[dict]             每分钟按键数 {t: epoch_minute, n: 次数}（限长）

持久化
======
- 写入 DATA_FILE（JSON），AUTO_SAVE_INTERVAL 秒自动落盘一次；
- 进程退出时由外部（start.py）调用 flush() 强制落盘；
- 启动时自动加载既有文件，实现跨会话长期累积。
"""

from __future__ import annotations

import json
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path

from .config import DATA_FILE, DATA_VERSION, MINUTE_BUCKETS_MAX, RECENT_KEYS_MAX


class KeyStore:
    def __init__(self, data_file: Path | str = DATA_FILE):
        self.data_file = Path(data_file)
        self._lock = threading.RLock()
        self.counts: dict[str, int] = {}
        self.daily: dict[str, dict[str, int]] = {}
        self.recent: deque[tuple[str, int]] = deque(maxlen=RECENT_KEYS_MAX)
        self.minutes: deque[dict] = deque(maxlen=MINUTE_BUCKETS_MAX)
        self._dirty = False
        self._total = 0
        self._paused = False
        self._loaded_at = time.time()
        self._load()

    # ------------------------------------------------------------------
    # 加载 / 保存
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self.data_file.exists():
            return
        try:
            raw = json.loads(self.data_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return  # 文件损坏时静默跳过，重新开始累积
        counts = raw.get("counts") or {}
        daily = raw.get("daily") or {}
        recent = raw.get("recent") or []
        minutes = raw.get("minutes") or []
        self.counts = {k: int(v) for k, v in counts.items() if int(v) > 0}
        self.daily = {
            d: {k: int(v) for k, v in kv.items() if int(v) > 0}
            for d, kv in daily.items()
        }
        self.recent = deque(
            [(k, int(ts)) for k, ts in recent[:RECENT_KEYS_MAX]],
            maxlen=RECENT_KEYS_MAX,
        )
        self.minutes = deque(minutes[-MINUTE_BUCKETS_MAX:], maxlen=MINUTE_BUCKETS_MAX)
        self._total = sum(self.counts.values())
        self._dirty = False

    def flush(self) -> None:
        """原子写入 JSON（先写临时文件再替换）。"""
        with self._lock:
            if not self._dirty:
                return
            payload = {
                "version": DATA_VERSION,
                "total": self._total,
                "counts": self.counts,
                "daily": self.daily,
                "recent": list(self.recent),
                "minutes": list(self.minutes),
                "saved_at": time.time(),
            }
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.data_file.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self.data_file)
            self._dirty = False

    # ------------------------------------------------------------------
    # 记录
    # ------------------------------------------------------------------

    def record(self, key_id: str) -> None:
        """记录一次按键。"""
        with self._lock:
            now = time.time()
            self.counts[key_id] = self.counts.get(key_id, 0) + 1
            day = datetime.now().strftime("%Y-%m-%d")
            self.daily.setdefault(day, {})
            self.daily[day][key_id] = self.daily[day].get(key_id, 0) + 1
            self.recent.append((key_id, now))
            self._total += 1
            self._bump_minute(now)
            self._dirty = True

    def _bump_minute(self, now: float) -> None:
        minute = int(now // 60)
        if self.minutes and self.minutes[-1]["t"] == minute:
            self.minutes[-1]["n"] += 1
        else:
            self.minutes.append({"t": minute, "n": 1})

    # ------------------------------------------------------------------
    # 查询（快照）
    # ------------------------------------------------------------------

    def snapshot(self) -> dict:
        """返回供前端渲染的全量快照。"""
        with self._lock:
            today = datetime.now().strftime("%Y-%m-%d")
            today_counts = dict(self.daily.get(today, {}))
            # 近 60 分钟速率（每分钟按键数，缺失补 0）
            now_minute = int(time.time() // 60)
            minute_map = {m["t"]: m["n"] for m in self.minutes}
            spark = []
            for i in range(minute_map and 59 or 59, -1, -1):
                t = now_minute - i
                spark.append({"t": t, "n": minute_map.get(t, 0)})
            return {
                "total": self._total,
                "paused": self._paused,
                "counts": dict(self.counts),
                "today": today_counts,
                "today_total": sum(today_counts.values()),
                "recent": list(self.recent),
                "spark": spark,
                "loaded_at": self._loaded_at,
            }

    @property
    def total(self) -> int:
        with self._lock:
            return self._total

    def set_paused(self, paused: bool) -> None:
        with self._lock:
            self._paused = bool(paused)

    @property
    def paused(self) -> bool:
        with self._lock:
            return self._paused

    # ------------------------------------------------------------------
    # 导出 / 导入
    # ------------------------------------------------------------------

    def export_data(self) -> dict:
        """导出完整统计数据（用于备份/迁移）。"""
        with self._lock:
            return {
                "app": "keyboard-peak",
                "version": DATA_VERSION,
                "exported_at": time.time(),
                "total": self._total,
                "counts": dict(self.counts),
                "daily": {d: dict(kv) for d, kv in self.daily.items()},
                "recent": list(self.recent),
                "minutes": [dict(m) for m in self.minutes],
            }

    def import_data(self, payload: dict, merge: bool = True) -> dict:
        """导入统计数据。

        merge=True  → 把导入的 counts 累加到现有数据（daily 按天累加）
        merge=False → 覆盖现有数据（以导入内容为准）
        返回 {"ok": bool, "message": str, "imported": int}
        """
        if not isinstance(payload, dict) or "counts" not in payload:
            return {"ok": False, "message": "无效的数据文件：缺少 counts"}
        import_counts = {k: int(v) for k, v in payload.get("counts", {}).items() if int(v) > 0}
        import_daily = payload.get("daily") or {}
        with self._lock:
            if not merge:
                # 覆盖模式
                self.counts = dict(import_counts)
                self.daily = {}
                self.recent = deque(maxlen=RECENT_KEYS_MAX)
                self.minutes = deque(maxlen=MINUTE_BUCKETS_MAX)
                for day, kv in import_daily.items():
                    self.daily[day] = {k: int(v) for k, v in kv.items() if int(v) > 0}
                self._total = sum(self.counts.values())
            else:
                # 合并模式：累加
                for k, v in import_counts.items():
                    self.counts[k] = self.counts.get(k, 0) + v
                for day, kv in import_daily.items():
                    d = self.daily.setdefault(day, {})
                    for k, v in kv.items():
                        d[k] = d.get(k, 0) + int(v)
                self._total = sum(self.counts.values())
            self._dirty = True
        self.flush()
        imported = sum(import_counts.values())
        return {"ok": True, "message": f"导入成功（{'合并' if merge else '覆盖'}，{imported} 次按键）", "imported": imported}