/* ==========================================================================
 * keyboard.js — 构建 104 键键帽 + 动态数据柱，成长动画与热力着色
 * ========================================================================== */

import * as THREE from 'three';
import {
  KEYS, getKey, gridToScene, heatColor, countToHeight,
} from './data.js';
import { Scene, PITCH, KEYCAP_TOP, BAR_BASE } from './scene.js';

const GAP = 0.045;               // 键帽间缝隙（u 内的比例）
const KEYCAP_H = 0.22;           // 键帽高度
const BAR_WIDTH = 0.34;          // 数据柱宽度（世界单位）
const BAR_DEPTH = 0.34;

// 成长动画参数
const GROW_SPEED = 4.5;          // 接近目标的速度
const PRESS_DEPTH = 0.10;        // 按压下沉深度
const PRESS_SPEED = 10;          // 回弹速度

export class Keyboard3D {
  constructor(scene) {
    this.scene = scene;
    this.keys = new Map();       // id -> { cap, bar, target, current, pressed, barMat }
    this.maxCount = 0;
    this.group = new THREE.Group();
    // 柱子统一分组，便于整体操作
    this.barGroup = new THREE.Group();
    this.group.add(this.barGroup);
    scene.scene.add(this.group);
    this._buildAll();
  }

  /* ---------------- 构建 ---------------- */

  _buildAll() {
    for (const k of KEYS) {
      const { x, z } = gridToScene(k.x + k.w / 2, k.y + k.h / 2);
      const mesh = this._buildKey(k, x, z);
      this.keys.set(k.id, mesh);
    }
  }

  _buildKey(k, x, z) {
    const wu = k.w - GAP, hu = k.h - GAP;

    // ---------- 键帽 ----------
    const capGeo = new THREE.BoxGeometry(wu, KEYCAP_H, hu);
    const capMat = new THREE.MeshStandardMaterial({
      color: 0x252a4a,
      metalness: 0.55,
      roughness: 0.38,
      emissive: 0x0a0d22,
      emissiveIntensity: 0.6,
    });
    const cap = new THREE.Mesh(capGeo, capMat);
    cap.position.set(x, KEYCAP_TOP / 2, z);
    cap.castShadow = true;
    cap.receiveShadow = true;

    // 键帽顶面标签
    const labelTex = Scene.makeLabelTexture(k.label, { big: k.label.length <= 1 });
    const labelMat = new THREE.MeshBasicMaterial({
      map: labelTex, transparent: true, depthWrite: false,
    });
    const labelGeo = new THREE.PlaneGeometry(Math.min(wu * 0.86, 0.95), Math.min(hu * 0.86, 0.95));
    const label = new THREE.Mesh(labelGeo, labelMat);
    label.rotation.x = -Math.PI / 2;
    label.position.set(x, KEYCAP_TOP + 0.005, z);
    label.renderOrder = 2;

    // ---------- 数据柱 ----------
    const barH = 1; // 单位高度，通过 scale.y 控制
    const barGeo = new THREE.BoxGeometry(BAR_WIDTH, barH, BAR_DEPTH);
    // 底部为原点，成长时向上生长
    barGeo.translate(0, barH / 2, 0);
    const barMat = new THREE.MeshStandardMaterial({
      color: 0x6c8cff,
      emissive: 0x6c8cff,
      emissiveIntensity: 0.55,
      metalness: 0.3,
      roughness: 0.3,
      transparent: true,
      opacity: 0.95,
    });
    const bar = new THREE.Mesh(barGeo, barMat);
    bar.position.set(x, BAR_BASE, z);
    bar.scale.y = 0.001; // 初始几乎为 0
    bar.castShadow = true;
    this.barGroup.add(bar);

    // 柱顶光点（发光小球，随着柱子长高而上移）
    const tipGeo = new THREE.SphereGeometry(0.075, 12, 12);
    const tipMat = new THREE.MeshBasicMaterial({
      color: 0xffffff, transparent: true, opacity: 0.95,
      blending: THREE.AdditiveBlending, depthWrite: false,
    });
    const tip = new THREE.Mesh(tipGeo, tipMat);
    tip.position.set(x, BAR_BASE, z);
    this.barGroup.add(tip);

    this.group.add(cap);
    this.group.add(label);

    return {
      id: k.id, cap, label, bar, tip, barMat,
      current: 0,      // 当前显示高度
      target: 0,       // 目标高度
      pressStart: -1,  // 按压动画开始时间
      hasData: false,
    };
  }

  /* ---------------- 数据更新 ---------------- */

  /** 应用整份快照（初始化或刷新） */
  applyCounts(counts) {
    let max = 0;
    for (const v of Object.values(counts)) if (v > max) max = v;
    this.maxCount = Math.max(this.maxCount, max);
    for (const [id, mesh] of this.keys) {
      const n = counts[id] || 0;
      mesh._count = n;
      mesh.target = countToHeight(n);
      if (n > 0) mesh.hasData = true;
    }
    this._refreshMax();
  }

  /** 单个按键 +1（实时事件），count 为该键绝对次数 */
  bump(id, count) {
    const mesh = this.keys.get(id);
    if (!mesh) return;
    const n = count || (mesh._count || 0) + 1;
    mesh._count = n;
    mesh.target = countToHeight(n);
    mesh.hasData = true;
    mesh.pressStart = performance.now();
    if (n > this.maxCount) {
      this.maxCount = n;
      this._refreshMax();
    }
  }

  _refreshMax() {
    // 热力着色依赖相对比例（由 main.js 每帧调用 updateColors 完成）
  }

  /** 每帧：成长 + 按压动画 + 热力颜色 */
  update(dt, elapsed) {
    for (const mesh of this.keys.values()) {
      // ---- 柱体成长（指数逼近） ----
      const h = mesh.current + (mesh.target - mesh.current) * Math.min(1, GROW_SPEED * dt);
      mesh.current = h;
      if (h < 0.01) {
        mesh.bar.visible = false;
        mesh.tip.visible = false;
      } else {
        mesh.bar.visible = true;
        mesh.tip.visible = true;
        mesh.bar.scale.y = h;
        const mid = BAR_BASE + h / 2;
        mesh.bar.position.y = mid;
        mesh.tip.position.y = BAR_BASE + h + 0.03;
      }

      // ---- 键帽按压回弹 ----
      if (mesh.pressStart >= 0) {
        const t = (performance.now() - mesh.pressStart) / 1000;
        if (t < 0.12) {
          // 快速下沉
          const k = t / 0.12;
          mesh.cap.position.y += ((KEYCAP_TOP / 2 - PRESS_DEPTH) - mesh.cap.position.y) * Math.min(1, PRESS_SPEED * dt * 2);
          mesh.label.position.y = mesh.cap.position.y + KEYCAP_TOP / 2 + 0.005;
        } else if (t < 0.4) {
          // 回弹
          const k = (t - 0.12) / 0.28;
          const targetY = KEYCAP_TOP / 2;
          mesh.cap.position.y += (targetY - mesh.cap.position.y) * Math.min(1, PRESS_SPEED * dt * 0.9);
          mesh.label.position.y = mesh.cap.position.y + KEYCAP_TOP / 2 + 0.005;
        } else {
          mesh.cap.position.y = KEYCAP_TOP / 2;
          mesh.label.position.y = KEYCAP_TOP + 0.005;
          mesh.pressStart = -1;
        }
      }
    }
  }

  /** 柱体热力颜色：每帧刷新（性能足够，104 根柱） */
  updateColors() {
    if (this.maxCount <= 0) return;
    for (const mesh of this.keys.values()) {
      if (!mesh.hasData || mesh._count <= 0) continue;
      const t = Math.min(mesh._count / this.maxCount, 1);
      const c = heatColor(t);
      const col = new THREE.Color(`hsl(${c.h}, ${c.s * 100}%, ${c.l * 100}%)`);
      mesh.barMat.color.copy(col);
      mesh.barMat.emissive.copy(col);
      mesh.barMat.emissiveIntensity = 0.35 + t * 0.55;
      mesh.tip.material.color.copy(col);
    }
  }

  /** 当前各键计数（供面板统计复用；由 main.js 维护真实 counts） */
  setCounts(counts) { this._counts = counts; }

  getCounts() { return this._counts || {}; }
}