/* ==========================================================================
 * data.js — 键盘布局与数学工具（与后端正交的常量副本，供前端独立渲染）
 * ========================================================================== */

// 键位定义：id / label / x / y / w / h（网格单位 u）
export const KEYS = [
  // ---- 功能键区 (y=0) ----
  { id: 'ESC', label: 'Esc', x: 0.0, y: 0, w: 1.0, h: 1.0 },
  { id: 'F1', label: 'F1', x: 1.5, y: 0, w: 1.0, h: 1.0 },
  { id: 'F2', label: 'F2', x: 2.5, y: 0, w: 1.0, h: 1.0 },
  { id: 'F3', label: 'F3', x: 3.5, y: 0, w: 1.0, h: 1.0 },
  { id: 'F4', label: 'F4', x: 4.5, y: 0, w: 1.0, h: 1.0 },
  { id: 'F5', label: 'F5', x: 5.5, y: 0, w: 1.0, h: 1.0 },
  { id: 'F6', label: 'F6', x: 6.5, y: 0, w: 1.0, h: 1.0 },
  { id: 'F7', label: 'F7', x: 7.5, y: 0, w: 1.0, h: 1.0 },
  { id: 'F8', label: 'F8', x: 8.5, y: 0, w: 1.0, h: 1.0 },
  { id: 'F9', label: 'F9', x: 9.5, y: 0, w: 1.0, h: 1.0 },
  { id: 'F10', label: 'F10', x: 10.5, y: 0, w: 1.0, h: 1.0 },
  { id: 'F11', label: 'F11', x: 11.5, y: 0, w: 1.0, h: 1.0 },
  { id: 'F12', label: 'F12', x: 12.5, y: 0, w: 1.0, h: 1.0 },
  { id: 'PRTSC', label: 'PrtSc', x: 14.0, y: 0, w: 1.0, h: 1.0 },
  { id: 'SCRLK', label: 'ScrLk', x: 15.0, y: 0, w: 1.0, h: 1.0 },
  { id: 'PAUSE', label: 'Pause', x: 16.0, y: 0, w: 1.0, h: 1.0 },

  // ---- 数字行 (y=1) ----
  { id: 'GRAVE', label: '`', x: 0.0, y: 1, w: 1.0, h: 1.0 },
  { id: '1', label: '1', x: 1.0, y: 1, w: 1.0, h: 1.0 },
  { id: '2', label: '2', x: 2.0, y: 1, w: 1.0, h: 1.0 },
  { id: '3', label: '3', x: 3.0, y: 1, w: 1.0, h: 1.0 },
  { id: '4', label: '4', x: 4.0, y: 1, w: 1.0, h: 1.0 },
  { id: '5', label: '5', x: 5.0, y: 1, w: 1.0, h: 1.0 },
  { id: '6', label: '6', x: 6.0, y: 1, w: 1.0, h: 1.0 },
  { id: '7', label: '7', x: 7.0, y: 1, w: 1.0, h: 1.0 },
  { id: '8', label: '8', x: 8.0, y: 1, w: 1.0, h: 1.0 },
  { id: '9', label: '9', x: 9.0, y: 1, w: 1.0, h: 1.0 },
  { id: '0', label: '0', x: 10.0, y: 1, w: 1.0, h: 1.0 },
  { id: 'MINUS', label: '-', x: 11.0, y: 1, w: 1.0, h: 1.0 },
  { id: 'EQUAL', label: '=', x: 12.0, y: 1, w: 1.0, h: 1.0 },
  { id: 'BACKSPACE', label: '⌫', x: 13.0, y: 1, w: 2.0, h: 1.0 },

  // ---- QWERTY 行 (y=2) ----
  { id: 'TAB', label: 'Tab', x: 0.0, y: 2, w: 1.5, h: 1.0 },
  { id: 'Q', label: 'Q', x: 1.5, y: 2, w: 1.0, h: 1.0 },
  { id: 'W', label: 'W', x: 2.5, y: 2, w: 1.0, h: 1.0 },
  { id: 'E', label: 'E', x: 3.5, y: 2, w: 1.0, h: 1.0 },
  { id: 'R', label: 'R', x: 4.5, y: 2, w: 1.0, h: 1.0 },
  { id: 'T', label: 'T', x: 5.5, y: 2, w: 1.0, h: 1.0 },
  { id: 'Y', label: 'Y', x: 6.5, y: 2, w: 1.0, h: 1.0 },
  { id: 'U', label: 'U', x: 7.5, y: 2, w: 1.0, h: 1.0 },
  { id: 'I', label: 'I', x: 8.5, y: 2, w: 1.0, h: 1.0 },
  { id: 'O', label: 'O', x: 9.5, y: 2, w: 1.0, h: 1.0 },
  { id: 'P', label: 'P', x: 10.5, y: 2, w: 1.0, h: 1.0 },
  { id: 'LBRACKET', label: '[', x: 11.5, y: 2, w: 1.0, h: 1.0 },
  { id: 'RBRACKET', label: ']', x: 12.5, y: 2, w: 1.0, h: 1.0 },
  { id: 'BACKSLASH', label: '\\', x: 13.5, y: 2, w: 1.5, h: 1.0 },

  // ---- ASDF 行 (y=3) ----
  { id: 'CAPSLOCK', label: 'Caps', x: 0.0, y: 3, w: 1.75, h: 1.0 },
  { id: 'A', label: 'A', x: 1.75, y: 3, w: 1.0, h: 1.0 },
  { id: 'S', label: 'S', x: 2.75, y: 3, w: 1.0, h: 1.0 },
  { id: 'D', label: 'D', x: 3.75, y: 3, w: 1.0, h: 1.0 },
  { id: 'F', label: 'F', x: 4.75, y: 3, w: 1.0, h: 1.0 },
  { id: 'G', label: 'G', x: 5.75, y: 3, w: 1.0, h: 1.0 },
  { id: 'H', label: 'H', x: 6.75, y: 3, w: 1.0, h: 1.0 },
  { id: 'J', label: 'J', x: 7.75, y: 3, w: 1.0, h: 1.0 },
  { id: 'K', label: 'K', x: 8.75, y: 3, w: 1.0, h: 1.0 },
  { id: 'L', label: 'L', x: 9.75, y: 3, w: 1.0, h: 1.0 },
  { id: 'SEMICOLON', label: ';', x: 10.75, y: 3, w: 1.0, h: 1.0 },
  { id: 'QUOTE', label: "'", x: 11.75, y: 3, w: 1.0, h: 1.0 },
  { id: 'ENTER', label: '⏎', x: 12.75, y: 3, w: 2.25, h: 1.0 },

  // ---- ZXCV 行 (y=4) ----
  { id: 'LSHIFT', label: '⇧', x: 0.0, y: 4, w: 2.25, h: 1.0 },
  { id: 'Z', label: 'Z', x: 2.25, y: 4, w: 1.0, h: 1.0 },
  { id: 'X', label: 'X', x: 3.25, y: 4, w: 1.0, h: 1.0 },
  { id: 'C', label: 'C', x: 4.25, y: 4, w: 1.0, h: 1.0 },
  { id: 'V', label: 'V', x: 5.25, y: 4, w: 1.0, h: 1.0 },
  { id: 'B', label: 'B', x: 6.25, y: 4, w: 1.0, h: 1.0 },
  { id: 'N', label: 'N', x: 7.25, y: 4, w: 1.0, h: 1.0 },
  { id: 'M', label: 'M', x: 8.25, y: 4, w: 1.0, h: 1.0 },
  { id: 'COMMA', label: ',', x: 9.25, y: 4, w: 1.0, h: 1.0 },
  { id: 'PERIOD', label: '.', x: 10.25, y: 4, w: 1.0, h: 1.0 },
  { id: 'SLASH', label: '/', x: 11.25, y: 4, w: 1.0, h: 1.0 },
  { id: 'RSHIFT', label: '⇧', x: 12.25, y: 4, w: 2.75, h: 1.0 },

  // ---- 底部修饰行 (y=5) ----
  { id: 'LCTRL', label: 'Ctrl', x: 0.0, y: 5, w: 1.25, h: 1.0 },
  { id: 'LWIN', label: 'Win', x: 1.25, y: 5, w: 1.25, h: 1.0 },
  { id: 'LALT', label: 'Alt', x: 2.5, y: 5, w: 1.25, h: 1.0 },
  { id: 'SPACE', label: '␣', x: 3.75, y: 5, w: 6.25, h: 1.0 },
  { id: 'RALT', label: 'Alt', x: 10.0, y: 5, w: 1.25, h: 1.0 },
  { id: 'RWIN', label: 'Win', x: 11.25, y: 5, w: 1.25, h: 1.0 },
  { id: 'MENU', label: '☰', x: 12.5, y: 5, w: 1.25, h: 1.0 },
  { id: 'RCTRL', label: 'Ctrl', x: 13.75, y: 5, w: 1.25, h: 1.0 },

  // ---- 数字小键盘 (右置) ----
  { id: 'NUMLOCK', label: 'Num', x: 19.0, y: 1, w: 1.0, h: 1.0 },
  { id: 'NUMPAD_DIVIDE', label: '/', x: 20.0, y: 1, w: 1.0, h: 1.0 },
  { id: 'NUMPAD_MULTIPLY', label: '*', x: 21.0, y: 1, w: 1.0, h: 1.0 },
  { id: 'NUMPAD_SUBTRACT', label: '-', x: 22.0, y: 1, w: 1.0, h: 1.0 },
  { id: 'NUMPAD_7', label: '7', x: 19.0, y: 2, w: 1.0, h: 1.0 },
  { id: 'NUMPAD_8', label: '8', x: 20.0, y: 2, w: 1.0, h: 1.0 },
  { id: 'NUMPAD_9', label: '9', x: 21.0, y: 2, w: 1.0, h: 1.0 },
  { id: 'NUMPAD_ADD', label: '+', x: 22.0, y: 2, w: 1.0, h: 2.0 },
  { id: 'NUMPAD_4', label: '4', x: 19.0, y: 3, w: 1.0, h: 1.0 },
  { id: 'NUMPAD_5', label: '5', x: 20.0, y: 3, w: 1.0, h: 1.0 },
  { id: 'NUMPAD_6', label: '6', x: 21.0, y: 3, w: 1.0, h: 1.0 },
  { id: 'NUMPAD_1', label: '1', x: 19.0, y: 4, w: 1.0, h: 1.0 },
  { id: 'NUMPAD_2', label: '2', x: 20.0, y: 4, w: 1.0, h: 1.0 },
  { id: 'NUMPAD_3', label: '3', x: 21.0, y: 4, w: 1.0, h: 1.0 },
  { id: 'NUMPAD_ENTER', label: '⏎', x: 22.0, y: 4, w: 1.0, h: 2.0 },
  { id: 'NUMPAD_0', label: '0', x: 19.0, y: 5, w: 2.0, h: 1.0 },
  { id: 'NUMPAD_DECIMAL', label: '.', x: 21.0, y: 5, w: 1.0, h: 1.0 },

  // ---- 导航编辑键区（主键区与小键盘之间）----
  { id: 'INSERT', label: 'Ins', x: 16.0, y: 1, w: 1.0, h: 1.0 },
  { id: 'HOME', label: 'Home', x: 16.0, y: 2, w: 1.0, h: 1.0 },
  { id: 'PAGEUP', label: 'PgUp', x: 16.0, y: 3, w: 1.0, h: 1.0 },
  { id: 'DELETE', label: 'Del', x: 17.0, y: 1, w: 1.0, h: 1.0 },
  { id: 'END', label: 'End', x: 17.0, y: 2, w: 1.0, h: 1.0 },
  { id: 'PAGEDOWN', label: 'PgDn', x: 17.0, y: 3, w: 1.0, h: 1.0 },
  // 方向键（倒 T 布局）
  { id: 'UP', label: '↑', x: 17.0, y: 4, w: 1.0, h: 1.0 },
  { id: 'DOWN', label: '↓', x: 17.0, y: 5, w: 1.0, h: 1.0 },
  { id: 'LEFT', label: '←', x: 16.0, y: 5, w: 1.0, h: 1.0 },
  { id: 'RIGHT', label: '→', x: 18.0, y: 5, w: 1.0, h: 1.0 },
];

// 网格范围与中心
export const GRID_MIN_X = 0;
export const GRID_MAX_X = 23;
export const GRID_MIN_Y = 0;
export const GRID_MAX_Y = 6;
export const GRID_CENTER_X = (GRID_MIN_X + GRID_MAX_X) / 2; // 11.5
export const GRID_CENTER_Y = (GRID_MIN_Y + GRID_MAX_Y) / 2; // 3

/** 网格坐标 → 世界坐标（单位：u × PITCH 放到 scene.js 里乘） */
export function gridToScene(gx, gy) {
  return { x: gx - GRID_CENTER_X, z: gy - GRID_CENTER_Y };
}

/** id → 键位定义 索引 */
const BY_ID = new Map(KEYS.map((k) => [k.id, k]));
export function getKey(id) { return BY_ID.get(id); }
export function allKeyIds() { return KEYS.map((k) => k.id); }

/* ---------------- 颜色工具 ---------------- */

/** 热度渐变：按 t∈[0,1] 从蓝 → 青 → 黄 → 红 */
export function heatColor(t) {
  // 分段线性 HSL 插值
  const stops = [
    [0.62, 0.9, 0.55],   // 蓝
    [0.50, 0.95, 0.60],  // 青
    [0.14, 0.95, 0.62],  // 黄
    [0.0, 0.85, 0.58],   // 红
  ];
  const seg = Math.min(Math.max(t, 0), 1) * (stops.length - 1);
  const i = Math.min(Math.floor(seg), stops.length - 2);
  const f = seg - i;
  const a = stops[i], b = stops[i + 1];
  return {
    h: a[0] + (b[0] - a[0]) * f,
    s: a[1] + (b[1] - a[1]) * f,
    l: a[2] + (b[2] - a[2]) * f,
  };
}

/** 高度映射：按键次数 → 柱子目标高度（√ 尺度，1u ≈ 0.32 世界单位） */
export function countToHeight(count) {
  if (count <= 0) return 0;
  return Math.sqrt(count) * 0.38;
}

/** 格式化为千分位 */
export function fmt(n) {
  return Math.round(n).toLocaleString('en-US');
}

/** 有符号时间格式化（HH:MM:SS） */
export function fmtTime(ts) {
  const d = new Date(ts * 1000);
  const p = (x) => String(x).padStart(2, '0');
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}