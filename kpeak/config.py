"""keyboard-peak 全局配置。

兼容两种运行形态：
1. 源码运行（开发）：数据在项目根 data/，web 资产在项目根 web/。
2. PyInstaller / frozen 打包：web 资产在解压临时目录 sys._MEIPASS/web，
   数据必须落在持久位置 %LOCALAPPDATA%/keyboard-peak（否则退出即丢，跨会话累积失效）。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

FROZEN = bool(getattr(sys, "frozen", False))


def _web_dir() -> Path:
    """Web 静态资源目录（打包后位于解压临时目录）。"""
    if FROZEN:
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        return base / "web"
    return Path(__file__).resolve().parent.parent / "web"


def _data_dir() -> Path:
    """数据目录：打包后禁用 _MEIPASS（临时、会丢），改用用户数据目录。"""
    if FROZEN:
        local = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
        return Path(local) / "keyboard-peak"
    return Path(__file__).resolve().parent.parent / "data"


# Web 静态资源目录
WEB_DIR = _web_dir()

# 数据目录与文件（运行时生成，不入库）
DATA_DIR = _data_dir()
DATA_FILE = DATA_DIR / "keylog.json"

# HTTP 服务
DEFAULT_PORT = 8765
HOST = "127.0.0.1"

# 持久化：每 N 秒自动落盘一次（退出时还会强制落盘）
AUTO_SAVE_INTERVAL = 5.0

# 统计窗口
RECENT_KEYS_MAX = 60            # 最近按键记录条数
MINUTE_BUCKETS_MAX = 80         # 每分钟计数桶保留数量（约 80 分钟趋势）

# JSON 文件结构版本
DATA_VERSION = 1