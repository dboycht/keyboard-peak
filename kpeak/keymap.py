"""104 键美式键盘布局：物理坐标、显示标签、Windows 虚拟键码(VK) 映射与按键归一化。

设计说明
========
- 键位以「网格单位(u)」描述：1u 的物理间距约 19.05mm（标准键距）。
- 每个键定义为 dict：id（统计用规范 ID）、label（键帽显示）、x/y（左上角网格坐标）、w/h（宽度/高度，单位 u）。
- 布局分区：
    * 主键区（数字行 + 三行字母 + 底部修饰行），总宽 15u
    * 功能键区（Esc/F1-F12/PrtSc/ScrLk/Pause）
    * 数字小键盘区（右置 4u 宽）
- normalize_key(key): 把 pynput 的 key 对象归一化为规范 ID（Windows 优先用 VK，无 VK 时退化用 char/name）。
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# 键位定义（网格坐标：x 向左为正，y 向下为正，单位 u）
# ---------------------------------------------------------------------------

# 功能键区 (y=0)
FUNCTION_KEYS = [
    # id, label, x, y, w, h
    ("ESC", "Esc", 0.00, 0, 1.0, 1.0),
    ("F1", "F1", 1.50, 0, 1.0, 1.0),
    ("F2", "F2", 2.50, 0, 1.0, 1.0),
    ("F3", "F3", 3.50, 0, 1.0, 1.0),
    ("F4", "F4", 4.50, 0, 1.0, 1.0),
    ("F5", "F5", 5.50, 0, 1.0, 1.0),
    ("F6", "F6", 6.50, 0, 1.0, 1.0),
    ("F7", "F7", 7.50, 0, 1.0, 1.0),
    ("F8", "F8", 8.50, 0, 1.0, 1.0),
    ("F9", "F9", 9.50, 0, 1.0, 1.0),
    ("F10", "F10", 10.50, 0, 1.0, 1.0),
    ("F11", "F11", 11.50, 0, 1.0, 1.0),
    ("F12", "F12", 12.50, 0, 1.0, 1.0),
    ("PRTSC", "PrtSc", 14.00, 0, 1.0, 1.0),
    ("SCRLK", "ScrLk", 15.00, 0, 1.0, 1.0),
    ("PAUSE", "Pause", 16.00, 0, 1.0, 1.0),
]

# 主键区 (y=1..5)，总宽 15u
MAIN_KEYS = [
    # ---- 数字行 (y=1) ----
    ("GRAVE", "`", 0.00, 1, 1.0, 1.0),
    ("1", "1", 1.00, 1, 1.0, 1.0),
    ("2", "2", 2.00, 1, 1.0, 1.0),
    ("3", "3", 3.00, 1, 1.0, 1.0),
    ("4", "4", 4.00, 1, 1.0, 1.0),
    ("5", "5", 5.00, 1, 1.0, 1.0),
    ("6", "6", 6.00, 1, 1.0, 1.0),
    ("7", "7", 7.00, 1, 1.0, 1.0),
    ("8", "8", 8.00, 1, 1.0, 1.0),
    ("9", "9", 9.00, 1, 1.0, 1.0),
    ("0", "0", 10.00, 1, 1.0, 1.0),
    ("MINUS", "-", 11.00, 1, 1.0, 1.0),
    ("EQUAL", "=", 12.00, 1, 1.0, 1.0),
    ("BACKSPACE", "⌫", 13.00, 1, 2.0, 1.0),
    # ---- 字母行 QWERTY (y=2) ----
    ("TAB", "Tab", 0.00, 2, 1.5, 1.0),
    ("Q", "Q", 1.50, 2, 1.0, 1.0),
    ("W", "W", 2.50, 2, 1.0, 1.0),
    ("E", "E", 3.50, 2, 1.0, 1.0),
    ("R", "R", 4.50, 2, 1.0, 1.0),
    ("T", "T", 5.50, 2, 1.0, 1.0),
    ("Y", "Y", 6.50, 2, 1.0, 1.0),
    ("U", "U", 7.50, 2, 1.0, 1.0),
    ("I", "I", 8.50, 2, 1.0, 1.0),
    ("O", "O", 9.50, 2, 1.0, 1.0),
    ("P", "P", 10.50, 2, 1.0, 1.0),
    ("LBRACKET", "[", 11.50, 2, 1.0, 1.0),
    ("RBRACKET", "]", 12.50, 2, 1.0, 1.0),
    ("BACKSLASH", "\\", 13.50, 2, 1.5, 1.0),
    # ---- 字母行 ASDF (y=3) ----
    ("CAPSLOCK", "Caps", 0.00, 3, 1.75, 1.0),
    ("A", "A", 1.75, 3, 1.0, 1.0),
    ("S", "S", 2.75, 3, 1.0, 1.0),
    ("D", "D", 3.75, 3, 1.0, 1.0),
    ("F", "F", 4.75, 3, 1.0, 1.0),
    ("G", "G", 5.75, 3, 1.0, 1.0),
    ("H", "H", 6.75, 3, 1.0, 1.0),
    ("J", "J", 7.75, 3, 1.0, 1.0),
    ("K", "K", 8.75, 3, 1.0, 1.0),
    ("L", "L", 9.75, 3, 1.0, 1.0),
    ("SEMICOLON", ";", 10.75, 3, 1.0, 1.0),
    ("QUOTE", "'", 11.75, 3, 1.0, 1.0),
    ("ENTER", "⏎", 12.75, 3, 2.25, 1.0),
    # ---- 字母行 ZXCV (y=4) ----
    ("LSHIFT", "⇧", 0.00, 4, 2.25, 1.0),
    ("Z", "Z", 2.25, 4, 1.0, 1.0),
    ("X", "X", 3.25, 4, 1.0, 1.0),
    ("C", "C", 4.25, 4, 1.0, 1.0),
    ("V", "V", 5.25, 4, 1.0, 1.0),
    ("B", "B", 6.25, 4, 1.0, 1.0),
    ("N", "N", 7.25, 4, 1.0, 1.0),
    ("M", "M", 8.25, 4, 1.0, 1.0),
    ("COMMA", ",", 9.25, 4, 1.0, 1.0),
    ("PERIOD", ".", 10.25, 4, 1.0, 1.0),
    ("SLASH", "/", 11.25, 4, 1.0, 1.0),
    ("RSHIFT", "⇧", 12.25, 4, 2.75, 1.0),
    # ---- 底部修饰行 (y=5) ----
    ("LCTRL", "Ctrl", 0.00, 5, 1.25, 1.0),
    ("LWIN", "Win", 1.25, 5, 1.25, 1.0),
    ("LALT", "Alt", 2.50, 5, 1.25, 1.0),
    ("SPACE", "␣", 3.75, 5, 6.25, 1.0),
    ("RALT", "Alt", 10.00, 5, 1.25, 1.0),
    ("RWIN", "Win", 11.25, 5, 1.25, 1.0),
    ("MENU", "☰", 12.50, 5, 1.25, 1.0),
    ("RCTRL", "Ctrl", 13.75, 5, 1.25, 1.0),
]

# 数字小键盘区 (右置，x 从 19 开始，宽 4u，y 与主区对齐)
NUMPAD_KEYS = [
    ("NUMLOCK", "Num", 19.00, 1, 1.0, 1.0),
    ("NUMPAD_DIVIDE", "/", 20.00, 1, 1.0, 1.0),
    ("NUMPAD_MULTIPLY", "*", 21.00, 1, 1.0, 1.0),
    ("NUMPAD_SUBTRACT", "-", 22.00, 1, 1.0, 1.0),
    ("NUMPAD_7", "7", 19.00, 2, 1.0, 1.0),
    ("NUMPAD_8", "8", 20.00, 2, 1.0, 1.0),
    ("NUMPAD_9", "9", 21.00, 2, 1.0, 1.0),
    ("NUMPAD_ADD", "+", 22.00, 2, 1.0, 2.0),  # 加号占两行高
    ("NUMPAD_4", "4", 19.00, 3, 1.0, 1.0),
    ("NUMPAD_5", "5", 20.00, 3, 1.0, 1.0),
    ("NUMPAD_6", "6", 21.00, 3, 1.0, 1.0),
    ("NUMPAD_1", "1", 19.00, 4, 1.0, 1.0),
    ("NUMPAD_2", "2", 20.00, 4, 1.0, 1.0),
    ("NUMPAD_3", "3", 21.00, 4, 1.0, 1.0),
    ("NUMPAD_ENTER", "⏎", 22.00, 4, 1.0, 2.0),  # 小键盘回车占两行高
    ("NUMPAD_0", "0", 19.00, 5, 2.0, 1.0),
    ("NUMPAD_DECIMAL", ".", 21.00, 5, 1.0, 1.0),
]

# 导航编辑键区（主键区与小键盘之间）
NAV_KEYS = [
    ("INSERT", "Ins", 16.00, 1, 1.0, 1.0),
    ("HOME", "Home", 16.00, 2, 1.0, 1.0),
    ("PAGEUP", "PgUp", 16.00, 3, 1.0, 1.0),
    ("DELETE", "Del", 17.00, 1, 1.0, 1.0),
    ("END", "End", 17.00, 2, 1.0, 1.0),
    ("PAGEDOWN", "PgDn", 17.00, 3, 1.0, 1.0),
    # 方向键（倒 T 布局）
    ("UP", "↑", 17.00, 4, 1.0, 1.0),
    ("DOWN", "↓", 17.00, 5, 1.0, 1.0),
    ("LEFT", "←", 16.00, 5, 1.0, 1.0),
    ("RIGHT", "→", 18.00, 5, 1.0, 1.0),
]

ALL_KEYS = FUNCTION_KEYS + MAIN_KEYS + NUMPAD_KEYS + NAV_KEYS

# 总网格范围（用于 3D 居中）
GRID_MIN_X = 0.0
GRID_MAX_X = 23.0
GRID_MIN_Y = 0.0
GRID_MAX_Y = 6.0

# 网格中心（网格坐标系中心，用于把网格坐标映射到世界坐标）
GRID_CENTER_X = (GRID_MIN_X + GRID_MAX_X) / 2.0  # 11.5
GRID_CENTER_Y = (GRID_MIN_Y + GRID_MAX_Y) / 2.0  # 3.0


def key_defs() -> list[dict]:
    """返回完整键位定义列表（id / label / x / y / w / h / key)。"""
    out = []
    for kid, label, x, y, w, h in ALL_KEYS:
        out.append({
            "id": kid,
            "label": label,
            "x": float(x),
            "y": float(y),
            "w": float(w),
            "h": float(h),
        })
    return out


# ---------------------------------------------------------------------------
# 规范 ID → 键位定义 索引
# ---------------------------------------------------------------------------

_ID_TO_DEF: dict[str, dict] = {d["id"]: d for d in key_defs()}


def get_key_def(key_id: str) -> dict | None:
    return _ID_TO_DEF.get(key_id)


def all_key_ids() -> list[str]:
    return [d["id"] for d in key_defs()]


# ---------------------------------------------------------------------------
# Windows 虚拟键码(VK) → 规范 ID
# 参考：https://learn.microsoft.com/en-us/windows/win32/inputdev/virtual-key-codes
# ---------------------------------------------------------------------------

_VK_TO_ID: dict[int, str] = {}


def _add_vk(vk: int, key_id: str) -> None:
    _VK_TO_ID[vk] = key_id


# 字母 A-Z：0x41-0x5A
for _i in range(26):
    _add_vk(0x41 + _i, chr(ord("A") + _i))
# 数字行 1-0：0x31-0x39, 0x30
for _i in range(1, 10):
    _add_vk(0x30 + _i, str(_i))
_add_vk(0x30, "0")

# 标点（OEM）
_add_vk(0xC0, "GRAVE")        # `~
_add_vk(0xBD, "MINUS")        # -_
_add_vk(0xBB, "EQUAL")        # =+
_add_vk(0xDB, "LBRACKET")     # [{
_add_vk(0xDD, "RBRACKET")     # ]}
_add_vk(0xDC, "BACKSLASH")    # \|
_add_vk(0xBA, "SEMICOLON")    # ;:
_add_vk(0xDE, "QUOTE")        # '"
_add_vk(0xBC, "COMMA")        # ,<
_add_vk(0xBE, "PERIOD")       # .>
_add_vk(0xBF, "SLASH")        # /?

# 控制/导航键
_add_vk(0x08, "BACKSPACE")
_add_vk(0x09, "TAB")
_add_vk(0x0D, "ENTER")
_add_vk(0x1B, "ESC")
_add_vk(0x20, "SPACE")
_add_vk(0x14, "CAPSLOCK")
_add_vk(0x2C, "PRTSC")
_add_vk(0x91, "SCRLK")
_add_vk(0x13, "PAUSE")
_add_vk(0x2D, "INSERT")
_add_vk(0x2E, "DELETE")
_add_vk(0x24, "HOME")
_add_vk(0x23, "END")
_add_vk(0x21, "PAGEUP")
_add_vk(0x22, "PAGEDOWN")
_add_vk(0x25, "LEFT")
_add_vk(0x26, "UP")
_add_vk(0x27, "RIGHT")
_add_vk(0x28, "DOWN")
_add_vk(0x90, "NUMLOCK")

# 修饰键（左右）
_add_vk(0xA0, "LSHIFT")
_add_vk(0xA1, "RSHIFT")
_add_vk(0xA2, "LCTRL")
_add_vk(0xA3, "RCTRL")
_add_vk(0xA4, "LALT")
_add_vk(0xA5, "RALT")
_add_vk(0x5B, "LWIN")
_add_vk(0x5C, "RWIN")
_add_vk(0x5D, "MENU")

# 通用修饰键（某些键盘/驱动只报通用码）
_add_vk(0x10, "LSHIFT")       # Shift（默认按左算）
_add_vk(0x11, "LCTRL")        # Ctrl
_add_vk(0x12, "LALT")         # Alt

# 功能键 F1-F12：0x70-0x7B
for _i in range(12):
    _add_vk(0x70 + _i, f"F{_i + 1}")

# 数字小键盘：0x60-0x69（与 NumLock 状态无关，物理按键恒定）
for _i in range(10):
    _add_vk(0x60 + _i, f"NUMPAD_{_i}")
_add_vk(0x6A, "NUMPAD_MULTIPLY")
_add_vk(0x6B, "NUMPAD_ADD")
_add_vk(0x6D, "NUMPAD_SUBTRACT")
_add_vk(0x6E, "NUMPAD_DECIMAL")
_add_vk(0x6F, "NUMPAD_DIVIDE")


def vk_to_id(vk: int) -> str | None:
    """把 Windows 虚拟键码映射为规范 ID；未知键返回 None。"""
    return _VK_TO_ID.get(vk)


# ---------------------------------------------------------------------------
# 非 Windows 平台退化映射：pynput Key.name / KeyCode.char → 规范 ID
# ---------------------------------------------------------------------------

_SPECIAL_NAME_TO_ID = {
    "esc": "ESC",
    "tab": "TAB",
    "enter": "ENTER",
    "space": "SPACE",
    "backspace": "BACKSPACE",
    "caps_lock": "CAPSLOCK",
    "delete": "DELETE",
    "insert": "INSERT",
    "home": "HOME",
    "end": "END",
    "page_up": "PAGEUP",
    "page_down": "PAGEDOWN",
    "left": "LEFT",
    "up": "UP",
    "right": "RIGHT",
    "down": "DOWN",
    "print_screen": "PRTSC",
    "scroll_lock": "SCRLK",
    "pause": "PAUSE",
    "num_lock": "NUMLOCK",
    "shift": "LSHIFT",
    "shift_r": "RSHIFT",
    "ctrl": "LCTRL",
    "ctrl_r": "RCTRL",
    "alt": "LALT",
    "alt_r": "RALT",
    "alt_gr": "RALT",
    "cmd": "LWIN",
    "cmd_r": "RWIN",
    "menu": "MENU",
    "media_previous": None,  # 多媒体键不在 104 布局内
    "media_next": None,
    "media_play_pause": None,
    "media_volume_down": None,
    "media_volume_up": None,
    "media_volume_mute": None,
}
for _i in range(12):
    _SPECIAL_NAME_TO_ID[f"f{_i + 1}"] = f"F{_i + 1}"

_CHAR_TO_ID = {
    "a": "A", "b": "B", "c": "C", "d": "D", "e": "E", "f": "F", "g": "G",
    "h": "H", "i": "I", "j": "J", "k": "K", "l": "L", "m": "M", "n": "N",
    "o": "O", "p": "P", "q": "Q", "r": "R", "s": "S", "t": "T", "u": "U",
    "v": "V", "w": "W", "x": "X", "y": "Y", "z": "Z",
    "1": "1", "2": "2", "3": "3", "4": "4", "5": "5",
    "6": "6", "7": "7", "8": "8", "9": "9", "0": "0",
    "`": "GRAVE", "-": "MINUS", "=": "EQUAL", "[": "LBRACKET",
    "]": "RBRACKET", "\\": "BACKSLASH", ";": "SEMICOLON", "'": "QUOTE",
    ",": "COMMA", ".": "PERIOD", "/": "SLASH",
}


def normalize_key(key) -> str | None:
    """把 pynput key 对象归一化为规范 ID。

    Windows：优先使用 vk（物理键恒定，不受 Shift 影响）。
    其他平台：退化到 Key.name / KeyCode.char。
    """
    vk = getattr(key, "vk", None)
    if isinstance(vk, int):
        kid = _VK_TO_ID.get(vk)
        if kid:
            return kid
    # 退化：特殊键 name
    name = getattr(key, "name", None)
    if name:
        kid = _SPECIAL_NAME_TO_ID.get(name.lower())
        if kid:
            return kid
    # 退化：可打印字符
    char = getattr(key, "char", None)
    if char:
        kid = _CHAR_TO_ID.get(char.lower())
        if kid:
            return kid
    return None