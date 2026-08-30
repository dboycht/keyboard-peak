/* ==========================================================================
 * ui.js — 左侧统计面板：指标、趋势图、Top 排行、最近按键
 * ========================================================================== */

import { getKey, fmt, fmtTime } from './data.js';

const MAX_TOP = 10;
const TICKER_MAX = 18;

export class UI {
  constructor() {
    this.el = {
      total: document.getElementById('mTotal'),
      today: document.getElementById('mToday'),
      rate: document.getElementById('mRate'),
      spark: document.getElementById('spark'),
      topList: document.getElementById('topList'),
      ticker: document.getElementById('recentTicker'),
      liveBadge: document.getElementById('liveBadge'),
      liveText: document.getElementById('liveText'),
      watermark: document.getElementById('watermark'),
    };
    this.sparkCtx = this.el.spark.getContext('2d');
    this._rateAccum = 0;       // 当前窗口按键次数
    this._rateStart = Date.now();
    this._lastSpark = null;
    this._tickerBuf = [];
  }

  /* ---------------- 连接状态 ---------------- */

  setLive(on) {
    this.el.liveBadge.classList.toggle('live', on);
    this.el.liveText.textContent = on ? '实时监听中' : '连接断开';
  }

  setWatermarkHidden(hidden) {
    this.el.watermark.style.opacity = hidden ? '0' : '1';
  }

  /* ---------------- 指标 ---------------- */

  /** 一键刷新全部（快照或定时刷新用） */
  applySnapshot(snap) {
    this.el.total.textContent = fmt(snap.total || 0);
    this.el.today.textContent = fmt(snap.today_total || 0);
    this.setSpark(snap.spark || []);
    this.renderTop(snap.counts || {});
    this.renderTicker(snap.recent || []);
  }

  /** 单次按键事件更新 */
  onKey(keyId) {
    this._rateAccum++;
    // 速率窗口：每秒重算一次（节流在 main 中处理）
  }

  setRate(rate) {
    this.el.rate.textContent = rate.toFixed(1);
  }

  /* ---------------- 趋势图 ---------------- */

  setSpark(points) {
    if (!points || points.length === 0) return;
    this._lastSpark = points;
    this._drawSpark();
  }

  _drawSpark() {
    const pts = this._lastSpark;
    if (!pts) return;
    const ctx = this.sparkCtx;
    const { width: W, height: H } = this.el.spark;
    ctx.clearRect(0, 0, W, H);

    const max = Math.max(...pts.map((p) => p.n), 1);
    const n = pts.length;
    const pad = 4;
    const bw = H - pad * 2;

    // 面积渐变
    const grad = ctx.createLinearGradient(0, 0, 0, H);
    grad.addColorStop(0, 'rgba(108,140,255,0.45)');
    grad.addColorStop(1, 'rgba(108,140,255,0.02)');

    ctx.beginPath();
    ctx.moveTo(0, H - pad);
    for (let i = 0; i < n; i++) {
      const x = (i / (n - 1)) * W;
      const y = H - pad - (pts[i].n / max) * bw;
      ctx.lineTo(x, y);
    }
    ctx.lineTo(W, H - pad);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();

    // 描线
    ctx.beginPath();
    for (let i = 0; i < n; i++) {
      const x = (i / (n - 1)) * W;
      const y = H - pad - (pts[i].n / max) * bw;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.strokeStyle = 'rgba(120,160,255,0.9)';
    ctx.lineWidth = 1.6;
    ctx.lineJoin = 'round';
    ctx.stroke();

    // 末端亮点
    const last = pts[n - 1];
    const lx = W, ly = H - pad - (last.n / max) * bw;
    ctx.beginPath();
    ctx.arc(lx, ly, 3.5, 0, Math.PI * 2);
    ctx.fillStyle = '#7fe7ff';
    ctx.fill();
  }

  /* ---------------- Top 排行 ---------------- */

  renderTop(counts) {
    const entries = Object.entries(counts)
      .map(([id, n]) => ({ id, n }))
      .filter((e) => e.n > 0)
      .sort((a, b) => b.n - a.n)
      .slice(0, MAX_TOP);

    const maxN = entries.length ? entries[0].n : 1;
    const list = this.el.topList;
    list.innerHTML = '';

    if (entries.length === 0) {
      const li = document.createElement('li');
      li.textContent = '还没有按键数据';
      li.style.cssText = 'color:#666; font-size:12px; padding:6px 0;';
      list.appendChild(li);
      return;
    }

    for (const e of entries) {
      const def = getKey(e.id);
      const li = document.createElement('li');

      const rank = document.createElement('span');
      rank.className = 'rank';

      const key = document.createElement('span');
      key.className = 'key';
      key.textContent = def ? def.label : e.id;

      const wrap = document.createElement('span');
      wrap.className = 'bar-wrap';
      const bar = document.createElement('span');
      bar.className = 'bar';
      bar.style.width = `${Math.max((e.n / maxN) * 100, 4)}%`;

      const cnt = document.createElement('span');
      cnt.className = 'cnt';
      cnt.textContent = fmt(e.n);

      wrap.appendChild(bar);
      li.append(rank, key, wrap, cnt);
      list.appendChild(li);
    }
  }

  /* ---------------- 最近按键 ---------------- */

  renderTicker(recent) {
    this._tickerBuf = recent.slice(-TICKER_MAX);
    this._drawTicker();
  }

  pushTicker(keyId, ts) {
    this._tickerBuf.push([keyId, ts]);
    if (this._tickerBuf.length > TICKER_MAX) this._tickerBuf.shift();
    this._drawTicker();
  }

  _drawTicker() {
    const el = this.el.ticker;
    el.innerHTML = '';
    for (const [id, ts] of this._tickerBuf) {
      const def = getKey(id);
      const span = document.createElement('span');
      span.className = 'tick';
      span.title = fmtTime(ts);
      span.textContent = def ? def.label : id;
      el.appendChild(span);
    }
  }
}