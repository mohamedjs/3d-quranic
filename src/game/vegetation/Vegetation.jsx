// Scatters all v3 painterly vegetation (public/models/env):
// date palms (4 hero variants), gnarled sycamores (2 variants), desert umbrella acacias,
// cascading bougainvillea, Ghibli leaf-cluster bushes (bush_a/b), Nile papyrus & reeds,
// oasis lotus pads, 5 rebuilt crops in rows + earth bunds, root-blended grass tufts, and
// wildflowers. Chunk sizes & LODs are tuned so Lite <=70 calls / <=150k tris and High
// stays cleanly <=210 calls / <=1.3M tris at both spawn and lookout.
import { useMemo, useRef, useEffect } from 'react';
import * as THREE from 'three';
import { useFrame, useThree } from '@react-three/fiber';
import { height, fieldPlot, pathDist, riverZ, waterDist, hash, OASIS, RUINS, rng, fbm, smooth, WATER_Y, ROAD_CANALS } from '../terrain/heightfield.js';
import { lump } from './plants.js';
import { instanceModels } from '../world/instancing.js';
import { mergedPlant, upgradeFoliageAtlas } from '../world/envAssets.js';
import { toonMaterial, WIND } from '../shaders/toon.js';
import { envMaterial } from '../shaders/stylizedPbr.js';
import { TOON } from '../shaders/toonPalette.js';
import { usePreset, useDetail, useGame } from '../systems/store.js';
import { LAYER_NO_REFLECT } from '../systems/layers.js';
import { refs } from '../systems/refs.js';

// Chunk density: full inside 55 % of the draw distance, thinning to 20 % at its edge, then
// gone — instances are shuffled per chunk, so drawing the first N is an even thinning.
const density = (d, lim) => (d < 0.55 * lim ? 1 : d > lim ? 0 : 1 - 0.8 * (d - 0.55 * lim) / (0.45 * lim));
function shuffle(m, c, r) {
  for (let i = m.length - 1; i > 0; i--) {
    const j = Math.floor(r() * (i + 1));
    [m[i], m[j]] = [m[j], m[i]]; if (c.length) [c[i], c[j]] = [c[j], c[i]];
  }
}

const _q = new THREE.Quaternion(), _e = new THREE.Euler(), _s = new THREE.Vector3(), _p = new THREE.Vector3();
const M = (x, y, z, ry, s, sy = s, tilt = 0) => new THREE.Matrix4().compose(_p.set(x, y, z), _q.setFromEuler(_e.set(tilt, ry, tilt * 0.7)), _s.set(s, sy, s));

function inst(geo, mat, list, { colors, shadow = false, receive = true, layer } = {}) {
  if (!list.length) return null;
  const m = new THREE.InstancedMesh(geo, mat, list.length);
  list.forEach((mx, i) => m.setMatrixAt(i, mx));
  colors?.forEach((c, i) => m.setColorAt(i, c));
  m.castShadow = shadow; m.receiveShadow = receive;
  if (layer) m.layers.set(layer);
  m.computeBoundingSphere(); m.computeBoundingBox?.();
  m.userData.shared = true;                     // geometry/material live in caches
  return m;
}
const tint = (r, spread = 0.16) => new THREE.Color(1, 1, 1).multiplyScalar(1 - spread / 2 + r() * spread);

export function Vegetation({ colliders, clearings, assets, gardens = [], onTrees = null }) {
  const preset = usePreset(), detail = useDetail();
  const camera = useThree(s => s.camera);
  const chunks = useRef([]), trees = useRef([]);

  // Lazy-upgrade shared WebP foliage atlas when running Medium (1024px) or High/Ultra (2048px)
  useEffect(() => {
    if ((preset.texRes ?? 512) >= 1024) {
      upgradeFoliageAtlas(preset.texRes, preset.waterMode === 'ultra' ? 8 : 4);
    }
  }, [preset.texRes, preset.waterMode]);

  const group = useMemo(() => {
    (window.__builds ??= []).push('vegetation:' + useGame.getState().detail);   // test probe: built once
    const r = rng(7), rs = rng(99), g = new THREE.Group();   // rs: shuffles only, so placement stays as before
    const add = (...o) => o.forEach(x => x && g.add(x));
    colliders.length = colliders.baseLength ??= colliders.length;   // rebuilds replace, not append, tree colliders
    const blocked = (x, z, pad) => colliders.some(b => x > b.x0 - pad && x < b.x1 + pad && z > b.z0 - pad && z < b.z1 + pad)
      || clearings.some(([cx, cz, cr]) => Math.hypot(x - cx, z - cz) < cr + pad);
    const lush = (x, z, h) => h > WATER_Y + 0.55 && h < 14 && fieldPlot(x, z) < 0 && pathDist(x, z) > 2.2 && Math.hypot(x, z) > 22;
    const list = [];
    const shading = detail.shading ?? 'toon';

    // 72 m chunks on non-Lite balance tight frustum culling (<=1.3M tris) with low draw calls (<=210)
    const CH = detail.lite ? 36 : 72;
    const bucket = () => new Map();
    const put = (map, key, x, z, m, c) => {
      const k = `${key}|${Math.floor(x / CH)},${Math.floor(z / CH)}`;
      if (!map.has(k)) map.set(k, { m: [], c: [] });
      map.get(k).m.push(m); if (c) map.get(k).c.push(c);
    };
    const flush = (map, kind, { wind, shadow = false, geo, mat, layer = LAYER_NO_REFLECT } = {}) => {
      for (const [k, v] of map) {
        const [model, cell] = k.split('|'), [cx, cz] = cell.split(',').map(Number);
        const p = geo ? { body: geo, material: null } : mergedPlant(assets, model);
        const center = new THREE.Vector3((cx + 0.5) * CH, 0, (cz + 0.5) * CH);
        shuffle(v.m, v.c, rs);
        const useMat = mat ?? p.material ?? envMaterial('plant_' + model, { shading, vertexColors: true, side: THREE.DoubleSide, wind, rim: 0.12, sss: 0.45 });
        const body = inst(p.body, useMat, v.m, { colors: v.c.length ? v.c : null, shadow, layer });
        body.userData.center = center; body.userData.kind = kind; body.userData.full = v.m.length; g.add(body); list.push(body);
      }
    };

    // ---- grass tufts, chunked (root-blended & backlit) ------------------------------
    const grass = bucket();
    for (let i = 0, n = 0; i < detail.grass * 3 && n < detail.grass; i++) {
      const x = (r() - 0.5) * 360, z = (r() - 0.5) * 360 - 10, h = height(x, z);
      if (!lush(x, z, h) || blocked(x, z, 0.15)) continue;
      const patch = fbm(x * 0.05, z * 0.05);
      if (patch < -0.5 && r() < 0.6) continue;
      const model = detail.lite ? 'grass_a' : patch > 0.55 ? 'grass_c' : hash(Math.floor(x / 9), Math.floor(z / 9)) < 0.5 ? 'grass_a' : 'grass_b';
      put(grass, model, x, z, M(x, h - 0.03, z, r() * 6.3, 0.95 + r() * 0.5, 0.85 + r() * 0.7 + (waterDist(x, z) < 5 ? 0.4 : 0)), tint(r));
      n++;
    }
    flush(grass, 'grass', { wind: WIND.grass });

    // ---- crops in rows, earth bunds between plots -----------------------------------
    const lowDetail = !detail.outlines;
    const crops = bucket(), R = lowDetail ? 105 : 140;
    for (let x = -204.6; x < 205; x += 0.8) for (let z = -149.7; z < 150; z += 0.6) {
      const far = Math.hypot(x, z);
      if (far > R || (far > R - 50 && r() < (far - R + 50) / 60)) continue;
      const t = fieldPlot(x, z); if (t < 0 || t === 4) continue;
      const row = Math.round(z / 0.6);
      if (t === 0 && (row % 4 === 1 || Math.round(x / 0.8) % 5 === 2)) continue;
      if (t >= 2 && row % 2) continue;
      if (t === 2 && r() > 0.85) continue;
      if (lowDetail && r() < (detail.cropThin ?? 0.35)) continue;
      if (blocked(x, z, 0.4)) continue;
      const jx = x + (r() - 0.5) * 0.2, h = height(jx, z);
      const model = t === 0 ? 'crop_berseem' : t === 1 ? 'crop_wheat' : t === 2 ? 'crop_maize'
        : hash(Math.floor((x + 1000) / 15), Math.floor((z + 1000) / 10)) < 0.5 ? 'crop_cotton' : 'crop_cabbage';
      const s = t === 0 ? 1.05 + r() * 0.35 : t === 1 ? 0.95 + r() * 0.25 : 0.88 + r() * 0.3;
      put(crops, model, jx, z, M(jx, h - 0.03, z, r() * 6.3, s, s * (0.9 + r() * 0.2)), tint(r, 0.12));
    }
    flush(crops, 'crop', {});

    const bunds = bucket(), RB = R - 40;
    for (let k = Math.ceil((-RB + 1000) / 15); k * 15 - 1000 < RB; k++) {
      const bx = k * 15 - 1000 + 0.45;
      for (let z = -RB; z < RB; z += 4) if (fieldPlot(bx, z) === 4 && fieldPlot(bx, z + 1.5) === 4 && fieldPlot(bx, z + 3) === 4 && Math.hypot(bx, z) < RB)
        put(bunds, 'field_bund', bx, z + 2, M(bx, height(bx, z + 2) - 0.1, z + 2, Math.PI / 2, 1));
    }
    for (let k = Math.ceil((-RB + 1000) / 10); k * 10 - 1000 < RB; k++) {
      const bz = k * 10 - 1000 + 0.35;
      for (let x = -RB; x < RB; x += 4) if (fieldPlot(x, bz) === 4 && fieldPlot(x + 1.5, bz) === 4 && fieldPlot(x + 3, bz) === 4 && Math.hypot(x, bz) < RB)
        put(bunds, 'field_bund', x + 2, bz, M(x + 2, height(x + 2, bz) - 0.1, bz, 0, 1));
    }
    flush(bunds, 'crop', {});

    // ---- reeds & Nile papyrus on wet river/canal/oasis banks ------------------------
    const reeds = bucket(); let nReeds = 0;
    for (let i = 0; i < 16000 && nReeds < 1500; i++) {
      let x, z;
      if (r() < 0.45) { x = (r() - 0.5) * 320; z = riverZ(x) + (r() - 0.5) * 22; }
      else if (r() < 0.16) {
        const a = r() * 6.3, d = 14.5 + r() * 3.5;
        x = OASIS.x + Math.cos(a) * d; z = OASIS.z + Math.sin(a) * d;
      } else {
        const seg = ROAD_CANALS[(r() * ROAD_CANALS.length) | 0], k = (r() * (seg.length - 1)) | 0, t = r();
        x = seg[k][0] + (seg[k + 1][0] - seg[k][0]) * t + (r() - 0.5) * 6; z = seg[k][1] + (seg[k + 1][1] - seg[k][1]) * t + (r() - 0.5) * 6;
      }
      const h = height(x, z), wd = waterDist(x, z);
      if (h < WATER_Y - 0.25 || h > WATER_Y + 1.6 || wd > 2.5 || blocked(x, z, 0.35)) continue;
      // Mix graceful Egyptian papyrus starburst clumps with riverbank reeds (~30% papyrus)
      const isPapyrus = !detail.lite && (hash(Math.floor(x / 5), Math.floor(z / 5)) > 0.68);
      put(reeds, isPapyrus ? 'papyrus' : 'reeds', x, z, M(x, h - 0.05, z, r() * 6.3, 0.85 + r() * 0.45, 0.85 + r() * 0.45));
      nReeds++;
    }
    flush(reeds, 'grass', { shadow: false });

    // ---- floating oasis lotus pads around the shallow outer spring rim --------------
    // Kept at r in [9.8, 13.6] so the center mirror reflects palms & sky unobstructed!
    const lotusM = [];
    const nLotus = detail.lite ? 10 : 22;
    for (let i = 0; i < nLotus; i++) {
      const a = (i / nLotus) * Math.PI * 2 + (r() - 0.5) * 0.25;
      const d = 10.2 + r() * 3.2;
      const lx = OASIS.x + Math.cos(a) * d, lz = OASIS.z + Math.sin(a) * d;
      if (height(lx, lz) < WATER_Y - 0.08) {
        lotusM.push(M(lx, WATER_Y + 0.015, lz, r() * 6.3, 0.78 + r() * 0.48));
      }
    }
    if (lotusM.length) {
      const lp = mergedPlant(assets, 'lotus_pad');
      const lm = inst(lp.body, lp.material, lotusM, { shadow: false, receive: true, layer: LAYER_NO_REFLECT });
      lm.userData.center = new THREE.Vector3(OASIS.x, 0, OASIS.z);
      lm.userData.kind = 'grass';
      lm.userData.full = lotusM.length;
      g.add(lm);
      list.push(lm);
    }

    // ---- date palms (4 hero variants: palm_a, palm_b, palm_c, palm_d) ---------------
    const spots = [];
    const tryPalm = (x, z, force = false) => {
      const h = height(x, z);
      if (!force) {
        if (h < WATER_Y + 0.4 || h > 9 || pathDist(x, z) < 2.6 || fieldPlot(x, z) >= 0 || blocked(x, z, 1.3)) return;
        if (spots.some(p => Math.hypot(p[0] - x, p[1] - z) < 3.2)) return;
      }
      spots.push([x, z, h]);
    };
    const k = detail.trees;
    tryPalm(-13.4, 23.2, true); tryPalm(-12.8, 30.4, true);          // framing grandma's house, by the canal
    for (let i = 0; i < 100 * k; i++) { const a = r() * 6.3, d = 16 + r() * 24; tryPalm(OASIS.x + Math.cos(a) * d, OASIS.z + Math.sin(a) * d); }
    for (let i = 0; i < 70 * k; i++) { const a = r() * 6.3, d = 12 + r() * 30; tryPalm(Math.cos(a) * d, Math.sin(a) * d); }
    for (let i = 0; i < 110 * k; i++) { const x = -200 + r() * 290, s = r() < 0.5 ? -1 : 1; tryPalm(x, riverZ(x) + s * (8 + r() * 9)); }
    for (let i = 0; i < 30 * k; i++) { const x = -80 + r() * 160; tryPalm(x, 11 + r() * 1.5); }
    for (const line of ROAD_CANALS) for (let j = 0; j + 1 < line.length; j++) {
      const [ax, az] = line[j], [bx, bz] = line[j + 1], L = Math.hypot(bx - ax, bz - az), nx = -(bz - az) / L, nz = (bx - ax) / L;
      for (let d = 3; d < L; d += 6.5 + r() * 3) if (r() < 0.8) for (const side of [-1, 1]) tryPalm(ax + (bx - ax) * d / L + nx * side * 3.3, az + (bz - az) * d / L + nz * side * 3.3);
    }
    for (let i = 0; i < 50 * k; i++) tryPalm((r() - 0.5) * 300, (r() - 0.5) * 200 - 20);
    for (let i = 0; i < 16 * k; i++) { const a = r() * 6.3, d = 20 + r() * 20; tryPalm(RUINS.x + Math.cos(a) * d, RUINS.z + Math.sin(a) * d); }
    const palmNames = ['palm_a', 'palm_b', 'palm_c', 'palm_d'];
    const treePl = spots.map(([x, z, h], i) => {
      const sc = 0.85 + r() * 0.35;
      return { model: palmNames[i % palmNames.length], x, y: h - 0.1, z, rot: r() * 6.3, sx: sc };
    });
    spots.forEach(([x, z]) => colliders.push({ x0: x - 0.4, x1: x + 0.4, z0: z - 0.4, z1: z + 0.4 }));

    // ---- sycamores (جميز, 2 variants) & desert umbrella acacias ---------------------
    const treeSpots = [];
    const okTree = (x, z, h, pad) => h > WATER_Y + 0.6 && !blocked(x, z, pad) && fieldPlot(x, z) < 0 && pathDist(x, z) > 3.2
      && !spots.some(p => Math.hypot(p[0] - x, p[1] - z) < 4.5) && !treeSpots.some(p => Math.hypot(p[0] - x, p[1] - z) < 7);
    for (const [x, z] of [[-4.6, 31.8], [5.2, 52], [-5.2, 58], [5.2, 63], [-26, 6], [22, -2], [-36, -4]]) {
      const h = height(x, z); if (okTree(x, z, h, 1)) treeSpots.push([x, z, h]);
    }
    for (const [[ax, az], [bx, bz]] of [[[0, -95], [0, -60]], [[-44, -9], [-96, -19]], [[44, -11], [130, -34]], [[0, 50], [0, 64]], [[-75, 12], [-50, 12]], [[50, 12], [75, 12]]]) {
      const L = Math.hypot(bx - ax, bz - az), nx = -(bz - az) / L, nz = (bx - ax) / L;
      for (let d = 4; d < L; d += 14 + r() * 8) for (const side of [-1, 1]) {
        const x = ax + (bx - ax) * d / L + nx * side * 6, z = az + (bz - az) * d / L + nz * side * 6, h = height(x, z);
        if (r() < 0.6 && okTree(x, z, h, 1.4)) treeSpots.push([x, z, h]);
      }
    }
    for (let i = 0; i < 1500 && treeSpots.length < 90 * k; i++) {
      const x = (r() - 0.5) * 360, z = (r() - 0.5) * 300 - 10, h = height(x, z);
      if (lush(x, z, h) && okTree(x, z, h, 2)) treeSpots.push([x, z, h]);
    }
    treeSpots.forEach(([x, z, h], i) => {
      // Dry eastern desert edge, ruins approach & elevated rocky slopes get iconic umbrella acacias!
      const isDesertEdge = (x > 65 && z < 15) || h > 6.5 || (Math.hypot(x - RUINS.x, z - RUINS.z) < 75);
      const model = isDesertEdge ? 'acacia' : (i % 2 === 0 ? 'sycamore_a' : 'sycamore_b');
      treePl.push({ model, x, y: h - 0.1, z, rot: r() * 6.3, sx: 0.74 + r() * 0.30 });
    });
    treeSpots.forEach(([x, z]) => colliders.push({ x0: x - 0.5, x1: x + 0.5, z0: z - 0.5, z1: z + 0.5 }));

    // Dedicated desert umbrella acacias scattered strictly clear of all 22 storytellers & paths
    const acaciaExtra = [];
    for (let i = 0; i < 420 && acaciaExtra.length < Math.round(28 * k); i++) {
      const x = 68 + r() * 140, z = -160 + r() * 170;
      const h = height(x, z);
      if (h < WATER_Y + 0.8 || h > 16 || fieldPlot(x, z) >= 0 || pathDist(x, z) < 4.5 || blocked(x, z, 2.8)) continue;
      if (spots.some(p => Math.hypot(p[0] - x, p[1] - z) < 6) || treeSpots.some(p => Math.hypot(p[0] - x, p[1] - z) < 8)
        || acaciaExtra.some(p => Math.hypot(p[0] - x, p[1] - z) < 11)) continue;
      acaciaExtra.push([x, z, h]);
      treePl.push({ model: 'acacia', x, y: h - 0.12, z, rot: r() * 6.3, sx: 0.82 + r() * 0.38 });
    }
    acaciaExtra.forEach(([x, z]) => colliders.push({ x0: x - 0.45, x1: x + 0.45, z0: z - 0.45, z1: z + 0.45 }));

    // ---- bougainvillea in the street gardens (rebuilt cascading vine/flower cards) --
    for (const [x, z] of gardens) {
      const fx = x + (r() - 0.5) * 0.8, fz = z + (r() - 0.5) * 1.2;
      treePl.push({ model: 'bougainvillea_bush', x: fx, y: height(fx, fz) - 0.05, z: fz, rot: r() * 6.3, sx: 0.85 + r() * 0.35 });
    }
    g.userData.treePl = treePl;
    if (onTrees) trees.current = null;                            // LITE: <World/> merges them with the other props
    else {
      trees.current = instanceModels(assets, treePl, { lodDistance: detail.lodDist ?? 60, outlines: false });
      add(trees.current.group); trees.current.update(camera.position); g.userData.trees = trees.current;
    }

    // ---- Ghibli leaf-cluster bushes (`bush_a` lush olive, `bush_b` golden desert scrub) ---
    const bushes = bucket(); let nBush = 0;
    for (let i = 0; i < 4000 && nBush < 460 * k; i++) {
      const x = (r() - 0.5) * 380, z = (r() - 0.5) * 320 - 10, h = height(x, z), dry = smooth(6, 16, h) * 0.7 + (x > 70 ? 0.5 : 0);
      if (h < WATER_Y + 0.5 || h > 12 || pathDist(x, z) < 2.2 || fieldPlot(x, z) >= 0 || blocked(x, z, 0.9) || Math.hypot(x, z) < 18) continue;
      const model = dry > 0.45 ? 'bush_b' : 'bush_a';
      put(bushes, model, x, z, M(x, h - 0.05, z, r() * 6.3, 0.75 + r() * 0.85, 0.68 + r() * 0.55), tint(r, 0.18));
      nBush++;
    }
    flush(bushes, 'bush', { shadow: false });

    // ---- rocks: along banks, mountain feet and ruins --------------------------------
    const rockM = [], rockC = [], stone = [new THREE.Color(TOON.toon_stone[0]), new THREE.Color(TOON.toon_stone_dark[0])];
    for (let i = 0; i < 6000 && rockM.length < (detail.rocks ?? 450); i++) {
      const x = (r() - 0.5) * 480, z = (r() - 0.5) * 480, h = height(x, z), wd = waterDist(x, z);
      const wild = z > 125 || Math.max(Math.abs(x), Math.abs(z)) > 180, bank = wd > 0 && wd < 1.6;
      if (!(wild || (bank && r() < 0.5)) || h < WATER_Y - 0.4 || pathDist(x, z) < 2.3 || blocked(x, z, 0.6) || fieldPlot(x, z) >= 0) continue;
      const s = bank ? 0.15 + r() * 0.35 : 0.3 + r() ** 3 * 3.5;
      rockM.push(M(x, h + s * 0.12, z, r() * 6.3, s, s * (0.55 + r() * 0.4), (r() - 0.5) * 0.4));
      rockC.push(stone[r() < 0.6 ? 0 : 1].clone().multiplyScalar(0.92 + r() * 0.16));
    }
    add(inst(lump(5, detail.lite ? 0 : 1), envMaterial('rock', { shading, vertexColors: true, roughness: 0.92 }), rockM, { colors: rockC, shadow: false }));

    // ---- fallen fronds/leaves under trees (tight distance); wildflowers near village & oasis --
    const litter = bucket(), litterPal = ['toon_frond_dry', 'toon_bark', 'toon_dates_gold', 'toon_leaf_dark'].map(n => new THREE.Color(TOON[n][0]));
    if (detail.litter !== false) for (const [x, z] of [...spots, ...treeSpots]) for (let j = 0; j < 7; j++) {
      const a = r() * 6.3, d = 0.4 + r() * 2.2, lx = x + Math.cos(a) * d, lz = z + Math.sin(a) * d;
      put(litter, 'litter', lx, lz, M(lx, height(lx, lz) + 0.02, lz, r() * 6.3, 0.09 + r() * 0.06, 1, Math.PI / 2 - 0.1), litterPal[(r() * litterPal.length) | 0]);
    }
    flush(litter, 'litter', { geo: new THREE.CircleGeometry(1, 5), mat: toonMaterial('litter', { side: THREE.DoubleSide, rim: 0 }) });

    const fl = bucket(); let nFl = 0;
    for (let i = 0; !detail.lite && i < 14000 && nFl < 1000 * k; i++) {
      const [ox, oz] = r() < 0.5 ? [0, 0] : [OASIS.x, OASIS.z], a = r() * 6.3, d = 14 + r() * 50;
      const x = ox + Math.cos(a) * d, z = oz + Math.sin(a) * d, h = height(x, z);
      if (!lush(x, z, h) || blocked(x, z, 0.3) || fbm(x * 0.07, z * 0.07) < 0.1) continue;
      put(fl, 'wildflowers', x, z, M(x, h - 0.02, z, r() * 6.3, 0.95 + r() * 0.4)); nFl++;
    }
    flush(fl, 'flower', {});

    chunks.current = list;
    return g;
  }, [detail]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { onTrees?.(group.userData.treePl); }, [group, onTrees]);
  useEffect(() => () => group.traverse(o => {   // free GPU buffers when Settings rebuilds
    if (!o.isMesh) return; o.dispose?.(); if (o.userData.shared) return; o.geometry.dispose(); o.material.dispose();
  }), [group]);

  // Run initial cull immediately on frame 0 (`acc = 1`) so unculled chunks never spike draw calls!
  const acc = useRef(1), focus = useRef(new THREE.Vector3());
  useFrame((_, dt) => {
    if ((acc.current += dt) < 0.25) return; acc.current = 0;
    trees.current?.update(camera.position);
    const v = refs.view, z = v.zoom, f = focus.current;
    f.set(THREE.MathUtils.lerp(camera.position.x, v.x, z), 0, THREE.MathUtils.lerp(camera.position.z, v.z, z));
    const lim = {
      grass: preset.grassDist * (1 - 0.25 * z),
      crop: preset.cropDist + z * 60,
      bush: Math.min(preset.bushDist, 120) + z * 40,
      flower: Math.min(preset.grassDist, 64),
      litter: 38,
    };
    const thin = { grass: 1 - 0.6 * z, crop: 1 - 0.55 * z, bush: 1 - 0.3 * z, flower: 1 - 0.5 * z, litter: 1 - 0.7 * z };
    for (const m of chunks.current) {
      const kind = m.userData.kind, c = m.userData.center;
      const k = density(Math.hypot(c.x - f.x, c.z - f.z), lim[kind] ?? lim.grass) * (thin[kind] ?? 1);
      const n = Math.ceil(m.userData.full * k);
      m.visible = n > 0; m.count = n;
    }
  });

  return <primitive object={group} />;
}
