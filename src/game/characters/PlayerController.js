// Third-person movement: keys or the touch joystick relative to the camera, or tap/click the
// ground to walk there (the game's walk-to-the-story autopilot steers through `target` too).
// Owns the orbit input (yaw/pitch/dist); the CameraRig turns that into a smooth camera.
import * as THREE from 'three';
import { groundAt, HALF } from '../terrain/heightfield.js';
import { ZOOM_MIN, ZOOM_MAX, ZOOM_DEFAULT } from '../camera/CameraRig.js';
import { createJoystick, isTouchDevice, STICK_R } from '../ui/joystick.js';

// zoom keys: + / PageDown / Z bring the camera down (in); − / PageUp / Q lift it (out)
const ZOOM_IN = ['Equal', 'NumpadAdd', 'PageDown', 'KeyZ'], ZOOM_OUT = ['Minus', 'NumpadSubtract', 'PageUp', 'KeyQ'];
// wheel / pinch go through overlays that have their own scrolling or zoom
const OWN_WHEEL = '#panel, #quran, #dialogue, #title, #reward, #scene';

export const WALK = 2.3, RUN = 4.6;          // a child's pace
const RADIUS = 0.3;
const DEAD = 0.12, TAP_MS = 500, TAP_PX = 10;   // joystick dead-zone (of its radius) · what counts as a tap on touch
// analog stick → speed: a small push strolls, most of the travel walks, the last bit runs
const stickSpeed = m => (m < 0.72 ? WALK * (0.3 + 0.7 * m / 0.72) : WALK + (RUN - WALK) * THREE.MathUtils.smoothstep(m, 0.72, 1));

export class PlayerController {
  constructor(rig, camera, dom, colliders, terrain, scene) {
    Object.assign(this, { rig, camera, dom, colliders, terrain });
    this.pos = new THREE.Vector3(); this.vel = new THREE.Vector3(); this.facing = 0; this.speed = 0;
    this.yaw = Math.PI; this.pitch = 0.22; this.dist = ZOOM_DEFAULT;  // camera orbit (dist: target boom length)
    this.zoomHold = 0;                                                // +1 out / −1 in while a HUD zoom button is held
    this.keys = new Set(); this.target = null; this.enabled = false; this.stepPhase = 0;
    this.stick = { x: 0, y: 0 }; this.stickRaw = { x: 0, y: 0 };     // joystick: raw from the finger, eased copy drives
    this.lookVel = { yaw: 0, pitch: 0 };                               // camera coast after a touch flick (rad/s)
    this.onManual = null;                                              // set by the game: manual input cancels the autopilot
    this.touch = isTouchDevice();
    if (typeof document !== 'undefined') { this.joy = createJoystick(); document.body.classList.toggle('touch', this.touch); }
    this.marker = new THREE.Mesh(new THREE.RingGeometry(0.25, 0.38, 24).rotateX(-Math.PI / 2),
      new THREE.MeshBasicMaterial({ color: 0xffe08a, transparent: true, opacity: 0.8, depthWrite: false }));
    this.marker.visible = false;
    scene.add(this.marker);
    this.bind();
  }
  // manual control (movement keys, joystick, tap-to-walk) cancels a walk target and the autopilot
  interrupt() { this.target = null; this.onManual?.(); }
  bind() {
    addEventListener('keydown', e => {
      if (!e.repeat) this.keys.add(e.code);
      if (this.enabled && /Arrow|Key[WASD]/.test(e.code)) this.interrupt();
      if (this.enabled && (ZOOM_IN.includes(e.code) || ZOOM_OUT.includes(e.code))) e.preventDefault();   // no page scroll / browser zoom
    });
    addEventListener('keyup', e => this.keys.delete(e.code));
    addEventListener('blur', () => { this.keys.clear(); this.zoomHold = 0; endStick(); });
    // Pointers (each finger tracked by pointerId, so they combine):
    //  · touch in the left half → floating joystick (a quick tap there still walks to the spot)
    //  · one finger elsewhere / mouse → drag to orbit (touch keeps some inertia), tap to walk
    //  · two orbit fingers → pinch to zoom (a second finger landing right after the stick finger
    //    turns both into a pinch, so a two-finger pinch works anywhere)
    const pts = this.pointers = new Map();
    let pinch = null, stickId = null;
    const looks = () => [...pts.values()].filter(p => p.role === 'look');
    const spread = () => { const [a, b] = looks(); return Math.hypot(a.x - b.x, a.y - b.y) || 1; };
    const endStick = () => { const s = pts.get(stickId); if (s) s.role = 'dead'; stickId = null; this.stickRaw.x = this.stickRaw.y = 0; this.joy?.hide(); };
    this.endStick = endStick;
    const stopLook = () => { this.lookVel.yaw = this.lookVel.pitch = 0; };
    this.dom.addEventListener('contextmenu', e => e.preventDefault());       // no long-press menu on the canvas
    this.dom.addEventListener('pointerdown', e => {
      const touch = e.pointerType === 'touch';
      if (touch && !this.touch) { this.touch = true; document.body.classList.add('touch'); }
      const now = e.timeStamp, p = { x: e.clientX, y: e.clientY, x0: e.clientX, y0: e.clientY, t0: now, tm: now, lastMove: 0, moved: 0, touch, role: 'look' };
      pts.set(e.pointerId, p);
      try { this.dom.setPointerCapture(e.pointerId); } catch { /* synthetic events */ }
      stopLook();                                                             // a new touch catches a coasting camera
      if (touch && this.enabled && stickId === null && e.clientX < innerWidth / 2 && !looks().some(q => q !== p)) {
        p.role = 'stick'; stickId = e.pointerId;
        const c = this.joy?.show(e.clientX, e.clientY);
        p.cx = c?.x ?? e.clientX; p.cy = c?.y ?? e.clientY;
      } else if (touch && stickId !== null) {
        const s = pts.get(stickId);
        if (s && now - s.t0 < 180 && s.moved < TAP_PX) { endStick(); s.role = 'look'; }   // it was a pinch
      }
      if (looks().length === 2) { pinch = { d0: spread(), dist0: this.dist }; for (const q of looks()) q.moved = 1e9; }   // a pinch is never a tap
    });
    this.dom.addEventListener('pointermove', e => {
      const p = pts.get(e.pointerId); if (!p || p.role === 'dead') return;
      const dx = e.clientX - p.x, dy = e.clientY - p.y; p.x = e.clientX; p.y = e.clientY;
      p.moved = Math.max(p.moved, Math.hypot(p.x - p.x0, p.y - p.y0));
      if (p.role === 'stick') {
        let kx = p.x - p.x0, ky = p.y - p.y0; const l = Math.hypot(kx, ky);
        if (l > STICK_R) { kx *= STICK_R / l; ky *= STICK_R / l; }
        this.joy?.move(kx, ky);
        this.stickRaw.x = kx / STICK_R; this.stickRaw.y = -ky / STICK_R;
        if (!p.drove && l > STICK_R * DEAD) { p.drove = true; this.interrupt(); }
        return;
      }
      if (pinch && looks().length >= 2) { if (this.enabled) this.dist = THREE.MathUtils.clamp(pinch.dist0 * pinch.d0 / spread(), ZOOM_MIN, ZOOM_MAX); return; }
      if (p.moved <= (p.touch ? TAP_PX : 6) || !this.enabled) return;
      const ky = p.touch ? 0.0078 : 0.005, kp = p.touch ? 0.0055 : 0.004;   // kids' thumbs: a bit livelier on touch
      this.yaw -= dx * ky; this.pitch = THREE.MathUtils.clamp(this.pitch + dy * kp, -0.05, 1.0);
      if (p.touch) {                                                          // velocity estimate for the release coast
        const now = e.timeStamp, h = Math.max(0.008, (now - p.tm) / 1000); p.tm = now; p.lastMove = now;
        const lv = this.lookVel, a = 0.45;
        lv.yaw = THREE.MathUtils.clamp(lv.yaw * (1 - a) + (-dx * ky / h) * a, -5, 5);
        lv.pitch = THREE.MathUtils.clamp(lv.pitch * (1 - a) + (dy * kp / h) * a, -3, 3);
      }
    });
    const up = e => {
      const p = pts.get(e.pointerId); if (!p) return;
      pts.delete(e.pointerId);
      const now = e.timeStamp;                                                 // event times, not handler times
      const tap = e.type === 'pointerup' && this.enabled && (p.touch ? now - p.t0 < TAP_MS && p.moved <= TAP_PX : p.moved <= 6);
      if (p.role === 'stick') { endStick(); if (tap) this.tapTo(e.clientX, e.clientY); }
      else if (p.role === 'look') {
        if (tap && !pinch && !looks().length && stickId === null) this.tapTo(e.clientX, e.clientY);
        if (!p.touch || pinch || now - p.lastMove > 90) stopLook();           // only a flick coasts
      }
      if (looks().length < 2) pinch = null;
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
    // Safari pinch arrives as gesture events: never let it zoom the page; a trackpad pinch
    // (no touches on the canvas) zooms the camera
    let g0 = null;
    addEventListener('gesturestart', e => { e.preventDefault(); if (!this.enabled || pts.size) return; g0 = this.dist; });
    addEventListener('gesturechange', e => { e.preventDefault(); if (g0 === null) return; this.dist = THREE.MathUtils.clamp(g0 / (e.scale || 1), ZOOM_MIN, ZOOM_MAX); });
    addEventListener('gestureend', () => { g0 = null; });
  }
  zoomBy(k) { this.dist = THREE.MathUtils.clamp(this.dist * k, ZOOM_MIN, ZOOM_MAX); }
  tapTo(cx, cy) {
    this.interrupt();
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
    const ek = 1 - Math.exp(-dt * 16), st = this.stick;                   // eased stick: no jerks from a twitchy thumb
    st.x += (this.stickRaw.x - st.x) * ek; st.y += (this.stickRaw.y - st.y) * ek;
    if (!this.enabled && this.stickRaw.x + this.stickRaw.y !== 0) this.endStick?.();
    let pace = WALK;
    if (this.enabled) {
      const k = this.keys, f = (k.has('KeyW') || k.has('ArrowUp')) - (k.has('KeyS') || k.has('ArrowDown'));
      const s = (k.has('KeyD') || k.has('ArrowRight')) - (k.has('KeyA') || k.has('ArrowLeft'));
      const sm = Math.hypot(st.x, st.y);
      const fw = new THREE.Vector3(-Math.sin(this.yaw), 0, -Math.cos(this.yaw)), rt = new THREE.Vector3(-fw.z, 0, fw.x);
      if (f || s) {
        want.addScaledVector(fw, f).addScaledVector(rt, s).normalize();
        pace = k.has('ShiftLeft') || k.has('ShiftRight') ? RUN : WALK;
      } else if (sm > DEAD) {                                             // joystick: camera-relative, analog
        want.addScaledVector(fw, st.y).addScaledVector(rt, st.x).normalize();
        pace = stickSpeed(Math.min(1, (sm - DEAD) / (1 - DEAD)));
      } else if (this.target) {
        want.subVectors(this.target, this.pos).setY(0);
        const d = want.length();
        if (d < 0.35) { this.target = null; want.set(0, 0, 0); } else want.normalize();
        pace = k.has('ShiftLeft') || k.has('ShiftRight') || d > 18 ? RUN : WALK;
      }
      // camera coast after a flick (touch), fading out over ~½ s
      const lv = this.lookVel;
      if ((lv.yaw || lv.pitch) && ![...(this.pointers?.values() ?? [])].some(p => p.role === 'look')) {
        this.yaw += lv.yaw * dt; this.pitch = THREE.MathUtils.clamp(this.pitch + lv.pitch * dt, -0.05, 1.0);
        const dk = Math.exp(-dt * 4.5); lv.yaw *= dk; lv.pitch *= dk;
        if (Math.abs(lv.yaw) + Math.abs(lv.pitch) < 0.02) lv.yaw = lv.pitch = 0;
      }
    }
    if (this.enabled) {                                   // held zoom keys / HUD buttons: smooth, ~1.5 s from close to bird's-eye
      const k = this.keys, dir = ZOOM_OUT.some(c => k.has(c)) - ZOOM_IN.some(c => k.has(c)) + this.zoomHold;
      if (dir) this.zoomBy(Math.exp(Math.sign(dir) * dt * 1.9));
    }
    want.multiplyScalar(pace);
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
