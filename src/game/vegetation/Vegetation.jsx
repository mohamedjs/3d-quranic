// Scatters all v4 vegetation & rocks (public/models/env):
// - Date palms (4 variants with Poly Haven `palm_bark` + feathery fronds + dates)
// - Poly Haven broadleaf trees (`sycamore_a/b` from island_tree_02 & tree_small_02, desert `acacia`)
// - Poly Haven shrubs (`bush_a` from shrub_02, `bush_b` from shrub_04) with per-chunk LOD0/LOD1 swap
// - Poly Haven rocks (`boulder` from namaqualand_boulder_02, `rock_small` from rock_07) replacing `lump`
// - Hero botanical accents (`ph_grass_medium_01`, `ph_flower_gazania`, <= 60 each near water/oasis/gardens)
// - Cheap v3 grass/crops/reeds/papyrus/lotus cards warmly tinted to match the v4 Poly Haven palette.
// Tree/palm placement uses a dedicated RNG and oasis-shore clearings so walkability is green on all tiers.
import { useMemo, useRef, useEffect } from 'react';
import * as THREE from 'three';
import { useFrame, useThree } from '@react-three/fiber';
import { height, fieldPlot, pathDist, riverZ, waterDist, hash, OASIS, RUINS, rng, fbm, smooth, WATER_Y, ROAD_CANALS } from '../terrain/heightfield.js';
import { instanceModels } from '../world/instancing.js';
import { mergedPlant, upgradeFoliageAtlas } from '../world/envAssets.js';
import { toonMaterial, WIND } from '../shaders/toon.js';
import { envMaterial } from '../shaders/stylizedPbr.js';
import { TOON } from '../shaders/toonPalette.js';
import { usePreset, useDetail, useGame } from '../systems/store.js';
import { LAYER_NO_REFLECT } from '../systems/layers.js';
import { refs } from '../systems/refs.js';

// Chunk density: full inside 55 % of the draw distance, thinning to 20 % at its edge, then gone.
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
// Warm golden-olive tint harmonizing v3 grass/crop cards with the v4 Poly Haven palette
const tint = (r, spread = 0.16, warmR = 1.0, warmG = 1.0, warmB = 1.0) => {
  const k = 1 - spread / 2 + r() * spread;
  return new THREE.Color(warmR * k, warmG * k, warmB * k);
};

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
    const r = rng(7), rs = rng(99), rt = rng(707), rr = rng(809), g = new THREE.Group();
    const add = (...o) => o.forEach(x => x && g.add(x));
    colliders.length = colliders.baseLength ??= colliders.length;   // rebuilds replace, not append, tree colliders

    // Keep the narrow oasis east-shore big-star corridor clear of tree trunks on every tier
    const treeClearings = [...clearings, [OASIS.x + OASIS.r + 3.5, OASIS.z + 2, 4.0]];
    const blocked = (x, z, pad, extra = clearings) => colliders.some(b => x > b.x0 - pad && x < b.x1 + pad && z > b.z0 - pad && z < b.z1 + pad)
      || extra.some(([cx, cz, cr]) => Math.hypot(x - cx, z - cz) < cr + pad);
    const lush = (x, z, h) => h > WATER_Y + 0.55 && h < 14 && fieldPlot(x, z) < 0 && pathDist(x, z) > 2.2 && Math.hypot(x, z) > 22;
    const list = [];
    const shading = detail.shading ?? 'toon';

    // Tight 48 m chunks on Medium/High balance frustum/distance culling with low draw calls
    const CH = detail.lite ? 36 : 48;
    const bucket = () => new Map();
    const put = (map, key, x, z, m, c, cellSize = CH) => {
      const k = `${key}|${Math.floor(x / cellSize)},${Math.floor(z / cellSize)}|${cellSize}`;
      if (!map.has(k)) map.set(k, { m: [], c: [] });
      map.get(k).m.push(m); if (c) map.get(k).c.push(c);
    };
    const flush = (map, kind, { wind, shadow = false, geo, mat, layer = LAYER_NO_REFLECT, lodKind = null } = {}) => {
      for (const [k, v] of map) {
        const [model, cell, csStr] = k.split('|'), [cx, cz] = cell.split(',').map(Number), cs = Number(csStr) || CH;
        const p = geo ? { body: geo, bodyLod1: null, activeMaterial: null } : mergedPlant(assets, model);
        const center = new THREE.Vector3((cx + 0.5) * cs, 0, (cz + 0.5) * cs);
        shuffle(v.m, v.c, rs);
        const useMat = mat ?? p.activeMaterial ?? envMaterial('plant_' + model, { shading, vertexColors: true, side: THREE.DoubleSide, wind, rim: 0.12, sss: 0.45 });
        const body = inst(p.body, useMat, v.m, { colors: v.c.length ? v.c : null, shadow, layer });
        body.userData.center = center;
        body.userData.kind = kind;
        body.userData.full = v.m.length;
        if (p.bodyLod1) {
          body.userData.geo0 = p.body;
          body.userData.geo1 = p.bodyLod1;
          body.userData.lodKind = lodKind ?? kind;
          body.userData.castNear = shadow;
        }
        g.add(body); list.push(body);
      }
    };

    // ---- grass tufts, chunked (v3 cards warmly tinted to v4 palette) ----------------
    const grass = bucket();
    for (let i = 0, n = 0; i < detail.grass * 3 && n < detail.grass; i++) {
      const x = (r() - 0.5) * 360, z = (r() - 0.5) * 360 - 10, h = height(x, z);
      if (!lush(x, z, h) || blocked(x, z, 0.15)) continue;
      const patch = fbm(x * 0.05, z * 0.05);
      if (patch < -0.5 && r() < 0.6) continue;
      const model = detail.lite ? 'grass_a' : patch > 0.55 ? 'grass_c' : hash(Math.floor(x / 9), Math.floor(z / 9)) < 0.5 ? 'grass_a' : 'grass_b';
      const scBoost = detail.lite ? 1.0 : 1.12;
      put(grass, model, x, z, M(x, h - 0.03, z, r() * 6.3, (0.95 + r() * 0.5) * scBoost, (0.85 + r() * 0.7 + (waterDist(x, z) < 5 ? 0.4 : 0)) * scBoost), tint(r, 0.16, 0.96, 0.94, 0.80));
      n++;
    }
    flush(grass, 'grass', { wind: WIND.grass });

    // ---- crops in rows, earth bunds between plots (thinned cleanly per tier) --------
    const cropThin = detail.cropThin ?? (detail.outlines ? 0.44 : 0.65);
    const crops = bucket(), R = detail.lite ? 95 : 132;
    const cropScaleBoost = 1 + cropThin * 0.24;
    for (let x = -204.6; x < 205; x += 0.8) for (let z = -149.7; z < 150; z += 0.6) {
      const far = Math.hypot(x, z);
      if (far > R || (far > R - 42 && r() < (far - R + 42) / 50)) continue;
      const t = fieldPlot(x, z); if (t < 0 || t === 4) continue;
      const row = Math.round(z / 0.6);
      if (t === 0 && (row % 4 === 1 || Math.round(x / 0.8) % 5 === 2)) continue;
      if (t >= 2 && row % 2) continue;
      if (t === 2 && r() > 0.85) continue;
      // Extra thinning on heavy 177-tri wheat clumps with matching scale compensation keeps golden fields lush under budget
      const thin = t === 1 ? Math.min(0.88, cropThin + (detail.lite ? 0.04 : 0.22)) : cropThin;
      if (r() < thin) continue;
      if (blocked(x, z, 0.4)) continue;
      const jx = x + (r() - 0.5) * 0.2, h = height(jx, z);
      const model = t === 0 ? 'crop_berseem' : t === 1 ? 'crop_wheat' : t === 2 ? 'crop_maize'
        : hash(Math.floor((x + 1000) / 15), Math.floor((z + 1000) / 10)) < 0.5 ? 'crop_cotton' : 'crop_cabbage';
      const s = (t === 0 ? 1.05 + r() * 0.35 : t === 1 ? 1.05 + r() * 0.28 : 0.92 + r() * 0.3) * cropScaleBoost;
      put(crops, model, jx, z, M(jx, h - 0.03, z, r() * 6.3, s, s * (0.9 + r() * 0.2)), tint(r, 0.14, 0.98, 0.95, 0.84));
    }
    flush(crops, 'crop', {});

    const bunds = bucket(), RB = R - 32;
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
    // Dedicated RNG & 32 m Lite chunks (48 m Med+) keep bank reeds lush along the Nile and road canal
    const reeds = bucket(), rw = rng(313); let nReeds = 0;
    const maxReeds = detail.lite ? 1500 : 1200;
    const reedCell = detail.lite ? 32 : 48;
    for (let i = 0; i < 16000 && nReeds < maxReeds; i++) {
      let x, z;
      if (rw() < 0.45) { x = (rw() - 0.5) * 320; z = riverZ(x) + (rw() - 0.5) * 22; }
      else if (rw() < 0.16) {
        const a = rw() * 6.3, d = 14.5 + rw() * 3.5;
        x = OASIS.x + Math.cos(a) * d; z = OASIS.z + Math.sin(a) * d;
      } else {
        const seg = ROAD_CANALS[(rw() * ROAD_CANALS.length) | 0], k = (rw() * (seg.length - 1)) | 0, t = rw();
        x = seg[k][0] + (seg[k + 1][0] - seg[k][0]) * t + (rw() - 0.5) * 6; z = seg[k][1] + (seg[k + 1][1] - seg[k][1]) * t + (rw() - 0.5) * 6;
      }
      const h = height(x, z), wd = waterDist(x, z);
      if (h < WATER_Y - 0.25 || h > WATER_Y + 1.6 || wd > 2.5 || pathDist(x, z) < 2.1 || blocked(x, z, 0.35)) continue;
      const isPapyrus = !detail.lite && (hash(Math.floor(x / 5), Math.floor(z / 5)) > 0.68);
      put(reeds, isPapyrus ? 'papyrus' : 'reeds', x, z, M(x, h - 0.05, z, rw() * 6.3, 0.85 + rw() * 0.45, 0.85 + rw() * 0.45), null, reedCell);
      nReeds++;
    }
    // Guarantee lush cattail & reed clumps along the north-road canal approach and Nile banks near the bridge
    for (let i = 0, added = 0; i < 400 && added < 36; i++) {
      const alongCanal = i % 2 === 0;
      const x = alongCanal ? (2.4 + rw() * 3.8) : (-26 + rw() * 52);
      const z = alongCanal ? (45 + rw() * 14) : (riverZ(x) + (rw() < 0.5 ? -1 : 1) * (5.2 + rw() * 3.8));
      const h = height(x, z), wd = waterDist(x, z);
      if (h < WATER_Y - 0.25 || h > WATER_Y + 1.6 || wd > 2.5 || pathDist(x, z) < 2.2 || blocked(x, z, 0.35)) continue;
      const isPapyrus = !detail.lite && (hash(Math.floor(x / 5), Math.floor(z / 5)) > 0.68);
      put(reeds, isPapyrus ? 'papyrus' : 'reeds', x, z, M(x, h - 0.05, z, rw() * 6.3, 0.90 + rw() * 0.42, 0.90 + rw() * 0.45), null, reedCell);
      added++;
    }
    flush(reeds, 'reed', { shadow: false });

    // ---- floating oasis lotus pads around the shallow outer spring rim --------------
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
      const lm = inst(lp.body, lp.activeMaterial, lotusM, { shadow: false, receive: true, layer: LAYER_NO_REFLECT });
      lm.userData.center = new THREE.Vector3(OASIS.x, 0, OASIS.z);
      lm.userData.kind = 'grass';
      lm.userData.full = lotusM.length;
      g.add(lm);
      list.push(lm);
    }

    // ---- date palms (4 v4 variants with Poly Haven `palm_bark`, dedicated RNG `rt`) --
    const spots = [];
    const tryPalm = (x, z, force = false) => {
      const h = height(x, z);
      if (!force) {
        if (h < WATER_Y + 0.40 || h > 9 || pathDist(x, z) < 2.6 || fieldPlot(x, z) >= 0 || blocked(x, z, 1.3, treeClearings)) return;
        if (spots.some(p => Math.hypot(p[0] - x, p[1] - z) < 3.2)) return;
      }
      spots.push([x, z, h]);
    };
    const k = detail.trees;
    tryPalm(-13.4, 23.2, true); tryPalm(-12.8, 30.4, true);          // framing grandma's house, by the canal
    for (let i = 0; i < 100 * k; i++) { const a = rt() * 6.3, d = 16.5 + rt() * 24; tryPalm(OASIS.x + Math.cos(a) * d, OASIS.z + Math.sin(a) * d); }
    for (let i = 0; i < 70 * k; i++) { const a = rt() * 6.3, d = 12 + rt() * 30; tryPalm(Math.cos(a) * d, Math.sin(a) * d); }
    for (let i = 0; i < 110 * k; i++) { const x = -200 + rt() * 290, s = rt() < 0.5 ? -1 : 1; tryPalm(x, riverZ(x) + s * (8 + rt() * 9)); }
    for (let i = 0; i < 30 * k; i++) { const x = -80 + rt() * 160; tryPalm(x, 11 + rt() * 1.5); }
    for (const line of ROAD_CANALS) for (let j = 0; j + 1 < line.length; j++) {
      const [ax, az] = line[j], [bx, bz] = line[j + 1], L = Math.hypot(bx - ax, bz - az), nx = -(bz - az) / L, nz = (bx - ax) / L;
      for (let d = 3; d < L; d += 6.5 + rt() * 3) if (rt() < 0.8) for (const side of [-1, 1]) tryPalm(ax + (bx - ax) * d / L + nx * side * 3.3, az + (bz - az) * d / L + nz * side * 3.3);
    }
    for (let i = 0; i < 50 * k; i++) tryPalm((rt() - 0.5) * 300, (rt() - 0.5) * 200 - 20);
    for (let i = 0; i < 16 * k; i++) { const a = rt() * 6.3, d = 20 + rt() * 20; tryPalm(RUINS.x + Math.cos(a) * d, RUINS.z + Math.sin(a) * d); }
    const palmNames = ['palm_a', 'palm_b', 'palm_c', 'palm_d'];
    const treePl = spots.map(([x, z, h], i) => {
      const sc = 0.85 + rt() * 0.35;
      return { model: palmNames[i % palmNames.length], x, y: h - 0.1, z, rot: rt() * 6.3, sx: sc };
    });
    spots.forEach(([x, z]) => colliders.push({ x0: x - 0.4, x1: x + 0.4, z0: z - 0.4, z1: z + 0.4 }));

    // ---- Poly Haven broadleaf sycamores (`sycamore_a/b`) & desert umbrella `acacia` --
    const treeSpots = [];
    const okTree = (x, z, h, pad) => h > WATER_Y + 0.6 && !blocked(x, z, pad, treeClearings) && fieldPlot(x, z) < 0 && pathDist(x, z) > 3.2
      && !spots.some(p => Math.hypot(p[0] - x, p[1] - z) < 4.5) && !treeSpots.some(p => Math.hypot(p[0] - x, p[1] - z) < 7);
    for (const [x, z] of [[-4.6, 31.8], [5.2, 52], [-5.2, 58], [5.2, 63], [-26, 6], [22, -2], [-36, -4]]) {
      const h = height(x, z); if (okTree(x, z, h, 1)) treeSpots.push([x, z, h]);
    }
    for (const [[ax, az], [bx, bz]] of [[[0, -95], [0, -60]], [[-44, -9], [-96, -19]], [[44, -11], [130, -34]], [[0, 50], [0, 64]], [[-75, 12], [-50, 12]], [[50, 12], [75, 12]]]) {
      const L = Math.hypot(bx - ax, bz - az), nx = -(bz - az) / L, nz = (bx - ax) / L;
      for (let d = 4; d < L; d += 14 + rt() * 8) for (const side of [-1, 1]) {
        const x = ax + (bx - ax) * d / L + nx * side * 6, z = az + (bz - az) * d / L + nz * side * 6, h = height(x, z);
        if (rt() < 0.6 && okTree(x, z, h, 1.4)) treeSpots.push([x, z, h]);
      }
    }
    for (let i = 0; i < 1500 && treeSpots.length < 90 * k; i++) {
      const x = (rt() - 0.5) * 360, z = (rt() - 0.5) * 300 - 10, h = height(x, z);
      if (lush(x, z, h) && okTree(x, z, h, 2)) treeSpots.push([x, z, h]);
    }
    treeSpots.forEach(([x, z, h], i) => {
      const isDesertEdge = (x > 65 && z < 15) || h > 6.5 || (Math.hypot(x - RUINS.x, z - RUINS.z) < 75);
      const model = isDesertEdge ? 'acacia' : (i % 2 === 0 ? 'sycamore_a' : 'sycamore_b');
      treePl.push({ model, x, y: h - 0.1, z, rot: rt() * 6.3, sx: 0.78 + rt() * 0.28 });
    });
    treeSpots.forEach(([x, z]) => colliders.push({ x0: x - 0.5, x1: x + 0.5, z0: z - 0.5, z1: z + 0.5 }));

    // Dedicated desert umbrella acacias scattered strictly clear of all 22 storytellers & paths
    const acaciaExtra = [];
    for (let i = 0; i < 420 && acaciaExtra.length < Math.round(28 * k); i++) {
      const x = 68 + rt() * 140, z = -160 + rt() * 170;
      const h = height(x, z);
      if (h < WATER_Y + 0.8 || h > 16 || fieldPlot(x, z) >= 0 || pathDist(x, z) < 4.5 || blocked(x, z, 2.8, treeClearings)) continue;
      if (spots.some(p => Math.hypot(p[0] - x, p[1] - z) < 6) || treeSpots.some(p => Math.hypot(p[0] - x, p[1] - z) < 8)
        || acaciaExtra.some(p => Math.hypot(p[0] - x, p[1] - z) < 11)) continue;
      acaciaExtra.push([x, z, h]);
      treePl.push({ model: 'acacia', x, y: h - 0.12, z, rot: rt() * 6.3, sx: 0.84 + rt() * 0.34 });
    }
    acaciaExtra.forEach(([x, z]) => colliders.push({ x0: x - 0.45, x1: x + 0.45, z0: z - 0.45, z1: z + 0.45 }));

    // ---- bougainvillea in the street gardens ----------------------------------------
    for (const [x, z] of gardens) {
      const fx = x + (rt() - 0.5) * 0.8, fz = z + (rt() - 0.5) * 1.2;
      treePl.push({ model: 'bougainvillea_bush', x: fx, y: height(fx, fz) - 0.05, z: fz, rot: rt() * 6.3, sx: 0.85 + rt() * 0.35 });
    }
    g.userData.treePl = treePl;
    if (onTrees) trees.current = null;                            // LITE: <World/> merges them with the other props
    else {
      // Distant trees use LOD1; LOD0 only close to camera (`treeLodDist`)
      trees.current = instanceModels(assets, treePl, { lodDistance: detail.treeLodDist ?? detail.lodDist ?? 28, outlines: false });
      add(trees.current.group); trees.current.update(camera.position); g.userData.trees = trees.current;
    }

    // ---- Poly Haven shrubs (`bush_a` lush Nile, `bush_b` golden desert scrub, LOD0/LOD1) --
    const bushes = bucket(); let nBush = 0;
    const maxBush = Math.round(380 * k);
    for (let i = 0; i < 4000 && nBush < maxBush; i++) {
      const x = (r() - 0.5) * 380, z = (r() - 0.5) * 320 - 10, h = height(x, z), dry = smooth(6, 16, h) * 0.7 + (x > 70 ? 0.5 : 0);
      if (h < WATER_Y + 0.5 || h > 12 || pathDist(x, z) < 2.2 || fieldPlot(x, z) >= 0 || blocked(x, z, 0.9) || Math.hypot(x, z) < 18) continue;
      const model = dry > 0.45 ? 'bush_b' : 'bush_a';
      put(bushes, model, x, z, M(x, h - 0.04, z, r() * 6.3, 0.72 + r() * 0.65, 0.72 + r() * 0.48), null, CH);
      nBush++;
    }
    flush(bushes, 'bush', { shadow: false, lodKind: 'bush' });

    // ---- Hero Poly Haven botanical accents (<= 60 each near water, oasis & house gardens) --
    const maxHero = Math.min(60, detail.heroAccents ?? 0);
    if (maxHero > 0) {
      const accents = bucket();
      let nGrass = 0, nFlw = 0;
      // Street & house gardens get flowering gazanias + lush grass tufts
      for (const [gx, gz] of gardens) {
        if (nFlw < Math.min(20, maxHero)) {
          const x = gx + (r() - 0.5) * 1.4, z = gz + (r() - 0.5) * 1.4, h = height(x, z);
          if (h > WATER_Y + 0.3 && pathDist(x, z) > 1.7 && !blocked(x, z, 0.25)) {
            const s = 1.45 + r() * 0.55;
            put(accents, 'ph_flower_gazania', x, z, M(x, h - 0.02, z, r() * 6.3, s, s), null, 64);
            nFlw++;
          }
        }
        if (nGrass < Math.min(18, maxHero)) {
          const x = gx + (r() - 0.5) * 1.8, z = gz + (r() - 0.5) * 1.8, h = height(x, z);
          if (h > WATER_Y + 0.3 && pathDist(x, z) > 1.7 && !blocked(x, z, 0.25)) {
            const s = 1.7 + r() * 0.65;
            put(accents, 'ph_grass_medium_01', x, z, M(x, h - 0.02, z, r() * 6.3, s, s), null, 64);
            nGrass++;
          }
        }
      }
      // Oasis rim & Nile river / canal banks
      for (let i = 0; i < 600 && (nGrass < maxHero || nFlw < maxHero); i++) {
        let x, z;
        if (i % 2 === 0) {
          const a = r() * 6.3, d = OASIS.r + 1.2 + r() * 7.5;
          x = OASIS.x + Math.cos(a) * d; z = OASIS.z + Math.sin(a) * d;
        } else {
          x = -140 + r() * 240; z = riverZ(x) + (r() < 0.5 ? -1 : 1) * (6.8 + r() * 4.5);
        }
        const h = height(x, z);
        if (h < WATER_Y + 0.15 || h > 5 || pathDist(x, z) < 1.9 || fieldPlot(x, z) >= 0 || blocked(x, z, 0.35)) continue;
        if (nGrass < maxHero && (i % 3 !== 0 || nFlw >= maxHero)) {
          const s = 1.8 + r() * 0.75;
          put(accents, 'ph_grass_medium_01', x, z, M(x, h - 0.02, z, r() * 6.3, s, s), null, 64);
          nGrass++;
        } else if (nFlw < maxHero) {
          const s = 1.4 + r() * 0.55;
          put(accents, 'ph_flower_gazania', x, z, M(x, h - 0.02, z, r() * 6.3, s, s), null, 64);
          nFlw++;
        }
      }
      flush(accents, 'accent', { shadow: false });
    }

    // ---- Poly Haven rocks: `boulder` (river banks, hill feet & ruins) + `rock_small` scattered --
    const boulders = bucket(), smallRocks = bucket();
    const maxRocks = detail.rocks ?? 260;
    const maxBoulders = Math.round(maxRocks * 0.46), maxSmall = Math.round(maxRocks * 0.54);
    let nB = 0, nS = 0;
    // Signature boulder clusters framing the ancient ruins & hillside approaches
    for (let i = 0; i < 240 && nB < Math.min(34, maxBoulders); i++) {
      const a = rr() * 6.3, d = 14 + rr() * 28;
      const x = RUINS.x + Math.cos(a) * d, z = RUINS.z + Math.sin(a) * d, h = height(x, z);
      if (h < WATER_Y + 0.3 || pathDist(x, z) < 2.8 || blocked(x, z, 1.4, treeClearings)) continue;
      const s = 0.75 + rr() * 1.15, sy = s * (0.75 + rr() * 0.45);
      put(boulders, 'boulder', x, z, M(x, h - 0.10 * sy, z, rr() * 6.3, s, sy, (rr() - 0.5) * 0.22), null, 64);
      nB++;
    }
    // Riverbanks, oasis outer rocky fringe & mountain feet
    for (let i = 0; i < 5500 && (nB < maxBoulders || nS < maxSmall); i++) {
      const x = (rr() - 0.5) * 460, z = (rr() - 0.5) * 460, h = height(x, z), wd = waterDist(x, z);
      const hillFoot = (z > 105 && h > 2.2) || Math.max(Math.abs(x), Math.abs(z)) > 168;
      const ruinsArea = Math.hypot(x - RUINS.x, z - RUINS.z) < 55;
      const bank = wd > 0.1 && wd < 2.2 && Math.abs(z - riverZ(x)) < 16;
      if (!(hillFoot || ruinsArea || (bank && rr() < 0.65)) || h < WATER_Y - 0.2 || pathDist(x, z) < 2.5 || blocked(x, z, 0.9, treeClearings) || fieldPlot(x, z) >= 0) continue;
      const wantBig = nB < maxBoulders && (hillFoot || ruinsArea ? rr() < 0.55 : rr() < 0.35);
      if (wantBig) {
        const s = bank ? 0.42 + rr() * 0.55 : 0.65 + rr() ** 2 * 1.45;
        const sy = s * (0.72 + rr() * 0.42);
        put(boulders, 'boulder', x, z, M(x, h - 0.10 * sy, z, rr() * 6.3, s, sy, (rr() - 0.5) * 0.25), null, 64);
        nB++;
      } else if (nS < maxSmall) {
        const s = bank ? 0.45 + rr() * 0.65 : 0.65 + rr() * 1.05;
        const sy = s * (0.70 + rr() * 0.45);
        put(smallRocks, 'rock_small', x, z, M(x, h - 0.05 * sy, z, rr() * 6.3, s, sy, (rr() - 0.5) * 0.35), null, 64);
        nS++;
      }
    }
    flush(boulders, 'boulder', { shadow: false, layer: LAYER_NO_REFLECT, lodKind: 'boulder' });
    flush(smallRocks, 'rock', { shadow: false });

    // ---- fallen fronds/leaves under trees (tight distance, coarse chunks); wildflowers --
    const litter = bucket(), litterPal = ['toon_frond_dry', 'toon_bark', 'toon_dates_gold', 'toon_leaf_dark'].map(n => new THREE.Color(TOON[n][0]));
    if (detail.litter !== false) for (const [x, z] of [...spots, ...treeSpots]) for (let j = 0; j < 5; j++) {
      const a = r() * 6.3, d = 0.4 + r() * 2.2, lx = x + Math.cos(a) * d, lz = z + Math.sin(a) * d;
      put(litter, 'litter', lx, lz, M(lx, height(lx, lz) + 0.02, lz, r() * 6.3, 0.09 + r() * 0.06, 1, Math.PI / 2 - 0.1), litterPal[(r() * litterPal.length) | 0], 72);
    }
    flush(litter, 'litter', { geo: new THREE.CircleGeometry(1, 5), mat: toonMaterial('litter', { side: THREE.DoubleSide, rim: 0 }) });

    const fl = bucket(); let nFl = 0;
    for (let i = 0; !detail.lite && i < 10000 && nFl < 680 * k; i++) {
      const [ox, oz] = r() < 0.5 ? [0, 0] : [OASIS.x, OASIS.z], a = r() * 6.3, d = 14 + r() * 48;
      const x = ox + Math.cos(a) * d, z = oz + Math.sin(a) * d, h = height(x, z);
      if (!lush(x, z, h) || blocked(x, z, 0.3) || fbm(x * 0.07, z * 0.07) < 0.1) continue;
      put(fl, 'wildflowers', x, z, M(x, h - 0.02, z, r() * 6.3, 0.95 + r() * 0.4), null, 64); nFl++;
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
      reed: (preset.lite ? 38 : preset.grassDist) * (1 - 0.2 * z),
      crop: preset.cropDist + z * 48,
      bush: Math.min(preset.bushDist, 100) + z * 32,
      accent: Math.min(preset.grassDist, 44),
      boulder: (preset.lite ? 95 : 155) + z * 45,
      rock: Math.min(preset.bushDist, 72) + z * 20,
      flower: Math.min(preset.grassDist, 52),
      litter: 32,
    };
    const lodLim = {
      bush: preset.bushLodDist ?? 24,
      boulder: (preset.lodDist ?? 32) + 12,
    };
    const thin = { grass: 1 - 0.6 * z, reed: 1 - 0.35 * z, crop: 1 - 0.55 * z, bush: 1 - 0.3 * z, accent: 1 - 0.5 * z, boulder: 1, rock: 1 - 0.4 * z, flower: 1 - 0.5 * z, litter: 1 - 0.7 * z };
    for (const m of chunks.current) {
      const kind = m.userData.kind, c = m.userData.center;
      const d = Math.hypot(c.x - f.x, c.z - f.z);
      const k = density(d, lim[kind] ?? lim.grass) * (thin[kind] ?? 1);
      const n = Math.ceil(m.userData.full * k);
      m.visible = n > 0; m.count = n;
      if (m.visible && m.userData.geo1) {
        const useFar = d >= (lodLim[m.userData.lodKind] ?? 26);
        const wantGeo = useFar ? m.userData.geo1 : m.userData.geo0;
        if (m.geometry !== wantGeo) m.geometry = wantGeo;
      }
    }
  });

  return <primitive object={group} />;
}
