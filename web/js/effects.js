/* ==========================================================================
 * effects.js — 按键迸发粒子、漂浮计数精灵
 * ========================================================================== */

import * as THREE from 'three';

// 迸发粒子池：每次按键在键帽上方喷一小簇光点，随即飘散消失
export class BurstFX {
  constructor(scene, maxBursts = 24) {
    this.scene = scene;
    this.MAX = maxBursts;
    this.pool = [];
    this.active = [];
    this._time = 0;
    this._buildPool();
  }

  _buildPool() {
    const COUNT = 12; // 每次迸发的粒子数
    for (let b = 0; b < this.MAX; b++) {
      const positions = new Float32Array(COUNT * 3);
      const geo = new THREE.BufferGeometry();
      geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
      const mat = new THREE.PointsMaterial({
        color: 0x7fe7ff,
        size: 0.09,
        transparent: true,
        opacity: 0,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        sizeAttenuation: true,
      });
      // 预置位置到“隐藏”区
      for (let i = 0; i < COUNT; i++) {
        positions[i * 3 + 1] = -100;
      }
      const points = new THREE.Points(geo, mat);
      points.visible = false;
      this.scene.scene.add(points);
      this.pool.push({
        points, geo, mat, positions,
        alive: 0,       // 剩余生命（秒）
        vel: new Float32Array(COUNT * 3),
        spawn: new Float32Array(3),
      });
    }
  }

  /** 在 (x, y, z) 迸发一簇粒子 */
  burst(x, y, z, color = null) {
    if (this.pool.length === 0) return;
    const b = this.pool.pop();
    b.alive = 0.7 + Math.random() * 0.25;
    b.spawn[0] = x; b.spawn[1] = y; b.spawn[2] = z;
    const COUNT = b.positions.length / 3;
    for (let i = 0; i < COUNT; i++) {
      // 位置：键帽上方随机偏移
      b.positions[i * 3] = x + (Math.random() - 0.5) * 0.3;
      b.positions[i * 3 + 1] = y + Math.random() * 0.2;
      b.positions[i * 3 + 2] = z + (Math.random() - 0.5) * 0.3;
      // 速度：向上为主 + 随机扩散
      const angle = Math.random() * Math.PI * 2;
      const spread = 0.6 + Math.random() * 1.2;
      b.vel[i * 3] = Math.cos(angle) * spread;
      b.vel[i * 3 + 1] = 1.2 + Math.random() * 2.2;
      b.vel[i * 3 + 2] = Math.sin(angle) * spread;
    }
    b.geo.attributes.position.needsUpdate = true;
    b.points.visible = true;
    if (color) b.mat.color.set(color);
    this.active.push(b);
  }

  /** 每帧更新：移动 + 衰减 */
  update(dt) {
    this._time += dt;
    for (let i = this.active.length - 1; i >= 0; i--) {
      const b = this.active[i];
      b.alive -= dt;
      if (b.alive <= 0) {
        b.points.visible = false;
        b.mat.opacity = 0;
        this.active.splice(i, 1);
        this.pool.push(b);
        continue;
      }
      const COUNT = b.positions.length / 3;
      const life01 = b.alive / 0.8;
      if (b.mat.opacity !== life01) b.mat.opacity = Math.max(life01, 0);
      for (let j = 0; j < COUNT; j++) {
        b.positions[j * 3] += b.vel[j * 3] * dt;
        b.positions[j * 3 + 1] += b.vel[j * 3 + 1] * dt;
        b.positions[j * 3 + 2] += b.vel[j * 3 + 2] * dt;
        b.vel[j * 3 + 1] -= 4.5 * dt; // 重力
      }
      b.geo.attributes.position.needsUpdate = true;
    }
  }
}

// 漂浮计数精灵：柱顶短暂显示 "+N"（简化：显示按键计数）
export class FloatTextFX {
  constructor(scene) {
    this.scene = scene;
    this.items = [];
  }

  add(text, x, y, z, color = '#7fe7ff') {
    const canvas = document.createElement('canvas');
    canvas.width = 128; canvas.height = 64;
    const ctx = canvas.getContext('2d');
    ctx.font = 'bold 40px "Segoe UI", sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.shadowColor = 'rgba(0,0,0,0.8)';
    ctx.shadowBlur = 6;
    ctx.fillStyle = color;
    ctx.fillText(String(text), 64, 32);
    const tex = new THREE.CanvasTexture(canvas);
    const mat = new THREE.SpriteMaterial({
      map: tex, transparent: true, depthWrite: false, opacity: 0,
    });
    const sprite = new THREE.Sprite(mat);
    sprite.position.set(x, y, z);
    sprite.scale.set(0.75, 0.375, 1);
    this.scene.scene.add(sprite);
    this.items.push({ sprite, mat, born: performance.now(), life: 1.1 });
  }

  update(dt) {
    for (let i = this.items.length - 1; i >= 0; i--) {
      const it = this.items[i];
      const age = (performance.now() - it.born) / 1000;
      if (age > it.life) {
        this.scene.scene.remove(it.sprite);
        it.mat.dispose();
        this.items.splice(i, 1);
        continue;
      }
      const t = age / it.life;
      it.sprite.position.y += dt * 0.55;
      it.mat.opacity = t < 0.15 ? t / 0.15 : 1 - (t - 0.15) / 0.85;
    }
  }
}