// Stylised characters built from primitives, with procedural walk/idle/talk animation.
import * as THREE from 'three';

const matCache = new Map();
const M = hex => {
  if (!matCache.has(hex)) matCache.set(hex, new THREE.MeshStandardMaterial({ color: hex, roughness: 0.85 }));
  return matCache.get(hex);
};
function part(geo, hex, x = 0, y = 0, z = 0, parent) {
  const m = new THREE.Mesh(geo, M(hex));
  m.position.set(x, y, z); m.castShadow = true; m.receiveShadow = true;
  parent?.add(m);
  return m;
}
const pivot = (parent, x, y, z) => { const g = new THREE.Group(); g.position.set(x, y, z); parent.add(g); return g; };
function limb(parent, x, y, len, r, hex, handHex) {
  const p = pivot(parent, x, y, 0);
  part(new THREE.CapsuleGeometry(r, len, 4, 8), hex, 0, -len / 2 - r * 0.5, 0, p);
  if (handHex) part(new THREE.SphereGeometry(r * 1.05, 8, 6), handHex, 0, -len - r * 1.2, 0, p);
  return p;
}
function face(head, r, skin, opts = {}) {
  for (const s of [-1, 1]) {
    part(new THREE.SphereGeometry(r * 0.13, 8, 6), 0xffffff, s * r * 0.36, r * 0.12, r * 0.86, head).scale.z = 0.5;
    part(new THREE.SphereGeometry(r * 0.08, 8, 6), 0x2a1a10, s * r * 0.36, r * 0.12, r * 0.93, head);
    part(new THREE.BoxGeometry(r * 0.3, r * 0.07, r * 0.05), opts.brow ?? 0x2a1a10, s * r * 0.36, r * 0.34, r * 0.9, head).rotation.z = -s * 0.12;
  }
  part(new THREE.SphereGeometry(r * 0.13, 8, 6), skin, 0, -r * 0.08, r * 0.98, head);
}

// The player: a village child with a scarf and a small satchel.
export function makeChild() {
  const root = new THREE.Group(), body = pivot(root, 0, 0, 0), skin = 0xc68e62;
  const legs = [-1, 1].map(s => {
    const l = limb(body, s * 0.09, 0.5, 0.3, 0.075, 0x445a78);
    part(new THREE.BoxGeometry(0.12, 0.07, 0.22), 0x5b3a21, 0, -0.5, 0.04, l);
    return l;
  });
  part(new THREE.CylinderGeometry(0.17, 0.25, 0.5, 12), 0xefe6d2, 0, 0.68, 0, body);
  part(new THREE.TorusGeometry(0.13, 0.05, 8, 16).rotateX(Math.PI / 2), 0x3f6f9f, 0, 0.93, 0, body);
  part(new THREE.BoxGeometry(0.3, 0.32, 0.14), 0x6d4a2b, 0, 0.72, -0.2, body);
  part(new THREE.BoxGeometry(0.31, 0.12, 0.15), 0x5b3a21, 0, 0.84, -0.2, body);
  const arms = [-1, 1].map(s => { const a = limb(body, s * 0.22, 0.88, 0.26, 0.055, 0xefe6d2, skin); a.rotation.z = s * 0.08; return a; });
  const head = pivot(body, 0, 1.1, 0);
  part(new THREE.SphereGeometry(0.19, 16, 12), skin, 0, 0, 0, head);
  const hair = part(new THREE.SphereGeometry(0.2, 16, 10, 0, Math.PI * 2, 0, Math.PI * 0.55), 0x1f140d, 0, 0.03, -0.01, head);
  hair.rotation.x = -0.25;
  for (const s of [-1, 1]) part(new THREE.SphereGeometry(0.05, 6, 5), skin, s * 0.19, 0, 0, head);
  face(head, 0.19, skin);
  return new Rig(root, body, head, legs, arms);
}

// NPCs share one builder: robe, head covering, optional beard and staff.
export function makeElder({ robe = 0x6b4a2e, inner = 0xefe6d2, skin = 0x9c6b48, beard = 0xeeeeea, headwear = 'turban', cloth = 0xf2efe6, band = 0x222222, staff = true, height = 1.72 } = {}) {
  const root = new THREE.Group(), s = height / 1.72, body = pivot(root, 0, 0, 0);
  body.scale.setScalar(s);
  part(new THREE.CylinderGeometry(0.2, 0.34, 1.05, 14), inner, 0, 0.52, 0.01, body);
  part(new THREE.CylinderGeometry(0.21, 0.36, 1.1, 14, 1, true, Math.PI * 0.62, Math.PI * 1.76), robe, 0, 0.58, 0, body).material.side = THREE.DoubleSide;
  part(new THREE.CylinderGeometry(0.22, 0.24, 0.3, 14), robe, 0, 1.2, 0, body);
  part(new THREE.TorusGeometry(0.22, 0.03, 6, 18).rotateX(Math.PI / 2), 0x8a6a3a, 0, 0.98, 0, body);
  const arms = [-1, 1].map(k => {
    const a = pivot(body, k * 0.27, 1.3, 0);
    part(new THREE.CylinderGeometry(0.07, 0.12, 0.55, 8), robe, 0, -0.27, 0, a);
    part(new THREE.SphereGeometry(0.065, 8, 6), skin, 0, -0.58, 0.02, a);
    a.rotation.z = k * 0.12;
    return a;
  });
  const head = pivot(body, 0, 1.55, 0);
  part(new THREE.SphereGeometry(0.17, 16, 12), skin, 0, 0, 0, head);
  face(head, 0.17, skin, { brow: beard === null ? 0x2a1a10 : beard });
  if (beard !== null) {
    part(new THREE.SphereGeometry(0.15, 12, 10), beard, 0, -0.12, 0.07, head).scale.set(1, 1.3, 0.8);
    part(new THREE.ConeGeometry(0.1, 0.22, 10).rotateX(Math.PI), beard, 0, -0.3, 0.1, head);
    part(new THREE.BoxGeometry(0.16, 0.035, 0.05), beard, 0, -0.06, 0.17, head);
  }
  if (headwear === 'turban') {
    part(new THREE.TorusGeometry(0.15, 0.07, 8, 18).rotateX(Math.PI / 2), cloth, 0, 0.1, 0, head);
    part(new THREE.SphereGeometry(0.15, 12, 8), cloth, 0, 0.15, 0, head).scale.y = 0.7;
  } else if (headwear === 'keffiyeh') {
    part(new THREE.SphereGeometry(0.19, 14, 10, 0, Math.PI * 2, 0, Math.PI * 0.6), cloth, 0, 0.02, -0.01, head);
    part(new THREE.ConeGeometry(0.26, 0.45, 14, 1, true), cloth, 0, -0.15, -0.05, head).material.side = THREE.DoubleSide;
    part(new THREE.TorusGeometry(0.17, 0.025, 6, 18).rotateX(Math.PI / 2), band, 0, 0.1, 0, head);
  } else { // hijab: covers hair and neck, face open
    part(new THREE.SphereGeometry(0.2, 16, 12, 0, Math.PI * 2, 0, Math.PI * 0.62), cloth, 0, 0.01, -0.02, head).scale.set(1, 1.05, 1.05);
    part(new THREE.CylinderGeometry(0.19, 0.3, 0.42, 16, 1, true, Math.PI * 0.2, Math.PI * 1.6), cloth, 0, -0.2, -0.01, head).material.side = THREE.DoubleSide;
  }
  let staffMesh = null;
  if (staff) { staffMesh = part(new THREE.CylinderGeometry(0.025, 0.03, 1.8, 6), 0x5e4028, 0.02, -0.25, 0.08, arms[1]); staffMesh.rotation.x = 0.1; }
  const rig = new Rig(root, body, head, [], arms);
  rig.headY = 1.55 * s + 0.15;
  return rig;
}

export function makeCamel() {
  const root = new THREE.Group(), c = 0xc49a64;
  part(new THREE.SphereGeometry(0.55, 14, 10), c, 0, 1.55, 0, root).scale.set(0.75, 0.7, 1.35);
  part(new THREE.SphereGeometry(0.38, 12, 10), c, 0, 1.95, -0.05, root).scale.set(0.9, 0.9, 1.1);
  part(new THREE.BoxGeometry(0.9, 0.08, 0.9), 0xa8322a, 0, 2.02, 0.35, root).rotation.x = 0.25;
  const neck = pivot(root, 0, 1.65, 0.65);
  part(new THREE.CylinderGeometry(0.11, 0.16, 0.9, 8), c, 0, 0.3, 0.2, neck).rotation.x = 0.7;
  const head = pivot(neck, 0, 0.72, 0.52);
  part(new THREE.BoxGeometry(0.2, 0.2, 0.45), c, 0, 0, 0.1, head);
  for (const s of [-1, 1]) part(new THREE.SphereGeometry(0.03, 6, 5), 0x1a120c, s * 0.1, 0.05, 0.1, head);
  const legs = [];
  for (const [x, z] of [[-0.22, 0.45], [0.22, 0.45], [-0.22, -0.45], [0.22, -0.45]]) {
    const l = pivot(root, x, 1.3, z);
    part(new THREE.CylinderGeometry(0.06, 0.05, 1.3, 6), c, 0, -0.65, 0, l);
    legs.push(l);
  }
  part(new THREE.CylinderGeometry(0.02, 0.04, 0.5, 5), c, 0, 1.45, -0.8, root).rotation.x = 0.4;
  root.userData.animate = t => { neck.rotation.x = Math.sin(t * 0.7) * 0.08; head.rotation.x = Math.sin(t * 5) * 0.03; };
  return root;
}

export class Rig {
  constructor(root, body, head, legs, arms) {
    Object.assign(this, { root, body, head, legs, arms, phase: 0, talking: false, headY: 1.25 });
  }
  // speed in m/s; drives the stride
  animate(dt, t, speed) {
    const k = Math.min(speed / 3.2, 1.6);
    this.phase += dt * (5 + speed * 2.2);
    const sw = Math.sin(this.phase) * 0.7 * Math.min(k, 1.1);
    this.legs.forEach((l, i) => { l.rotation.x = i ? sw : -sw; });
    this.arms.forEach((a, i) => { a.rotation.x = (i ? -sw : sw) * 0.8; });
    this.body.position.y = Math.abs(Math.cos(this.phase)) * 0.05 * k + Math.sin(t * 2) * 0.004;
    this.body.rotation.z = Math.sin(this.phase) * 0.03 * k;
    if (this.talking) { // gentle storytelling gesture with the free hand
      this.arms[0].rotation.x = -0.6 + Math.sin(t * 2.2) * 0.25;
      this.arms[0].rotation.z = -0.35 + Math.sin(t * 1.3) * 0.1;
      this.head.rotation.z = Math.sin(t * 1.7) * 0.05;
    } else if (!this.legs.length) {
      this.arms[0].rotation.x *= 0.9; this.arms[0].rotation.z = THREE.MathUtils.lerp(this.arms[0].rotation.z, -0.12, 0.05);
      this.body.scale.y = 1 + Math.sin(t * 1.8) * 0.006; // breathing
    }
  }
  wave(t) { this.arms[0].rotation.z = -2.4 + Math.sin(t * 9) * 0.3; this.arms[0].rotation.x = 0; }
}
