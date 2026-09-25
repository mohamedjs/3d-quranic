// Cinematic third-person camera.
// - critically damped spring toward an orbit point behind the player (natural lag)
// - slight look-ahead in the walking direction, shoulder offset, human eye height
// - pulls in when a wall or the ground is between player and camera
// - cinematic shots (dialogue / Quran) blend in with a slower spring and a faint drift
// - zoom: the boom length eases (in log space) toward the player's chosen distance, from a
//   close follow (~2.6 m) out to a bird's-eye view (60 m); on the way out the pitch leans
//   toward ~68° and the shoulder offset fades, so far out it looks down over the village
import * as THREE from 'three';
import { groundAt } from '../terrain/heightfield.js';
import { refs } from '../systems/refs.js';

export const ZOOM_MIN = 2.6, ZOOM_MAX = 60, ZOOM_DEFAULT = 5.2;
const TOP_PITCH = 1.19;                       // ~68°: near top-down, still shows house fronts
const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
const _right = new THREE.Vector3(), _back = new THREE.Vector3();

const _goal = new THREE.Vector3(), _look = new THREE.Vector3(), _dir = new THREE.Vector3(), _ray = new THREE.Raycaster();

export class CameraRig {
  constructor(camera, player) {
    this.camera = camera; this.player = player;
    this.vel = new THREE.Vector3(); this.lookPos = new THREE.Vector3(); this.lookVel = new THREE.Vector3();
    this.shot = null;          // { pos, look, stiffness } while a cinematic is active
    this.blockers = [];        // meshes the camera must not pass through
    this.t = 0;
    this.dist = player.dist ?? ZOOM_DEFAULT;   // smoothed boom length (player.dist is the target)
  }
  // 0 = close follow … 1 = bird's-eye
  get zoom() { return smooth(7, 40, this.dist); }
  // critically damped spring (no overshoot), stiffness ω
  static spring(x, v, target, w, dt) {
    const k = w * w, d = 2 * w;
    v.addScaledVector(_dir.subVectors(target, x), k * dt).multiplyScalar(Math.max(0, 1 - d * dt));
    x.addScaledVector(v, dt);
  }
  snap() { this.update(1 / 60, true); }
  update(dt, snap = false) {
    const p = this.player, cam = this.camera; this.t += dt;
    const target = THREE.MathUtils.clamp(p.dist, ZOOM_MIN, ZOOM_MAX);
    this.dist = snap ? target : Math.exp(THREE.MathUtils.lerp(Math.log(this.dist), Math.log(target), 1 - Math.exp(-dt * 5)));
    const z = this.zoom;
    let w;
    if (this.shot) {
      const drift = 0.03;
      _goal.copy(this.shot.pos).add(_dir.set(Math.sin(this.t * 0.31) * drift, Math.sin(this.t * 0.47) * drift * 0.6, Math.cos(this.t * 0.27) * drift));
      _look.copy(this.shot.look);
      w = this.shot.stiffness ?? 2.2;
    } else {
      _look.copy(p.pos).add(_dir.set(0, 1.25 - 0.75 * z, 0)).addScaledVector(p.vel, 0.18 + 0.25 * z);
      const pitch = THREE.MathUtils.lerp(p.pitch, TOP_PITCH, z), cp = Math.cos(pitch);
      _right.set(Math.cos(p.yaw), 0, -Math.sin(p.yaw));
      _back.set(Math.sin(p.yaw) * cp, Math.sin(pitch), Math.cos(p.yaw) * cp);
      let dist = this.dist;
      _look.addScaledVector(_right, 0.35 * (1 - z));          // over-the-shoulder up close, centred from above
      // occlusion: shorten the boom if a wall/rock sits between look point and camera. Only
      // up close: from high above a roof edge crossing the ray is brief, and snapping a 60 m
      // boom down to the roof would be far more jarring than the glimpse it hides.
      if (this.blockers.length && dist < 16) {
        _ray.set(_look, _back); _ray.far = dist;
        const hit = _ray.intersectObjects(this.blockers, false)[0];
        if (hit) dist = Math.max(1.2, hit.distance - 0.35);
      }
      _goal.copy(_look).addScaledVector(_back, dist);
      w = 6.5;
    }
    _goal.y = Math.max(_goal.y, groundAt(_goal.x, _goal.z) + 0.45);
    if (snap) { cam.position.copy(_goal); this.lookPos.copy(_look); this.vel.set(0, 0, 0); this.lookVel.set(0, 0, 0); }
    else {
      const steps = Math.ceil(dt / (1 / 120)), h = dt / steps;  // sub-step: stable at low frame rates
      for (let i = 0; i < steps; i++) { CameraRig.spring(cam.position, this.vel, _goal, w, h); CameraRig.spring(this.lookPos, this.lookVel, _look, w * 1.4, h); }
    }
    cam.lookAt(this.lookPos);
    // what the camera frames, for distance-based detail (vegetation, shadows, markers, fog)
    const v = refs.view, d = cam.position.distanceTo(this.lookPos);
    v.x = this.lookPos.x; v.z = this.lookPos.z; v.dist = this.shot ? Math.min(d, 8) : d; v.zoom = this.shot ? 0 : z;   // shots look far ahead: not a zoom
    v.height = cam.position.y - groundAt(cam.position.x, cam.position.z);
  }
}
