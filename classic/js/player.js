// Third-person movement: keys relative to the camera, or tap/click the ground to walk there.
import * as THREE from 'three';
import { groundAt, HALF } from './terrain.js';

const WALK = 3.4, RUN = 6.2, RADIUS = 0.35;

export class Player {
  constructor(rig, camera, dom, colliders, terrain) {
    Object.assign(this, { rig, camera, dom, colliders, terrain });
    this.pos = new THREE.Vector3(); this.vel = new THREE.Vector3(); this.facing = 0; this.speed = 0;
    this.yaw = Math.PI; this.pitch = 0.32; this.dist = 6.5;  // camera orbit
    this.keys = new Set(); this.target = null; this.enabled = false; this.stepPhase = 0;
    this.camGoal = null; // set by cinematics: { pos, look }
    this.camLook = new THREE.Vector3();
    this.marker = new THREE.Mesh(new THREE.RingGeometry(0.25, 0.38, 24).rotateX(-Math.PI / 2),
      new THREE.MeshBasicMaterial({ color: 0xffe08a, transparent: true, opacity: 0.8, depthWrite: false }));
    this.marker.visible = false;
    rig.root.parent?.add(this.marker);
    this.bind();
  }
  bind() {
    addEventListener('keydown', e => { if (!e.repeat) this.keys.add(e.code); if (this.enabled && /Arrow|Key[WASD]/.test(e.code)) this.target = null; });
    addEventListener('keyup', e => this.keys.delete(e.code));
    addEventListener('blur', () => this.keys.clear());
    let down = null;
    this.dom.addEventListener('pointerdown', e => { down = { x: e.clientX, y: e.clientY, moved: 0 }; this.dom.setPointerCapture(e.pointerId); });
    this.dom.addEventListener('pointermove', e => {
      if (!down) return;
      const dx = e.movementX ?? 0, dy = e.movementY ?? 0;
      down.moved += Math.abs(dx) + Math.abs(dy);
      if (down.moved > 6 && this.enabled) { this.yaw -= dx * 0.005; this.pitch = THREE.MathUtils.clamp(this.pitch + dy * 0.004, -0.1, 1.1); }
    });
    this.dom.addEventListener('pointerup', e => {
      if (down && down.moved <= 6 && this.enabled) this.tapTo(e.clientX, e.clientY);
      down = null;
    });
    this.dom.addEventListener('wheel', e => { this.dist = THREE.MathUtils.clamp(this.dist + e.deltaY * 0.005, 3, 14); }, { passive: true });
  }
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
    this.updateCamera(dt);
  }
  lookAtYaw(yaw) { this.facing = yaw; }
  updateCamera(dt) {
    const cam = this.camera, goal = new THREE.Vector3(), look = new THREE.Vector3();
    if (this.camGoal) { goal.copy(this.camGoal.pos); look.copy(this.camGoal.look); }
    else {
      look.copy(this.pos).add(new THREE.Vector3(0, 1.15, 0));
      const cp = Math.cos(this.pitch);
      goal.set(Math.sin(this.yaw) * cp, Math.sin(this.pitch), Math.cos(this.yaw) * cp).multiplyScalar(this.dist).add(look);
      goal.y = Math.max(goal.y, groundAt(goal.x, goal.z) + 0.6);
    }
    const k = 1 - Math.exp(-dt * (this.camGoal ? this.camGoal.speed ?? 2 : 8));
    cam.position.lerp(goal, k); this.camLook.lerp(look, k);
    cam.lookAt(this.camLook);
  }
  // steps for footstep sounds: returns true once per footfall
  footfall(dt) {
    if (this.speed < 0.5) return false;
    const prev = Math.sin(this.rig.phase - dt * (5 + this.speed * 2.2)), now = Math.sin(this.rig.phase);
    return Math.sign(prev) !== Math.sign(now);
  }
}
