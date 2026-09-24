// Cinematic third-person camera.
// - critically damped spring toward an orbit point behind the player (natural lag)
// - slight look-ahead in the walking direction, shoulder offset, human eye height
// - pulls in when a wall or the ground is between player and camera
// - cinematic shots (dialogue / Quran) blend in with a slower spring and a faint drift
import * as THREE from 'three';
import { groundAt } from '../terrain/heightfield.js';

const _goal = new THREE.Vector3(), _look = new THREE.Vector3(), _dir = new THREE.Vector3(), _ray = new THREE.Raycaster();

export class CameraRig {
  constructor(camera, player) {
    this.camera = camera; this.player = player;
    this.vel = new THREE.Vector3(); this.lookPos = new THREE.Vector3(); this.lookVel = new THREE.Vector3();
    this.shot = null;          // { pos, look, stiffness } while a cinematic is active
    this.blockers = [];        // meshes the camera must not pass through
    this.t = 0;
  }
  // critically damped spring (no overshoot), stiffness ω
  static spring(x, v, target, w, dt) {
    const k = w * w, d = 2 * w;
    v.addScaledVector(_dir.subVectors(target, x), k * dt).multiplyScalar(Math.max(0, 1 - d * dt));
    x.addScaledVector(v, dt);
  }
  snap() { this.update(1 / 60, true); }
  update(dt, snap = false) {
    const p = this.player, cam = this.camera; this.t += dt;
    let w;
    if (this.shot) {
      const drift = 0.03;
      _goal.copy(this.shot.pos).add(_dir.set(Math.sin(this.t * 0.31) * drift, Math.sin(this.t * 0.47) * drift * 0.6, Math.cos(this.t * 0.27) * drift));
      _look.copy(this.shot.look);
      w = this.shot.stiffness ?? 2.2;
    } else {
      _look.copy(p.pos).add(_dir.set(0, 1.25, 0)).addScaledVector(p.vel, 0.18);
      const cp = Math.cos(p.pitch), right = new THREE.Vector3(Math.cos(p.yaw), 0, -Math.sin(p.yaw));
      const back = new THREE.Vector3(Math.sin(p.yaw) * cp, Math.sin(p.pitch), Math.cos(p.yaw) * cp);
      let dist = p.dist;
      _look.addScaledVector(right, 0.35);                   // over-the-shoulder, not dead centre
      // occlusion: shorten the boom if a wall/rock sits between look point and camera
      if (this.blockers.length) {
        _ray.set(_look, back); _ray.far = dist;
        const hit = _ray.intersectObjects(this.blockers, false)[0];
        if (hit) dist = Math.max(1.2, hit.distance - 0.35);
      }
      _goal.copy(_look).addScaledVector(back, dist);
      w = 6.5;
    }
    _goal.y = Math.max(_goal.y, groundAt(_goal.x, _goal.z) + 0.45);
    if (snap) { cam.position.copy(_goal); this.lookPos.copy(_look); this.vel.set(0, 0, 0); this.lookVel.set(0, 0, 0); }
    else {
      const steps = Math.ceil(dt / (1 / 120)), h = dt / steps;  // sub-step: stable at low frame rates
      for (let i = 0; i < steps; i++) { CameraRig.spring(cam.position, this.vel, _goal, w, h); CameraRig.spring(this.lookPos, this.lookVel, _look, w * 1.4, h); }
    }
    cam.lookAt(this.lookPos);
  }
}
