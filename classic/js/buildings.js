// Mud-brick village, well, market, bridge, oasis huts and the ancient ruins.
// All of it is merged into one vertex-coloured mesh: one draw call.
import * as THREE from 'three';
import { height, pathDist, riverZ, rng, OASIS, RUINS, BRIDGE } from './terrain.js';
import { paint, merge } from './nature.js';

const WALLS = [0xc9a276, 0xd4b087, 0xbf9469, 0xdcc19a, 0xc79f78];
const FABRIC = [0xb5563a, 0x3f6f8f, 0xd9a441, 0x7a8f4a];
const JAR = [new THREE.Vector2(0.001, 0), new THREE.Vector2(0.18, 0.02), new THREE.Vector2(0.28, 0.25),
  new THREE.Vector2(0.25, 0.5), new THREE.Vector2(0.12, 0.62), new THREE.Vector2(0.15, 0.72)];

export function buildVillage(scene) {
  const r = rng(21), parts = [], colliders = [];
  const pick = a => a[(r() * a.length) | 0];
  const put = (geo, color, M, x = 0, y = 0, z = 0) => { geo.translate(x, y, z); const g = paint(geo, color); if (M) g.applyMatrix4(M); parts.push(g); };
  const box = (w, h, d) => new THREE.BoxGeometry(w, h, d);
  const cyl = (r0, r1, h, s = 8) => new THREE.CylinderGeometry(r0, r1, h, s);
  const collide = (x, z, hw, hd) => colliders.push({ x0: x - hw, x1: x + hw, z0: z - hd, z1: z + hd });
  const shade = (hex, k) => new THREE.Color(hex).multiplyScalar(k).getHex();

  function house(x, z, w, d, h, rot) {
    const M = new THREE.Matrix4().makeRotationY(rot).setPosition(x, height(x, z) - 0.3, z), wall = pick(WALLS);
    put(box(w, h, d), wall, M, 0, h / 2, 0);
    put(box(w + 0.25, 0.55, d + 0.25), shade(wall, 0.82), M, 0, 0.27, 0);
    put(box(w + 0.2, 0.32, d + 0.2), shade(wall, 1.08), M, 0, h + 0.16, 0);
    const dx = (r() - 0.5) * Math.max(0, w - 2.2);
    put(box(0.95, 1.9, 0.1), 0x5b3a21, M, dx, 1.25, d / 2 + 0.03);
    put(box(1.4, 0.14, 0.2), 0x6a4a2e, M, dx, 2.27, d / 2 + 0.06);
    if (w > 4.4) put(box(0.55, 0.6, 0.1), 0x3b2a1a, M, dx > 0 ? -w * 0.3 : w * 0.3, h * 0.66, d / 2 + 0.03);
    put(box(0.1, 0.6, 0.55), 0x3b2a1a, M, w / 2 + 0.03, h * 0.66, 0);
    const n = Math.round(w / 1.1);
    for (let i = 0; i < n; i++) put(cyl(0.07, 0.07, 0.8, 5).rotateX(Math.PI / 2), 0x6a4a2e, M, -w / 2 + (i + 0.5) * w / n, h - 0.3, d / 2 + 0.3);
    const roll = r();
    if (roll < 0.35) {
      const w2 = w * 0.5, d2 = d * 0.5, h2 = h * 0.62;
      put(box(w2, h2, d2), wall, M, -w / 4, h + h2 / 2, -d / 4);
      put(box(w2 + 0.2, 0.3, d2 + 0.2), shade(wall, 1.08), M, -w / 4, h + h2 + 0.15, -d / 4);
      put(box(0.5, 0.55, 0.1), 0x3b2a1a, M, -w / 4, h + h2 * 0.55, 0.03);
    } else if (roll < 0.55) {
      const rad = Math.min(w, d) * 0.27;
      put(cyl(rad, rad, 0.4, 14), 0xe2d2b4, M, 0, h + 0.2, 0);
      put(new THREE.SphereGeometry(rad, 14, 7, 0, Math.PI * 2, 0, Math.PI / 2), 0xece0c6, M, 0, h + 0.4, 0);
    }
    if (r() < 0.45) {
      const g = box(2, 0.06, 1.4).rotateX(0.22);
      put(g, pick(FABRIC), M, dx, 2.45, d / 2 + 0.75);
      for (const s of [-0.9, 0.9]) put(cyl(0.05, 0.05, 2.3, 5), 0x6a4a2e, M, dx + s, 1.15, d / 2 + 1.35);
    }
    for (let k = 0, m = 1 + ((r() * 3) | 0); k < m; k++) put(new THREE.LatheGeometry(JAR, 10), r() < 0.5 ? 0xa65a32 : 0x9c6b42, M, (r() - 0.5) * w * 0.8, 0.3, d / 2 + 0.45 + r() * 0.3);
    const c = Math.abs(Math.cos(rot)), s = Math.abs(Math.sin(rot));
    collide(x, z, c * w / 2 + s * d / 2 + 0.1, s * w / 2 + c * d / 2 + 0.1);
  }

  // village: houses around the square, clear of the four roads and the well
  const placed = [];
  for (let i = 0; i < 600 && placed.length < 17; i++) {
    const a = r() * Math.PI * 2, dist = 13 + r() * 25, x = Math.cos(a) * dist, z = Math.sin(a) * dist;
    const w = 4 + r() * 3, d = 4 + r() * 2.5, h = 2.8 + r() * 1.3;
    const rot = Math.round(Math.atan2(-x, -z) / (Math.PI / 2)) * (Math.PI / 2);
    const R = Math.max(w, d) / 2;
    if (pathDist(x, z) < R + 2.8 || Math.hypot(x, z) - R < 10) continue;
    if (placed.some(p => Math.abs(p.x - x) < (p.R + R + 1.8) && Math.abs(p.z - z) < (p.R + R + 1.8))) continue;
    placed.push({ x, z, R }); house(x, z, w, d, h, rot);
  }
  // a few homes by the oasis, facing the water
  for (const a of [0.3, 1.2, 2.2, 5.4]) {
    const x = OASIS.x + Math.cos(a) * 30, z = OASIS.z + Math.sin(a) * 30;
    if (pathDist(x, z) > 5) house(x, z, 4.5, 4, 3, Math.round(Math.atan2(OASIS.x - x, OASIS.z - z) / (Math.PI / 2)) * (Math.PI / 2));
  }

  // the well on the square
  const well = { x: -5, z: 4 }, wy = height(well.x, well.z);
  const WM = new THREE.Matrix4().setPosition(well.x, wy, well.z);
  put(cyl(1.15, 1.25, 0.9, 16), 0xb9a384, WM, 0, 0.45, 0);
  put(cyl(0.9, 0.9, 0.03, 16), 0x1d3438, WM, 0, 0.91, 0);
  for (const s of [-1.05, 1.05]) put(box(0.16, 2.1, 0.16), 0x6a4a2e, WM, s, 1.05, 0);
  put(cyl(0.07, 0.07, 2.3, 6).rotateZ(Math.PI / 2), 0x6a4a2e, WM, 0, 2, 0);
  put(cyl(0.015, 0.015, 0.9, 4), 0xcbb48a, WM, 0.2, 1.55, 0);
  put(cyl(0.2, 0.16, 0.3, 10), 0x7a5a36, WM, 0.2, 0.95 + 0.2, 0);
  collide(well.x, well.z, 1.4, 1.4);

  // market stalls
  for (const [x, z] of [[9, -7], [-10, -8]]) {
    const M = new THREE.Matrix4().setPosition(x, height(x, z), z);
    for (const [px, pz] of [[-1.4, -0.9], [1.4, -0.9], [-1.4, 0.9], [1.4, 0.9]]) put(cyl(0.06, 0.06, 2.4, 5), 0x6a4a2e, M, px, 1.2, pz);
    put(box(3.2, 0.06, 2.2).rotateX(0.12), pick(FABRIC), M, 0, 2.4, 0);
    put(box(2.6, 0.8, 1.2), 0x8a6440, M, 0, 0.4, 0.2);
    for (let k = 0; k < 14; k++) put(new THREE.SphereGeometry(0.14, 7, 5), pick([0xe08a2a, 0x7f9a3a, 0x6b3a22, 0xc8412c]), M, -1.1 + (k % 7) * 0.37, 0.92, 0.2 + ((k / 7) | 0) * 0.35 - 0.15);
    collide(x, z, 1.6, 1.2);
  }

  // hay bales along the field road
  for (let i = 0; i < 9; i++) {
    const x = -70 + r() * 140; if (Math.abs(x) < 4) continue;
    const z = 11.5 + r(), M = new THREE.Matrix4().makeRotationY(r() * 3).setPosition(x, height(x, z) + 0.55, z);
    put(cyl(0.6, 0.6, 1.2, 12).rotateZ(Math.PI / 2), 0xd8b25a, M);
    collide(x, z, 0.8, 0.8);
  }

  // wooden bridge across the river on the north road
  const bz = riverZ(BRIDGE.x), BM = new THREE.Matrix4().setPosition(BRIDGE.x, 0, bz);
  for (let z = -BRIDGE.halfL; z <= BRIDGE.halfL; z += 0.5) put(box(BRIDGE.halfW * 2 + 0.2, 0.12, 0.45), r() < 0.5 ? 0x7a5634 : 0x6b4a2c, BM, 0, BRIDGE.deck - 0.06, z);
  for (const s of [-1, 1]) {
    put(box(0.1, 0.1, BRIDGE.halfL * 2), 0x5e4028, BM, s * BRIDGE.halfW, BRIDGE.deck + 0.85, 0);
    for (let z = -BRIDGE.halfL; z <= BRIDGE.halfL; z += 2.5) put(box(0.14, 3.5, 0.14), 0x5e4028, BM, s * BRIDGE.halfW, -0.25, z);
  }

  // palm-frond shade shelter at the oasis (arish)
  const sh = { x: -92, z: -9 }, SM = new THREE.Matrix4().setPosition(sh.x, height(sh.x, sh.z), sh.z);
  for (const [px, pz] of [[-2, -1.6], [2, -1.6], [-2, 1.6], [2, 1.6]]) put(cyl(0.09, 0.11, 2.6, 6), 0x6a4a2e, SM, px, 1.3, pz);
  put(box(4.8, 0.18, 4), 0x8a7a45, SM, 0, 2.65, 0);
  put(box(2.4, 0.3, 1.2), 0x9b4a32, SM, 0, 0.15, 0.6); // a rug-covered bench

  // ancient settlement: broken walls, a colonnade and a gate arch
  const stone = [0xcdb183, 0xc2a676, 0xd6bd92];
  const RM = h => new THREE.Matrix4().setPosition(0, h, 0);
  const wallRun = (x0, z0, x1, z1) => {
    const len = Math.hypot(x1 - x0, z1 - z0), n = Math.ceil(len / 4);
    for (let i = 0; i < n; i++) {
      if (r() < 0.25) continue;
      const t = (i + 0.5) / n, x = x0 + (x1 - x0) * t, z = z0 + (z1 - z0) * t, hh = 0.6 + r() * 3, along = Math.abs(x1 - x0) > Math.abs(z1 - z0);
      put(along ? box(4, hh, 0.9) : box(0.9, hh, 4), pick(stone), RM(height(x, z) - 0.2), x, hh / 2, z);
      collide(x, z, along ? 2 : 0.45, along ? 0.45 : 2);
    }
  };
  const { x: rx, z: rz } = RUINS;
  wallRun(rx - 14, rz - 12, rx + 14, rz - 12); wallRun(rx - 14, rz - 12, rx - 14, rz + 8);
  wallRun(rx + 14, rz - 12, rx + 14, rz + 8); wallRun(rx - 14, rz + 8, rx - 4, rz + 8); wallRun(rx + 4, rz + 8, rx + 14, rz + 8);
  wallRun(rx - 6, rz - 12, rx - 6, rz - 2);
  for (let i = 0; i < 7; i++) {
    const x = rx - 9 + i * 3, z = rz + 14, hh = r() < 0.3 ? 1 + r() : 4.2;
    put(cyl(0.38, 0.42, hh, 10), pick(stone), RM(height(x, z)), x, hh / 2, z);
    if (hh > 4) put(box(1, 0.35, 1), pick(stone), RM(height(x, z)), x, hh + 0.17, z);
    collide(x, z, 0.45, 0.45);
  }
  put(cyl(0.4, 0.4, 3.6, 10).rotateZ(Math.PI / 2).rotateY(0.4), stone[0], RM(height(rx, rz + 18) + 0.3), rx + 2, 0, rz + 18);
  const gy = height(rx, rz + 8);
  for (const s of [-2, 2]) { put(box(0.9, 3.4, 0.9), stone[1], RM(gy), rx + s, 1.7, rz + 8); collide(rx + s, rz + 8, 0.5, 0.5); }
  put(new THREE.TorusGeometry(2, 0.4, 6, 14, Math.PI), stone[2], RM(gy), rx, 3.4, rz + 8);

  const mesh = new THREE.Mesh(merge(parts), new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.92 }));
  mesh.castShadow = mesh.receiveShadow = true;
  scene.add(mesh);
  return { mesh, colliders, well, shelter: sh };
}
