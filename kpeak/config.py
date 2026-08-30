"""keyboard-peak 全局配置。"""

from pathlib import Path

# 项目根目录（kpeak 的上一级）
ROOT = Path(__file__).resolve().parent.parent

# 数据目录与文件（运行时生成，不入库）
DATA_DIR = ROOT / "data"
DATA_FILE = DATA_DIR / "keylog.json"

# Web 静态资源目录
WEB_DIR = ROOT / "web"

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