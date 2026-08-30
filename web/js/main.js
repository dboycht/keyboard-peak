/* ==========================================================================
 * main.js — 应用入口：SSE 实时数据 + 3D 场景 + 特效 + 统计面板
 * ========================================================================== */

import { Scene } from './scene.js';
import { Keyboard3D } from './keyboard.js';
import { BurstFX, FloatTextFX } from './effects.js';
import { UI } from './ui.js';
import { getKey, fmtTime } from './data.js';

// ---------------------------------------------------------------- 工具

function el(id) { return document.getElementById(id); }

// ---------------------------------------------------------------- 状态

const scene = new Scene(document.getElementById('stage'));
const keyboard = new Keyboard3D(scene);
const burst = new BurstFX(scene);
const floatText = new FloatTextFX(scene);
const ui = new UI();

// 当前计数（键 ID -> 次数），实时维护
const counts = {};
let totalCount = 0;
let todayTotal = 0;
let lastEventTime = Date.now();   // 最近一次按键时间
let rateSamples = [];             // 近 60 秒速率采样
const RATE_WINDOW = 60000;

// 防抖：面板每秒最多刷新一次
let uiDirty = false;
let uiTimer = null;

// ---------------------------------------------------------------- SSE

function connect() {
  const es = new EventSource('/stream');
  es.onopen = () => { ui.setLive(true); };
  es.onerror = () => { ui.setLive(false); };

  es.addEventListener('init', (ev) => {
    const snapshot = JSON.parse(ev.data);
    applySnapshot(snapshot);
    ui.setLive(true);
  });

  es.addEventListener('key', (ev) => {
    const data = JSON.parse(ev.data);
    handleKey(data.key, data.ts || Date.now() / 1000);
  });

  es.onmessage = (ev) => {
    // 兼容仅 data 的推送（备用路径）
    try { handleKey(ev.data, Date.now() / 1000); } catch {}
  };
}

function applySnapshot(snap) {
  // 重置本地计数（以服务端为准）
  for (const k of Object.keys(counts)) delete counts[k];
  Object.assign(counts, snap.counts || {});
  keyboard.applyCounts(counts);
  keyboard.setCounts(counts);
  totalCount = snap.total || 0;
  todayTotal = snap.today_total || 0;
  ui.applySnapshot(snap);
  UI_rateRefresh();
  ui.setWatermarkHidden(Object.keys(counts).length > 0);
}

function handleKey(rawKey, ts) {
  const id = typeof rawKey === 'string' ? rawKey : rawKey.key;
  if (!id) return;

  counts[id] = (counts[id] || 0) + 1;
  totalCount++;
  todayTotal++;
  lastEventTime = Date.now();

  // 3D：柱子 + 特效
  keyboard.bump(id, counts[id]);
  const mesh = keyboard.keys.get(id);
  if (mesh) {
    const { x, z } = mesh.cap.position;
    burst.burst(x, mesh.cap.position.y + 0.35, z, mesh.tip.material.color.getHex());
    floatText.add(counts[id], x, BAR_TOP_Y(mesh), z);
    scene.addRipple(x, z, mesh.tip.material.color.getHex());
  }

  // 速率采样
  rateSamples.push(Date.now());

  // UI
  ui.pushTicker(id, ts);
  uiDirty = true;
  scheduleUiRefresh();
}

function BAR_TOP_Y(mesh) {
  // 柱顶高度（与 keyboard.update 中的动画一致）
  return mesh.bar.position.y + mesh.bar.scale.y / 2 + 0.25;
}

// ---------------------------------------------------------------- UI 刷新（每秒节流）

function scheduleUiRefresh() {
  if (uiTimer) return;
  uiTimer = setTimeout(() => {
    uiTimer = null;
    if (!uiDirty) return;
    uiDirty = false;
    ui.el.total.textContent = fmt(totalCount);
    ui.el.today.textContent = fmt(todayTotal);
    ui.renderTop(counts);
  }, 1000);
}

// 直接复用一个格式化函数
function fmt(n) { return Math.round(n).toLocaleString('en-US'); }

function UI_rateRefresh() {
  // 供 applySnapshot 初始化速率显示
  ui.setRate(0);
}

// ---------------------------------------------------------------- 速率计算

function computeRate() {
  const now = Date.now();
  while (rateSamples.length && now - rateSamples[0] > RATE_WINDOW) {
    rateSamples.shift();
  }
  return (rateSamples.length / RATE_WINDOW) * 60000;
}

// ---------------------------------------------------------------- 动画循环注册

scene.addAnimation((dt) => {
  // 键盘成长/按压动画
  keyboard.update(dt);
  keyboard.updateColors();

  // 特效
  burst.update(dt);
  floatText.update(dt);

  // 速率显示（节流：每秒 2 次）
  if (Math.floor(performance.now() / 500) != Math.floor((performance.now() - dt * 1000) / 500)) {
    ui.setRate(computeRate());
  }
});

// 空状态 5 秒后自动淡出水位线
setTimeout(() => {
  if (Object.keys(counts).length > 0) ui.setWatermarkHidden(true);
}, 5000);

// ---------------------------------------------------------------- 模型旋转控制

// 「暂停」= 暂停模型的自动旋转（autoRotate），与按键采集无关
const pauseBtn = document.getElementById('pauseBtn');
const pauseText = document.getElementById('pauseText');
const pauseIcon = document.getElementById('pauseIcon');
let rotating = true;

function setRotatingUI(state) {
  rotating = !!state;
  pauseBtn.classList.toggle('paused', !rotating);
  pauseText.textContent = rotating ? '暂停旋转' : '恢复旋转';
  pauseIcon.textContent = rotating ? '⏸' : '▶';
}

function toggleRotate() {
  rotating = !rotating;
  scene.setAutoRotate(rotating);
  setRotatingUI(rotating);
}

pauseBtn.addEventListener('click', toggleRotate);

// ---------------------------------------------------------------- 显示模式切换

const MODE_KEY = 'kpeak-bar-mode';
const MODES = ['classic', 'cover', 'heat'];

function applyMode(mode) {
  if (!MODES.includes(mode)) mode = 'classic';
  keyboard.setMode(mode);
  // 更新按钮高亮
  document.querySelectorAll('.mode-btn').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.mode === mode);
  });
  try { localStorage.setItem(MODE_KEY, mode); } catch (e) {}
}

// 初始化模式（优先 localStorage，其次服务端设置）
function initMode() {
  let mode = null;
  try { mode = localStorage.getItem(MODE_KEY); } catch (e) {}
  if (!mode || !MODES.includes(mode)) mode = 'classic';
  applyMode(mode);
  document.querySelectorAll('.mode-btn').forEach((btn) => {
    btn.addEventListener('click', () => applyMode(btn.dataset.mode));
  });
}

// ---------------------------------------------------------------- 启动

initMode();
connect();
scene.start();

// 服务端断开时重连（EventSource 自动重连，此处监听可见性变化保活）
document.addEventListener('visibilitychange', () => {
  if (!document.hidden) {
    // 回到前台时刷新快照
    fetch('/snapshot')
      .then((r) => r.json())
      .then((snap) => { if (snap && snap.counts) { applySnapshot(snap); ui.setLive(true); } })
      .catch(() => {});
  }
});

// 调试钩子：window.__kpeakDebug() 输出键盘/柱子真实尺寸（生产保留，便于排查显示问题）
window.__kpeakDebug = () => {
  const out = {};
  for (const [id, m] of keyboard.keys) {
    if (['SPACE', 'A', 'ENTER', 'E'].includes(id)) {
      out[id] = {
        w: m.curW, d: m.curD, base: m.curBase, h: m.current, target: m.target,
        bottom: m.bar.position.y,   // 柱体底部世界 y（几何体底部在本地原点）
        capTop: m.cap.position.y + 0.11,  // 键帽顶面世界 y
      };
    }
  }
  out.mode = keyboard.mode;
  out.autoRotate = scene.isAutoRotating();
  return out;
};