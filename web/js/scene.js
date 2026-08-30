/* ==========================================================================
 * scene.js — 场景、相机、灯光、粒子背景、渲染循环调度
 * ========================================================================== */

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/OrbitControls.js';

// 世界尺度：1u（键距）对应的世界单位
export const PITCH = 1.0;

export const KEYCAP_TOP = 0.26;      // 键帽顶面高度
export const BAR_BASE = 0.42;        // 数据柱起始高度（略高于键帽）

export class Scene {
  constructor(container) {
    this.container = container;
    this.keys = new Map();          // keyId -> { cap, bar, last}

    // ---------- 渲染器 ----------
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setSize(window.innerWidth, window.innerHeight);
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.15;
    container.appendChild(this.renderer.domElement);

    // ---------- 场景 ----------
    this.scene = new THREE.Scene();
    this.scene.fog = new THREE.FogExp2(0x05060f, 0.022);

    // ---------- 相机 ----------
    this.camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 300);
    this.camera.position.set(14, 13, 16);

    // ---------- 控制器 ----------
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.target.set(0, 1.4, 0);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    this.controls.minDistance = 6;
    this.controls.maxDistance = 60;
    this.controls.maxPolarAngle = Math.PI / 2.15;
    this.controls.autoRotate = true;
    this.controls.autoRotateSpeed = 1.2;
    this.controls.update();

    // ---------- 灯光 ----------
    this._buildLights();

    // ---------- 环境 ----------
    this._buildEnvironment();

    // ---------- 粒子 ----------
    this.particles = this._buildParticles();
    this.scene.add(this.particles.points);

    // ---------- 状态 ----------
    this._clock = new THREE.Clock();
    this._animations = [];   // 每帧执行的更新函数
    this._ripples = [];
    this._stopped = false;

    window.addEventListener('resize', () => this._onResize());
  }

  /* ---------------- 灯光 ---------------- */

  _buildLights() {
    const hemi = new THREE.HemisphereLight(0x8090ff, 0x0a0a18, 0.55);
    this.scene.add(hemi);

    const key = new THREE.DirectionalLight(0xffffff, 1.6);
    key.position.set(10, 20, 12);
    key.castShadow = true;
    key.shadow.mapSize.set(2048, 2048);
    key.shadow.camera.left = -16;
    key.shadow.camera.right = 16;
    key.shadow.camera.top = 12;
    key.shadow.camera.bottom = -12;
    key.shadow.camera.far = 60;
    this.scene.add(key);

    const rim = new THREE.DirectionalLight(0x7a8cff, 0.8);
    rim.position.set(-12, 6, -10);
    this.scene.add(rim);

    const fill = new THREE.PointLight(0x00e5ff, 30, 60);
    fill.position.set(-6, 8, 14);
    this.scene.add(fill);
    this.fillLight = fill;

    // 缓慢漂移的彩色补光
    this.moodLight = new THREE.PointLight(0xff5c8a, 18, 70);
    this.moodLight.position.set(12, 5, -6);
    this.scene.add(this.moodLight);
  }

  /* ---------------- 环境：底盘 / 地面 / 网格 ---------------- */

  _buildEnvironment() {
    // 键盘底盘（暗色亚克力）
    const baseGeo = new THREE.BoxGeometry(22.4, 0.5, 8.4);
    const baseMat = new THREE.MeshStandardMaterial({
      color: 0x0b0d1e,
      metalness: 0.75,
      roughness: 0.35,
      emissive: 0x070a1c,
    });
    const base = new THREE.Mesh(baseGeo, baseMat);
    base.position.set(0, -0.28, 0);
    base.receiveShadow = true;
    this.scene.add(base);

    // 底座霓虹边框
    const edgeGeo = new THREE.BoxGeometry(22.4, 0.06, 8.4);
    const edgeMat = new THREE.MeshStandardMaterial({
      color: 0x111c4d,
      emissive: 0x3355ff,
      emissiveIntensity: 0.55,
      metalness: 0.3,
      roughness: 0.6,
    });
    const edge = new THREE.Mesh(edgeGeo, edgeMat);
    edge.position.set(0, 0.02, 0);
    this.scene.add(edge);

    // 地面（接受阴影的暗面）
    const floor = new THREE.Mesh(
      new THREE.PlaneGeometry(120, 120),
      new THREE.MeshStandardMaterial({ color: 0x04050d, roughness: 0.9, metalness: 0.1 })
    );
    floor.rotation.x = -Math.PI / 2;
    floor.position.y = -0.55;
    floor.receiveShadow = true;
    this.scene.add(floor);

    // 辅助网格线（发光风格）
    const grid = new THREE.GridHelper(60, 50, 0x1a2450, 0x101430);
    grid.position.y = -0.52;
    this.scene.add(grid);
  }

  /* ---------------- 粒子星空 ---------------- */

  _buildParticles() {
    const COUNT = 1800;
    const positions = new Float32Array(COUNT * 3);
    const colors = new Float32Array(COUNT * 3);
    const spreads = [
      { x: 90, y: 40, z: 90, c: new THREE.Color(0x6c8cff) },
      { x: 70, y: 55, z: 70, c: new THREE.Color(0x00e5ff) },
      { x: 110, y: 25, z: 110, c: new THREE.Color(0xff5c8a) },
    ];
    const rnd = (a, b) => a + Math.random() * (b - a);
    for (let i = 0; i < COUNT; i++) {
      const s = spreads[i % spreads.length];
      positions[i * 3] = rnd(-s.x, s.x);
      positions[i * 3 + 1] = rnd(-s.y, s.y);
      positions[i * 3 + 2] = rnd(-s.z, s.z);
      const c = s.c;
      const bright = rnd(0.35, 1.0);
      colors[i * 3] = c.r * bright;
      colors[i * 3 + 1] = c.g * bright;
      colors[i * 3 + 2] = c.b * bright;
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    const mat = new THREE.PointsMaterial({
      size: 0.09, vertexColors: true, transparent: true, opacity: 0.85,
      blending: THREE.AdditiveBlending, depthWrite: false, sizeAttenuation: true,
    });
    const points = new THREE.Points(geo, mat);
    points.userData = { baseY: 0 };
    return { points, material: mat };
  }

  /* ---------------- 键帽标签纹理 ---------------- */

  static makeLabelTexture(label, opts = {}) {
    const { size = 128, fontSize = opts.big ? 88 : 54, color = '#dfe6ff' } = opts;
    const canvas = document.createElement('canvas');
    canvas.width = size; canvas.height = size;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, size, size);
    ctx.fillStyle = color;
    ctx.font = `${fontSize}px "Segoe UI", "Microsoft YaHei", sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.shadowColor = 'rgba(0,0,0,0.6)';
    ctx.shadowBlur = 4;
    ctx.fillText(String(label), size / 2, size / 2 + 2);
    const tex = new THREE.CanvasTexture(canvas);
    tex.anisotropy = 4;
    return tex;
  }

  /* ---------------- 对外 API ---------------- */

  /** 注册每帧更新函数 */
  addAnimation(fn) { this._animations.push(fn); }

  /** 添加涟漪环（按键特效） */
  addRipple(x, z, color = 0x6c8cff) {
    const ring = new THREE.Mesh(
      new THREE.RingGeometry(0.3, 0.55, 48),
      new THREE.MeshBasicMaterial({
        color, transparent: true, opacity: 0.9,
        side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false,
      })
    );
    ring.rotation.x = -Math.PI / 2;
    ring.position.set(x, 0.06, z);
    ring.userData = { born: performance.now() };
    this.scene.add(ring);
    this._ripples.push(ring);
  }

  /* ---------------- 渲染循环 ---------------- */

  start() {
    this._rendererLoop();
  }

  _rendererLoop() {
    if (this._stopped) return;
    requestAnimationFrame(() => this._rendererLoop());

    const dt = this._clock.getDelta();
    const elapsed = this._clock.elapsedTime;

    // 粒子缓慢旋转与呼吸
    this.particles.points.rotation.y = elapsed * 0.012;
    this.particles.material.opacity = 0.7 + Math.sin(elapsed * 0.6) * 0.15;
    // 彩色补光漂移
    this.moodLight.position.x = 12 + Math.sin(elapsed * 0.25) * 8;
    this.moodLight.position.z = -6 + Math.cos(elapsed * 0.3) * 6;

    // 涟漪
    for (let i = this._ripples.length - 1; i >= 0; i--) {
      const r = this._ripples[i];
      const age = (performance.now() - r.userData.born) / 1000;
      if (age > 1.3) {
        this.scene.remove(r);
        this._ripples.splice(i, 1);
        continue;
      }
      const t = age / 1.3;
      r.scale.setScalar(0.4 + t * 3.4);
      r.material.opacity = 0.9 * (1 - t);
    }

    // 用户动画（柱体成长、键帽按压等）
    for (const fn of this._animations) fn(dt, elapsed);

    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }

  _onResize() {
    const w = window.innerWidth, h = window.innerHeight;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
  }

  destroy() {
    this._stopped = true;
    this.controls.dispose();
    this.renderer.dispose();
    if (this.renderer.domElement.parentElement === this.container) {
      this.container.removeChild(this.renderer.domElement);
    }
  }
}