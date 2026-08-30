"""应用设置（持久化到数据目录 settings.json）。

当前设置项
==========
- notify_enabled: bool   右下角通知开关（启动/退出/每日等通知推送）
- notify_daily: bool     每日统计摘要通知
- bar_mode: str          网页显示模式（'classic' 经典柱状 / 'cover' 覆盖式柱体）；前端也会自己存 localStorage，
                         这里存「应用默认模式」供启动时同步
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

from .config import DATA_DIR

DEFAULT_SETTINGS = {
    "notify_enabled": True,   # 通知总开关
    "notify_daily": False,    # 每日统计摘要（默认关，避免打扰）
    "bar_mode": "classic",    # 默认经典柱状
}


class Settings:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else DATA_DIR / "settings.json"
        self._lock = threading.RLock()
        self._data = dict(DEFAULT_SETTINGS)
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                self._data.update({k: raw[k] for k in DEFAULT_SETTINGS if k in raw})
        except (OSError, json.JSONDecodeError):
            pass

    def save(self) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self.path)

    def get(self, key: str, default=None):
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        with self._lock:
            self._data[key] = value
        self.save()

    def all(self) -> dict:
        with self._lock:
            return dict(self._data)