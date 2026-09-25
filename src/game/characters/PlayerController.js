// Third-person movement: keys relative to the camera, or tap/click the ground to walk there.
// Owns the orbit input (yaw/pitch/dist); the CameraRig turns that into a smooth camera.
import * as THREE from 'three';
import { groundAt, HALF } from '../terrain/heightfield.js';
import { ZOOM_MIN, ZOOM_MAX, ZOOM_DEFAULT } from '../camera/CameraRig.js';

// zoom keys: + / PageDown / Z bring the camera down (in); − / PageUp / Q lift it (out)
const ZOOM_IN = ['Equal', 'NumpadAdd', 'PageDown', 'KeyZ'], ZOOM_OUT = ['Minus', 'NumpadSubtract', 'PageUp', 'KeyQ'];
// wheel / pinch go through overlays that have their own scrolling or zoom
const OWN_WHEEL = '#panel, #quran, #dialogue, #title, #reward, #scene';

const WALK = 2.3, RUN = 4.6, RADIUS = 0.3;   // a child's pace

export class PlayerController {
  constructor(rig, camera, dom, colliders, terrain, scene) {
    Object.assign(this, { rig, camera, dom, colliders, terrain });
    this.pos = new THREE.Vector3(); this.vel = new THREE.Vector3(); this.facing = 0; this.speed = 0;
    this.yaw = Math.PI; this.pitch = 0.22; this.dist = ZOOM_DEFAULT;  // camera orbit (dist: target boom length)
    this.zoomHold = 0;                                                // +1 out / −1 in while a HUD zoom button is held
    this.keys = new Set(); this.target = null; this.enabled = false; this.stepPhase = 0;
    this.marker = new THREE.Mesh(new THREE.RingGeometry(0.25, 0.38, 24).rotateX(-Math.PI / 2),
      new THREE.MeshBasicMaterial({ color: 0xffe08a, transparent: true, opacity: 0.8, depthWrite: false }));
    this.marker.visible = false;
    scene.add(this.marker);
    this.bind();
  }
  bind() {
    addEventListener('keydown', e => {
      if (!e.repeat) this.keys.add(e.code);
      if (this.enabled && /Arrow|Key[WASD]/.test(e.code)) this.target = null;
      if (this.enabled && (ZOOM_IN.includes(e.code) || ZOOM_OUT.includes(e.code))) e.preventDefault();   // no page scroll / browser zoom
    });
    addEventListener('keyup', e => this.keys.delete(e.code));
    addEventListener('blur', () => { this.keys.clear(); this.zoomHold = 0; });
    // one finger / mouse: drag to orbit, tap to walk · two fingers: pinch to zoom
    const pts = new Map();
    let down = null, pinch = null;
    const spread = () => { const [a, b] = [...pts.values()]; return Math.hypot(a.x - b.x, a.y - b.y) || 1; };
    this.dom.addEventListener('pointerdown', e => {
      pts.set(e.pointerId, { x: e.clientX, y: e.clientY });
      try { this.dom.setPointerCapture(e.pointerId); } catch { /* synthetic events */ }
      if (pts.size === 1) down = { moved: 0 };
      else if (pts.size === 2) { pinch = { d0: spread(), dist0: this.dist }; if (down) down.moved = 1e9; }   // a pinch is never a tap
    });
    this.dom.addEventListener('pointermove', e => {
      const pt = pts.get(e.pointerId); if (!pt) return;
      const dx = e.clientX - pt.x, dy = e.clientY - pt.y; pt.x = e.clientX; pt.y = e.clientY;
      if (pinch && pts.size >= 2) { if (this.enabled) this.dist = THREE.MathUtils.clamp(pinch.dist0 * pinch.d0 / spread(), ZOOM_MIN, ZOOM_MAX); return; }
      if (!down) return;
      down.moved += Math.abs(dx) + Math.abs(dy);
      if (down.moved > 6 && this.enabled) { this.yaw -= dx * 0.005; this.pitch = THREE.MathUtils.clamp(this.pitch + dy * 0.004, -0.05, 1.0); }
    });
    const up = e => {
      if (!pts.delete(e.pointerId)) return;
      if (e.type === 'pointerup' && down && !pinch && pts.size === 0 && down.moved <= 6 && this.enabled) this.tapTo(e.clientX, e.clientY);
      if (pts.size < 2) pinch = null;
      if (pts.size === 0) down = null;
    };
    this.dom.addEventListener('pointerup', up);
    this.dom.addEventListener('pointercancel', up);
    // mouse wheel, and trackpad pinch (arrives as ctrl+wheel): exponential, so each notch
    // feels the same close up and far out
    addEventListener('wheel', e => {
      if (!this.enabled || e.target?.closest?.(OWN_WHEEL)) return;
      if (e.ctrlKey) e.preventDefault();                 // otherwise the browser zooms the page
      const d = e.deltaY * (e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? 400 : 1);
      this.zoomBy(Math.exp(THREE.MathUtils.clamp(d, -300, 300) * (e.ctrlKey ? 0.012 : 0.0018)));
    }, { passive: false });
    // Safari trackpad pinch arrives as gesture events (touch pinches are handled above)
    let g0 = null;
    addEventListener('gesturestart', e => { if (!this.enabled || pts.size) return; e.preventDefault(); g0 = this.dist; });
    addEventListener('gesturechange', e => { if (g0 === null) return; e.preventDefault(); this.dist = THREE.MathUtils.clamp(g0 / (e.scale || 1), ZOOM_MIN, ZOOM_MAX); });
    addEventListener('gestureend', () => { g0 = null; });
  }
  zoomBy(k) { this.dist = THREE.MathUtils.clamp(this.dist * k, ZOOM_MIN, ZOOM_MAX); }
  tapTo(cx, cy) {
    const ray = new THREE.Raycaster(), ndc = new THREE.Vector2(cx / innerWidth * 2 - 1, -(cy / innerHeight) * 2 + 1);
    ray.setFromCamera(ndc, this.camera);
    const hit = ray.intersectObject(this.terrain, false)[0];
    if (!hit) return;
    this.target = hit.point.clone();
    this.marker.position.set(hit.point.x, groundAt(hit.point.x, hit.point.z) + 0.05, hit.point.z);
    this.marker.visible = true; this.marker.scale.setScalar(1.4);
  }
  place(x, z, facing = 0) {
    this.pos.set(x, groundAt(x, z), z); this.facing = facing; this.yaw = facing + Math.PI;
    this.rig.root.position.copy(this.pos); this.rig.root.rotation.y = facing;
  }
  blocked(x, z) {
    if (Math.abs(x) > HALF - 20 || Math.abs(z) > HALF - 20) return true;
    const g = groundAt(x, z);
    return g < -1.05 || g > 16;           // deep water / mountain side
  }
  pushOut(p) {
    for (const c of this.colliders) {
      const x0 = c.x0 - RADIUS, x1 = c.x1 + RADIUS, z0 = c.z0 - RADIUS, z1 = c.z1 + RADIUS;
      if (p.x <= x0 || p.x >= x1 || p.z <= z0 || p.z >= z1) continue;
      const dx = Math.min(p.x - x0, x1 - p.x), dz = Math.min(p.z - z0, z1 - p.z);
      if (dx < dz) p.x = p.x - x0 < x1 - p.x ? x0 : x1; else p.z = p.z - z0 < z1 - p.z ? z0 : z1;
    }
  }
  update(dt, t) {
    const want = new THREE.Vector3();
    if (this.enabled) {
      const k = this.keys, f = (k.has('KeyW') || k.has('ArrowUp')) - (k.has('KeyS') || k.has('ArrowDown'));
      const s = (k.has('KeyD') || k.has('ArrowRight')) - (k.has('KeyA') || k.has('ArrowLeft'));
      if (f || s) {
        const fw = new THREE.Vector3(-Math.sin(this.yaw), 0, -Math.cos(this.yaw)), rt = new THREE.Vector3(-fw.z, 0, fw.x);
        want.addScaledVector(fw, f).addScaledVector(rt, s).normalize();
      } else if (this.target) {
        want.subVectors(this.target, this.pos).setY(0);
        if (want.length() < 0.35) { this.target = null; want.set(0, 0, 0); } else want.normalize();
      }
    }
    if (this.enabled) {                                   // held zoom keys / HUD buttons: smooth, ~1.5 s from close to bird's-eye
      const k = this.keys, dir = ZOOM_OUT.some(c => k.has(c)) - ZOOM_IN.some(c => k.has(c)) + this.zoomHold;
      if (dir) this.zoomBy(Math.exp(Math.sign(dir) * dt * 1.9));
    }
    const run = this.keys.has('ShiftLeft') || this.keys.has('ShiftRight') || (this.target && this.pos.distanceTo(this.target) > 18);
    want.multiplyScalar(run ? RUN : WALK);
    this.vel.lerp(want, 1 - Math.exp(-dt * 10));
    const nx = this.pos.x + this.vel.x * dt, nz = this.pos.z + this.vel.z * dt;
    const next = new THREE.Vector3(nx, 0, nz);
    if (this.blocked(nx, nz)) { next.set(this.pos.x, 0, this.pos.z); this.vel.multiplyScalar(0.2); this.target = null; }
    this.pushOut(next);
    this.pos.set(next.x, THREE.MathUtils.lerp(this.pos.y, groundAt(next.x, next.z), 1 - Math.exp(-dt * 20)), next.z);
    this.speed = Math.hypot(this.vel.x, this.vel.z);
    if (this.speed > 0.2) {
      const aim = Math.atan2(this.vel.x, this.vel.z);
      let d = aim - this.facing; d = Math.atan2(Math.sin(d), Math.cos(d));
      this.facing += d * (1 - Math.exp(-dt * 12));
    }
    this.rig.root.position.copy(this.pos); this.rig.root.rotation.y = this.facing;
    this.rig.animate(dt, t, this.speed);
    if (this.marker.visible) { this.marker.scale.multiplyScalar(1 - dt * 1.5); if (!this.target || this.marker.scale.x < 0.4) this.marker.visible = false; }
  }
  // steps for footstep sounds: returns true once per footfall
  footfall(dt) {
    if (this.speed < 0.5) return false;
    const prev = Math.sin(this.rig.phase - dt * (5 + this.speed * 2.2)), now = Math.sin(this.rig.phase);
    return Math.sign(prev) !== Math.sign(now);
  }
}
