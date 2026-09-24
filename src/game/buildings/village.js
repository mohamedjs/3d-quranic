// Village layout. Houses, well, stalls and hay bales are placed as Blender models; the
// river bridge, oasis shelter and ancient ruins are still generated here and merged per
// material (triplanar PBR, tinted by vertex colour).
import * as THREE from 'three';
import { height, pathDist, riverZ, rng, OASIS, RUINS, BRIDGE, STREET } from '../terrain/heightfield.js';
import { paint, merge } from '../vegetation/plants.js';

const WOOD = new Set([0x5b3a21, 0x6a4a2e, 0x5e4028, 0x7a5634, 0x6b4a2c, 0x3b2a1a, 0x8a6440, 0x7a5a36, 0x8a7a45]);
const STONE = new Set([0xcdb183, 0xc2a676, 0xd6bd92, 0xb9a384]);
const CLOTH = new Set([0xb5563a, 0x3f6f8f, 0xd9a441, 0x7a8f4a, 0x9b4a32, 0xcbb48a]);
// Grandma's house: on the northern edge of the village, between the north road and the
// canal (x = -15), facing east toward the road. Front (door side, model +Z) faces world +X.
// The mastaba (مصطبة) — a plastered mud-brick bench — runs along the front wall beside
// the door. Model: house_a (5.9 × 5.1 m incl. plinth, front wall at model z = +2.4,
// door centred at model x ≈ -0.59). Encounter positions in encounters.json match this.
export const HOME = { x: -9.4, z: 26, rot: Math.PI / 2 };
export const MASTABA = { h: 0.45, depth: 0.6, len: 2.5, x0: 0.05, wallZ: 2.4 };   // model-space, metres
// world-space centre of the bench and the point where a sitter's pelvis goes (0.25 m off the wall)
export function mastabaSeat(inset = 0.25) {
  const c = Math.cos(HOME.rot), s = Math.sin(HOME.rot), mx = MASTABA.x0 + MASTABA.len / 2, mz = MASTABA.wallZ + inset;
  return { x: HOME.x + mx * c + mz * s, z: HOME.z - mx * s + mz * c, y: height(HOME.x, HOME.z) + MASTABA.h };
}

const groupOf = hex => WOOD.has(hex) ? 'wood' : STONE.has(hex) ? 'stone' : CLOTH.has(hex) ? 'cloth' : [0xa65a32, 0x9c6b42, 0x1d3438, 0xe08a2a, 0x7f9a3a, 0x6b3a22, 0xc8412c, 0xd8b25a].includes(hex) ? 'clay' : 'plaster';


export function buildVillage() {
  const r = rng(21), parts = { plaster: [], wood: [], stone: [], cloth: [], clay: [] }, colliders = [];
  const pick = a => a[(r() * a.length) | 0];
  const put = (geo, color, M, x = 0, y = 0, z = 0) => { geo.translate(x, y, z); const g = paint(geo, color); if (M) g.applyMatrix4(M); parts[groupOf(color)].push(g); };
  const box = (w, h, d) => new THREE.BoxGeometry(w, h, d);
  const cyl = (r0, r1, h, s = 8) => new THREE.CylinderGeometry(r0, r1, h, s);
  const collide = (x, z, hw, hd) => colliders.push({ x0: x - hw, x1: x + hw, z0: z - hd, z1: z + hd });

  // Houses, the well, stalls and hay are Blender models (public/models/env); here we only
  // decide where they go. Each house picks the closest of three modelled sizes.
  const placements = [];
  const HOUSES = [['house_a', 5.6, 4.8], ['house_b', 7.3, 5.4], ['house_c', 4.6, 4.4]];   // b includes its outside stair
  function house(x, z, w, d, h, rot) {
    const [model, mw, md] = HOUSES.reduce((best, v) => (Math.abs(v[1] * v[2] - w * d) < Math.abs(best[1] * best[2] - w * d) ? v : best));
    const sx = THREE.MathUtils.clamp(w / mw, 0.88, 1.12), sz = THREE.MathUtils.clamp(d / md, 0.88, 1.12);
    placements.push({ model, x, y: height(x, z) - 0.05, z, rot, sx, sy: THREE.MathUtils.clamp(h / 3.1, 0.92, 1.1), sz });
    const c = Math.abs(Math.cos(rot)), s = Math.abs(Math.sin(rot)), W = mw * sx, D = md * sz;
    collide(x, z, c * W / 2 + s * D / 2 + 0.1, s * W / 2 + c * D / 2 + 0.1);
  }

  // the village street (south approach): houses face the lane from both sides, garden walls,
  // pots and flowering bushes between them, a stone-lined stream along the west side
  const placed = [], gardens = [];
  const place = (model, x, z, rot, s = 1) => placements.push({ model, x, y: height(x, z) - 0.03, z, rot, sx: s, sy: s, sz: s });
  for (let z = STREET.z0 + 2, i = 0; z < STREET.z1 - 3; i++) {
    for (const side of [-1, 1]) {
      if ((i + (side > 0 ? 1 : 0)) % 4 === 3) {                         // a garden instead of a house
        place('garden_wall', side * 6.2, z + 2, Math.PI / 2); collide(side * 6.2, z + 2, 0.25, 2);
        gardens.push([side * 8, z + 2]);
        continue;
      }
      const w = 5 + r() * 1.6, d = 4.6 + r() * 1, x = side * (5.6 + d / 2);
      house(x, z + w / 2, w, d, 2.9 + r() * 0.6, side < 0 ? Math.PI / 2 : -Math.PI / 2);
      placed.push({ x, z: z + w / 2, R: Math.max(w, d) / 2 });
      if (r() < 0.7) place('pot_plant', side * 5.0, z + r() * w, r() * 6, 0.9 + r() * 0.4);
      if (r() < 0.5) place(r() < 0.5 ? 'jar' : 'jar_b', side * 5.2, z + w - 0.6, r() * 6);
      if (r() < 0.8) gardens.push([side * 5.1, z + (r() < 0.5 ? 0.4 : w - 0.4)]);
    }
    z += 7.2;
  }
  for (let z = STREET.z0; z < STREET.z1; z += 4) place('stream', STREET.channelX, z + 2, 0);
  collide(STREET.channelX, (STREET.z0 + STREET.z1) / 2, 0.6, (STREET.z1 - STREET.z0) / 2);

  // village: houses around the square, clear of the four roads and the well
  for (let i = 0; i < 600 && placed.length < 17; i++) {
    const a = r() * Math.PI * 2, dist = 13 + r() * 25, x = Math.cos(a) * dist, z = Math.sin(a) * dist;
    const w = 4 + r() * 3, d = 4 + r() * 2.5, h = 2.8 + r() * 1.3;
    const rot = Math.round(Math.atan2(-x, -z) / (Math.PI / 2)) * (Math.PI / 2);
    const R = Math.max(w, d) / 2;
    if (pathDist(x, z) < R + 2.8 || Math.hypot(x, z) - R < 10) continue;
    if (Math.hypot(x - HOME.x, z - HOME.z) < R + 7) continue;           // grandma's house and yard
    if (placed.some(p => Math.abs(p.x - x) < (p.R + R + 1.8) && Math.abs(p.z - z) < (p.R + R + 1.8))) continue;
    placed.push({ x, z, R }); house(x, z, w, d, h, rot);
  }
  // grandma's house with its mastaba (مصطبة) along the front wall
  {
    placements.push({ model: 'house_a', x: HOME.x, y: height(HOME.x, HOME.z) - 0.05, z: HOME.z, rot: HOME.rot, sx: 1, sy: 1, sz: 1 });
    placed.push({ x: HOME.x, z: HOME.z, R: 3 });
    collide(HOME.x, HOME.z, 2.55, 3.0);                                  // rot = 90°: depth along x, width along z
    const g = height(HOME.x, HOME.z), HM = new THREE.Matrix4().makeRotationY(HOME.rot).setPosition(HOME.x, g, HOME.z);
    const { h, depth, len, x0, wallZ } = MASTABA, cx = x0 + len / 2, cz = wallZ + depth / 2;
    put(box(len, h + 0.2 - 0.05, depth), 0xd9c4a0, HM, cx, (h - 0.25) / 2, cz);              // mud-brick body, sunk 0.2 m
    put(box(len + 0.04, 0.05, depth + 0.04), 0xe6d6b8, HM, cx, h - 0.025, cz);              // smooth plastered top
    put(box(1.3, 0.012, depth - 0.1), 0xb5563a, HM, cx - 0.2, h + 0.006, cz);               // a kilim where grandma sits
    put(box(0.34, 0.1, 0.3), 0xcbb48a, HM, cx - 0.2 + 0.65 + 0.2, h + 0.05, wallZ + 0.16); // folded cushion at her side
    const w = mastabaSeat(depth / 2);
    collide(w.x, w.z, Math.abs(Math.sin(HOME.rot)) * depth / 2 + Math.abs(Math.cos(HOME.rot)) * len / 2 + 0.05,
      Math.abs(Math.cos(HOME.rot)) * depth / 2 + Math.abs(Math.sin(HOME.rot)) * len / 2 + 0.05);
  }

  // a few homes by the oasis, facing the water
  for (const a of [0.3, 1.2, 2.2, 5.4]) {
    const x = OASIS.x + Math.cos(a) * 30, z = OASIS.z + Math.sin(a) * 30;
    if (pathDist(x, z) > 5) house(x, z, 4.5, 4, 3, Math.round(Math.atan2(OASIS.x - x, OASIS.z - z) / (Math.PI / 2)) * (Math.PI / 2));
  }

  // the well on the square
  const well = { x: -5, z: 4 }, wy = height(well.x, well.z);
  placements.push({ model: 'well', x: well.x, y: wy, z: well.z, rot: 0.4 });
  collide(well.x, well.z, 1.4, 1.4);

  // market stalls
  for (const [x, z] of [[9, -7], [-10, -8]]) {
    placements.push({ model: 'stall', x, y: height(x, z), z, rot: Math.atan2(-x, -z) });
    collide(x, z, 1.6, 1.2);
  }

  // hay bales along the field road
  for (let i = 0; i < 9; i++) {
    const x = -70 + r() * 140; if (Math.abs(x) < 4) continue;
    const z = 11.5 + r();
    placements.push({ model: 'hay', x, y: height(x, z) - 0.05, z, rot: r() * 3 });
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

  const geometries = Object.fromEntries(Object.entries(parts).filter(([, l]) => l.length).map(([k, l]) => [k, merge(l)]));
  return { geometries, colliders, placements, gardens, well, shelter: sh, home: HOME };
}
