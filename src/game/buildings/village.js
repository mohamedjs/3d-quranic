// Village layout. Houses (6 variants across 3 footprints), the mastaba, garden walls,
// river bridge, oasis arish shelter and ancient sandstone ruins are placed as Blender GLB models.
import * as THREE from 'three';
import { height, pathDist, riverZ, rng, hash, OASIS, RUINS, BRIDGE, STREET } from '../terrain/heightfield.js';

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

export function buildVillage() {
  const r = rng(21), colliders = [];
  const collide = (x, z, hw, hd) => colliders.push({ x0: x - hw, x1: x + hw, z0: z - hd, z1: z + hd });

  // Houses, the well, stalls and hay are Blender models (public/models/env); here we only
  // decide where they go. Each house picks the closest of three footprint groups, then picks
  // between the two variants in that group from a position hash (without consuming `r()`).
  const placements = [];
  const HOUSES = [
    [['house_a', 'house_d'], 5.6, 4.8],
    [['house_b', 'house_e'], 7.3, 5.4],
    [['house_c', 'house_f'], 4.6, 4.4],
  ];
  function house(x, z, w, d, h, rot) {
    const [variants, mw, md] = HOUSES.reduce((best, v) => (Math.abs(v[1] * v[2] - w * d) < Math.abs(best[1] * best[2] - w * d) ? v : best));
    const model = variants[hash(Math.round(x * 10) + 1, Math.round(z * 10) + 3) < 0.5 ? 0 : 1];
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
  for (let z = STREET.z0; z < STREET.z1; z += 4) place('stream_channel', STREET.channelX, z + 2, 0);
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
    // the mastaba is its own model, authored in house_a's model space (x 0.05–2.55, z 2.4–3.0,
    // seat 0.45 m): same transform as the house, at ground level (the house sits 5 cm lower)
    const g = height(HOME.x, HOME.z), { depth } = MASTABA;
    placements.push({ model: 'mastaba', x: HOME.x, y: g, z: HOME.z, rot: HOME.rot });
    const Wm = (mx, mz) => [HOME.x + mx * Math.cos(HOME.rot) + mz * Math.sin(HOME.rot), HOME.z - mx * Math.sin(HOME.rot) + mz * Math.cos(HOME.rot)];
    const [bx, bz] = Wm(3.35, 2.1), [px, pz] = Wm(-2.9, 2.55);          // bougainvillea by the bench, a pot by the door
    placements.push({ model: 'bougainvillea', x: bx, y: height(bx, bz) - 0.05, z: bz, rot: 0.6, sx: 1.15, sy: 1.15, sz: 1.15 });
    placements.push({ model: 'pot_plant', x: px, y: height(px, pz) - 0.03, z: pz, rot: 1, sx: 1.1, sy: 1.1, sz: 1.1 });
    collide(bx, bz, 0.5, 0.5);
    const { len } = MASTABA;
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

  // arched limestone-and-timber Nile river bridge (v3 GLB matching BRIDGE.deck = 0.55)
  placements.push({ model: 'river_bridge', x: BRIDGE.x, y: 0, z: riverZ(BRIDGE.x), rot: 0, sx: 1, sy: 1, sz: 1 });

  // palm-frond shade shelter at the oasis (arish)
  const sh = { x: -92, z: -9 };
  placements.push({ model: 'oasis_arish', x: sh.x, y: height(sh.x, sh.z), z: sh.z, rot: 0, sx: 1, sy: 1, sz: 1 });

  // ancient settlement: broken sandstone walls, a colonnade and a gate arch
  // Preserve every `r()` draw and `collide(...)` call in exact order so walkability stays identical.
  const RUIN_WALLS = [['ruins_wall_a', 1.2], ['ruins_wall_b', 2.2], ['ruins_wall_c', 3.4]];
  const wallRun = (x0, z0, x1, z1) => {
    const len = Math.hypot(x1 - x0, z1 - z0), n = Math.ceil(len / 4);
    for (let i = 0; i < n; i++) {
      if (r() < 0.25) continue;
      const t = (i + 0.5) / n, x = x0 + (x1 - x0) * t, z = z0 + (z1 - z0) * t, hh = 0.6 + r() * 3, along = Math.abs(x1 - x0) > Math.abs(z1 - z0);
      const flip = r() < 0.5 ? Math.PI : 0;
      const [model, refH] = RUIN_WALLS.reduce((best, v) => (Math.abs(v[1] - hh) < Math.abs(best[1] - hh) ? v : best));
      placements.push({ model, x, y: height(x, z) - 0.2, z, rot: (along ? 0 : Math.PI / 2) + flip, sx: 1, sy: hh / refH, sz: 1 });
      collide(x, z, along ? 2 : 0.45, along ? 0.45 : 2);
    }
  };
  const { x: rx, z: rz } = RUINS;
  wallRun(rx - 14, rz - 12, rx + 14, rz - 12); wallRun(rx - 14, rz - 12, rx - 14, rz + 8);
  wallRun(rx + 14, rz - 12, rx + 14, rz + 8); wallRun(rx - 14, rz + 8, rx - 4, rz + 8); wallRun(rx + 4, rz + 8, rx + 14, rz + 8);
  wallRun(rx - 6, rz - 12, rx - 6, rz - 2);
  for (let i = 0; i < 7; i++) {
    const x = rx - 9 + i * 3, z = rz + 14, hh = r() < 0.3 ? 1 + r() : 4.2;
    const rot = r() * Math.PI * 2;
    if (hh > 4) r();
    placements.push({ model: 'ruins_column', x, y: height(x, z), z, rot, sx: 1, sy: hh / 4.2, sz: 1 });
    collide(x, z, 0.45, 0.45);
  }
  {
    const rot = 0.4 + Math.PI / 2, half = 1.8;
    placements.push({
      model: 'ruins_column',
      x: rx + 2 - Math.sin(rot) * half,
      y: height(rx, rz + 18) + 0.38,
      z: rz + 18 - Math.cos(rot) * half,
      rot,
      tilt: Math.PI / 2,
      sx: 1,
      sy: 3.6 / 4.2,
      sz: 1,
    });
  }
  const gy = height(rx, rz + 8);
  for (const s of [-2, 2]) collide(rx + s, rz + 8, 0.5, 0.5);
  placements.push({ model: 'ruins_arch', x: rx, y: gy, z: rz + 8, rot: 0, sx: 1, sy: 1, sz: 1 });

  return { geometries: {}, colliders, placements, gardens, well, shelter: sh, home: HOME };
}
