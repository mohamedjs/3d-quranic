// A small oil lantern (فانوس) hung on a wall bracket: toon wood/metal frame, a warm unlit
// glass body and an additive glow sprite (bloom makes it shine). No real light — cheap.
// Used by encounter props: { "model": "lantern", "position": [x, z], "rot": yaw, "y": 1.9 }
import * as THREE from 'three';
import { toonMaterial } from '../shaders/toon.js';

let glowTex;
function glow() {
  if (glowTex) return glowTex;
  const c = document.createElement('canvas'); c.width = c.height = 64; const x = c.getContext('2d');
  const g = x.createRadialGradient(32, 32, 2, 32, 32, 32);
  g.addColorStop(0, 'rgba(255,214,130,0.95)'); g.addColorStop(0.35, 'rgba(255,170,70,0.35)'); g.addColorStop(1, 'rgba(255,150,50,0)');
  x.fillStyle = g; x.fillRect(0, 0, 64, 64);
  glowTex = new THREE.CanvasTexture(c); glowTex.colorSpace = THREE.SRGBColorSpace;
  return glowTex;
}

// rot: the way the wall faces (the bracket sticks out along it); y: hanging height above ground
export function makeLantern({ x, y, z, rot = 0 }) {
  const root = new THREE.Group(); root.position.set(x, y, z); root.rotation.y = rot;
  const metal = toonMaterial('proc_lantern_metal', { color: 0x3b2a1a }), wood = toonMaterial('proc_lantern_wood', { color: 0x6a4a2e });
  const add = (geo, mat, px, py, pz) => { const m = new THREE.Mesh(geo, mat); m.position.set(px, py, pz); m.castShadow = mat !== glass; root.add(m); return m; };
  const glass = new THREE.MeshBasicMaterial({ color: 0xffd488, toneMapped: false });
  add(new THREE.BoxGeometry(0.08, 0.08, 0.42), wood, 0, 0.32, 0.18);              // bracket from the wall
  add(new THREE.CylinderGeometry(0.012, 0.012, 0.16, 5), metal, 0, 0.22, 0.36);     // hook
  add(new THREE.CylinderGeometry(0.1, 0.12, 0.2, 6), glass, 0, 0.02, 0.36);         // glowing glass
  add(new THREE.ConeGeometry(0.15, 0.13, 6), metal, 0, 0.18, 0.36);                 // cap
  add(new THREE.CylinderGeometry(0.13, 0.1, 0.04, 6), metal, 0, -0.1, 0.36);        // base
  const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: glow(), blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, toneMapped: false, fog: false }));
  halo.position.set(0, 0.02, 0.36); halo.scale.setScalar(0.9); root.add(halo);
  return root;
}
