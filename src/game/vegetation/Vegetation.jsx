// Scatters all vegetation with the toon plant models from Blender (public/models/env):
// grass tufts where the land is lush, reeds on wet banks, crops planted in rows per plot
// (berseem, wheat, maize, cotton / cabbage), earth bunds between plots, date palms and
// sycamores, bougainvillea in the gardens, wild flowers near homes. Everything is instanced;
// grass and crops are split into chunks so frustum culling and per-quality distance cut-offs
// skip what you can't see, and crop ink outlines are only drawn up close.
import { useMemo, useRef, useEffect } from 'react';
import * as THREE from 'three';
import { useFrame, useThree } from '@react-three/fiber';
import { height, fieldPlot, pathDist, riverZ, waterDist, hash, OASIS, RUINS, rng, fbm, smooth, WATER_Y, ROAD_CANALS } from '../terrain/heightfield.js';
import { bush, lump } from './plants.js';
import { instanceModels } from '../world/instancing.js';
import { mergedPlant } from '../world/envAssets.js';
import { toonMaterial, outlineMaterial, WIND } from '../shaders/toon.js';
import { TOON } from '../shaders/toonPalette.js';
import { usePreset, useDetail } from '../systems/store.js';
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
const plantMat = (key, wind) => toonMaterial('plant_' + key, { vertexColors: true, side: THREE.DoubleSide, wind, rim: 0.12 });
const tint = (r, spread = 0.18) => new THREE.Color(1, 1, 1).multiplyScalar(1 - spread / 2 + r() * spread);

export function Vegetation({ colliders, clearings, assets, gardens = [] }) {
  const preset = usePreset(), detail = useDetail();
  const camera = useThree(s => s.camera);
  const chunks = useRef([]), trees = useRef([]);

  const group = useMemo(() => {
    const r = rng(7), rs = rng(99), g = new THREE.Group();   // rs: shuffles only, so placement stays as before
    const add = (...o) => o.forEach(x => x && g.add(x));
    colliders.length = colliders.baseLength ??= colliders.length;   // rebuilds (quality change) replace, not append, tree colliders
    const blocked = (x, z, pad) => colliders.some(b => x > b.x0 - pad && x < b.x1 + pad && z > b.z0 - pad && z < b.z1 + pad)
      || clearings.some(([cx, cz, cr]) => Math.hypot(x - cx, z - cz) < cr + pad);
    const lush = (x, z, h) => h > WATER_Y + 0.55 && h < 14 && fieldPlot(x, z) < 0 && pathDist(x, z) > 2.2 && Math.hypot(x, z) > 22;
    const list = [];

    // chunked instancing: one body (+ optional ink hull) mesh per chunk × model
    const CH = 24;
    const bucket = () => new Map();
    const put = (map, key, x, z, m, c) => {
      const k = `${key}|${Math.floor(x / CH)},${Math.floor(z / CH)}`;
      if (!map.has(k)) map.set(k, { m: [], c: [] });
      map.get(k).m.push(m); if (c) map.get(k).c.push(c);
    };
    const flush = (map, kind, { wind, shadow = false, outline = true, geo, mat } = {}) => {
      for (const [k, v] of map) {
        const [model, cell] = k.split('|'), [cx, cz] = cell.split(',').map(Number), p = geo ? { body: geo, outline: null } : mergedPlant(assets, model);
        const center = new THREE.Vector3((cx + 0.5) * CH, 0, (cz + 0.5) * CH);
        shuffle(v.m, v.c, rs);
        const body = inst(p.body, mat ?? plantMat(model, wind), v.m, { colors: v.c.length ? v.c : null, shadow, layer: LAYER_NO_REFLECT });
        body.userData.center = center; body.userData.kind = kind; body.userData.full = v.m.length; g.add(body); list.push(body);
        if (outline && p.outline && detail.outlines) {
          const hull = inst(p.outline, outlineMaterial('env', wind), v.m, { receive: false, layer: LAYER_NO_REFLECT });
          hull.userData.center = center; hull.userData.kind = 'outline'; hull.userData.full = v.m.length; g.add(hull); list.push(hull);
        }
      }
    };

    // ---- grass tufts, chunked -------------------------------------------------------
    const grass = bucket();
    for (let i = 0, n = 0; i < detail.grass * 3 && n < detail.grass; i++) {
      const x = (r() - 0.5) * 360, z = (r() - 0.5) * 360 - 10, h = height(x, z);
      if (!lush(x, z, h) || blocked(x, z, 0.15)) continue;
      const patch = fbm(x * 0.05, z * 0.05);
      if (patch < -0.5 && r() < 0.6) continue;                 // a few natural bare patches
      const model = patch > 0.55 ? 'grass_c' : hash(Math.floor(x / 9), Math.floor(z / 9)) < 0.5 ? 'grass_a' : 'grass_b';
      put(grass, model, x, z, M(x, h - 0.03, z, r() * 6.3, 0.9 + r() * 0.5, 0.8 + r() * 0.7 + (waterDist(x, z) < 5 ? 0.4 : 0)), tint(r));
      n++;
    }
    flush(grass, 'grass', { wind: WIND.grass, outline: false });

    // ---- crops in rows, earth bunds between plots -------------------------------------
    const lowDetail = !detail.outlines;
    const crops = bucket(), R = lowDetail ? 105 : 140;   // lighter on LOW; the terrain paints the far fields
    for (let x = -204.6; x < 205; x += 0.8) for (let z = -149.7; z < 150; z += 0.6) {
      const far = Math.hypot(x, z);
      if (far > R || (far > R - 50 && r() < (far - R + 50) / 60)) continue;
      const t = fieldPlot(x, z); if (t < 0 || t === 4) continue;
      const row = Math.round(z / 0.6);
      if (t === 0 && (row % 4 === 1 || Math.round(x / 0.8) % 5 === 2)) continue;    // berseem: bushy, a little sparser
      if (t >= 2 && row % 2) continue;                                                 // maize, cotton, cabbage: rows 1.2 m apart
      if (t === 2 && r() > 0.85) continue;
      if (lowDetail && r() < 0.35) continue;                                          // LOW: a thinner planting
      if (blocked(x, z, 0.4)) continue;
      const jx = x + (r() - 0.5) * 0.2, h = height(jx, z);
      const model = t === 0 ? 'crop_berseem' : t === 1 ? 'crop_wheat' : t === 2 ? 'crop_maize'
        : hash(Math.floor((x + 1000) / 15), Math.floor((z + 1000) / 10)) < 0.5 ? 'crop_cotton' : 'crop_cabbage';
      const s = t === 0 ? 1 + r() * 0.35 : t === 1 ? 0.9 + r() * 0.25 : 0.85 + r() * 0.3;
      put(crops, model, jx, z, M(jx, h - 0.03, z, r() * 6.3, s, s * (0.9 + r() * 0.2)), tint(r, 0.12));
    }
    for (const [model, wind] of [['crop_berseem', WIND.crop], ['crop_wheat', WIND.wheat], ['crop_maize', WIND.maize], ['crop_cotton', WIND.crop], ['crop_cabbage', WIND.crop]]) {
      const only = new Map([...crops].filter(([k]) => k.startsWith(model + '|')));
      flush(only, 'crop', { wind });
    }
    const bunds = bucket(), RB = R - 40;
    for (let k = Math.ceil((-RB + 1000) / 15); k * 15 - 1000 < RB; k++) {   // bunds along x = 15k (run along z)
      const bx = k * 15 - 1000 + 0.45;
      for (let z = -RB; z < RB; z += 4) if (fieldPlot(bx, z) === 4 && fieldPlot(bx, z + 1.5) === 4 && fieldPlot(bx, z + 3) === 4 && Math.hypot(bx, z) < RB)
        put(bunds, 'field_bund', bx, z + 2, M(bx, height(bx, z + 2) - 0.1, z + 2, Math.PI / 2, 1));
    }
    for (let k = Math.ceil((-RB + 1000) / 10); k * 10 - 1000 < RB; k++) {   // bunds along z = 10k (run along x)
      const bz = k * 10 - 1000 + 0.35;
      for (let x = -RB; x < RB; x += 4) if (fieldPlot(x, bz) === 4 && fieldPlot(x + 1.5, bz) === 4 && fieldPlot(x + 3, bz) === 4 && Math.hypot(x, bz) < RB)
        put(bunds, 'field_bund', x + 2, bz, M(x + 2, height(x + 2, bz) - 0.1, bz, 0, 1));
    }
    flush(bunds, 'crop', {});

    // ---- reeds on wet banks ---------------------------------------------------------
    const reeds = bucket(); let nReeds = 0;
    for (let i = 0; i < 16000 && nReeds < 1500; i++) {
      let x, z;
      if (r() < 0.5) { x = (r() - 0.5) * 320; z = riverZ(x) + (r() - 0.5) * 22; }
      else { const seg = ROAD_CANALS[(r() * ROAD_CANALS.length) | 0], k = (r() * (seg.length - 1)) | 0, t = r();
        x = seg[k][0] + (seg[k + 1][0] - seg[k][0]) * t + (r() - 0.5) * 6; z = seg[k][1] + (seg[k + 1][1] - seg[k][1]) * t + (r() - 0.5) * 6; }
      const h = height(x, z), wd = waterDist(x, z);
      if (h < WATER_Y - 0.25 || h > WATER_Y + 1.6 || wd > 2.5 || blocked(x, z, 0.3)) continue;
      put(reeds, 'reeds', x, z, M(x, h - 0.05, z, r() * 6.3, 0.8 + r() * 0.5, 0.8 + r() * 0.5)); nReeds++;
    }
    flush(reeds, 'crop', { wind: WIND.reed, shadow: !lowDetail, outline: false });

    // ---- date palms (three variants) ------------------------------------------------------
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
    for (let i = 0; i < 30 * k; i++) { const x = -80 + r() * 160; tryPalm(x, 11 + r() * 1.5); }   // row along the field road
    for (const line of ROAD_CANALS) for (let j = 0; j + 1 < line.length; j++) {    // palm rows on the canal banks
      const [ax, az] = line[j], [bx, bz] = line[j + 1], L = Math.hypot(bx - ax, bz - az), nx = -(bz - az) / L, nz = (bx - ax) / L;
      for (let d = 3; d < L; d += 6.5 + r() * 3) if (r() < 0.8) for (const side of [-1, 1]) tryPalm(ax + (bx - ax) * d / L + nx * side * 3.3, az + (bz - az) * d / L + nz * side * 3.3);
    }
    for (let i = 0; i < 50 * k; i++) tryPalm((r() - 0.5) * 300, (r() - 0.5) * 200 - 20);
    for (let i = 0; i < 16 * k; i++) { const a = r() * 6.3, d = 20 + r() * 20; tryPalm(RUINS.x + Math.cos(a) * d, RUINS.z + Math.sin(a) * d); }
    const treePl = spots.map(([x, z, h], i) => { const sc = 0.85 + r() * 0.35; return { model: `palm_${'abc'[i % 3]}`, x, y: h - 0.1, z, rot: r() * 6.3, sx: sc }; });
    spots.forEach(([x, z]) => colliders.push({ x0: x - 0.4, x1: x + 0.4, z0: z - 0.4, z1: z + 0.4 }));

    // ---- sycamores (جميز): shade trees along the roads and around the village ------------------
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
    for (const [x, z, h] of treeSpots) treePl.push({ model: 'sycamore', x, y: h - 0.1, z, rot: r() * 6.3, sx: 0.72 + r() * 0.3 });
    treeSpots.forEach(([x, z]) => colliders.push({ x0: x - 0.5, x1: x + 0.5, z0: z - 0.5, z1: z + 0.5 }));

    // ---- bougainvillea in the street gardens -----------------------------------------------------
    for (const [x, z] of gardens) { const fx = x + (r() - 0.5) * 0.8, fz = z + (r() - 0.5) * 1.2; treePl.push({ model: 'bougainvillea', x: fx, y: height(fx, fz) - 0.05, z: fz, rot: r() * 6.3, sx: 0.85 + r() * 0.35 }); }
    trees.current = instanceModels(assets, treePl, { lodDistance: 60, outlines: detail.outlines });
    add(trees.current.group); trees.current.update(camera.position);

    // ---- bushes ----------------------------------------------------------------------------
    const bushes = bucket(), dryTint = new THREE.Color(1.3, 1.02, 0.55); let nBush = 0;
    for (let i = 0; i < 4000 && nBush < 500 * k; i++) {
      const x = (r() - 0.5) * 380, z = (r() - 0.5) * 320 - 10, h = height(x, z), dry = smooth(8, 20, h) * 0.6;
      if (h < WATER_Y + 0.5 || h > 11 || pathDist(x, z) < 2 || fieldPlot(x, z) >= 0 || blocked(x, z, 0.8) || Math.hypot(x, z) < 18) continue;
      put(bushes, 'bush', x, z, M(x, h - 0.05, z, r() * 6.3, 0.7 + r() * 0.9, 0.6 + r() * 0.6), tint(r, 0.2).lerp(dryTint, dry)); nBush++;
    }
    flush(bushes, 'bush', { geo: bush(31), mat: plantMat('bush', WIND.shrub), shadow: !lowDetail, outline: false });

    // ---- rocks: along banks, mountain feet and ruins ----------------------------------------------
    const rockM = [], rockC = [], stone = [new THREE.Color(TOON.toon_stone[0]), new THREE.Color(TOON.toon_stone_dark[0])];
    for (let i = 0; i < 6000 && rockM.length < 450; i++) {
      const x = (r() - 0.5) * 480, z = (r() - 0.5) * 480, h = height(x, z), wd = waterDist(x, z);
      const wild = z > 125 || Math.max(Math.abs(x), Math.abs(z)) > 180, bank = wd > 0 && wd < 1.6;
      if (!(wild || (bank && r() < 0.5)) || h < WATER_Y - 0.4 || pathDist(x, z) < 2.3 || blocked(x, z, 0.6) || fieldPlot(x, z) >= 0) continue;
      const s = bank ? 0.15 + r() * 0.35 : 0.3 + r() ** 3 * 3.5;
      rockM.push(M(x, h + s * 0.12, z, r() * 6.3, s, s * (0.55 + r() * 0.4), (r() - 0.5) * 0.4));
      rockC.push(stone[r() < 0.6 ? 0 : 1].clone().multiplyScalar(0.92 + r() * 0.16));
    }
    add(inst(lump(5), toonMaterial('rock', { vertexColors: true }), rockM, { colors: rockC, shadow: true }));

    // ---- fallen fronds/leaves under trees; wild flowers near homes and the oasis ------------------
    const litter = bucket(), litterPal = ['toon_frond_dry', 'toon_bark', 'toon_dates_gold', 'toon_leaf_dark'].map(n => new THREE.Color(TOON[n][0]));
    for (const [x, z] of [...spots, ...treeSpots]) for (let j = 0; j < 10; j++) {
      const a = r() * 6.3, d = 0.4 + r() * 2.2, lx = x + Math.cos(a) * d, lz = z + Math.sin(a) * d;
      put(litter, 'litter', lx, lz, M(lx, height(lx, lz) + 0.02, lz, r() * 6.3, 0.09 + r() * 0.06, 1, Math.PI / 2 - 0.1), litterPal[(r() * litterPal.length) | 0]);
    }
    flush(litter, 'grass', { geo: new THREE.CircleGeometry(1, 5), mat: toonMaterial('litter', { side: THREE.DoubleSide, rim: 0 }), outline: false });
    const fl = bucket(); let nFl = 0;
    for (let i = 0; i < 14000 && nFl < 1000 * k; i++) {
      const [ox, oz] = r() < 0.5 ? [0, 0] : [OASIS.x, OASIS.z], a = r() * 6.3, d = 14 + r() * 50;
      const x = ox + Math.cos(a) * d, z = oz + Math.sin(a) * d, h = height(x, z);
      if (!lush(x, z, h) || blocked(x, z, 0.3) || fbm(x * 0.07, z * 0.07) < 0.1) continue;
      put(fl, 'wildflowers', x, z, M(x, h - 0.02, z, r() * 6.3, 0.9 + r() * 0.4)); nFl++;
    }
    flush(fl, 'grass', { wind: WIND.shrub, outline: false });
    chunks.current = list;
    return g;
  }, [detail]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => () => group.traverse(o => {   // free GPU buffers when Settings rebuilds
    if (!o.isMesh) return; o.dispose?.(); if (o.userData.shared) return; o.geometry.dispose(); o.material.dispose();
  }), [group]);

  // Draw distances are measured from what the camera frames (the child, or the camera itself
  // in cinematics). Zooming out keeps grass, crops, reeds and bushes out to the edges of the
  // view but thinner (from 60 m a third of the tufts reads the same as all of them), and
  // drops the crop ink hulls.
  const acc = useRef(0), focus = useRef(new THREE.Vector3());
  useFrame((_, dt) => {
    if ((acc.current += dt) < 0.25) return; acc.current = 0;
    trees.current?.update(camera.position);
    const v = refs.view, z = v.zoom, f = focus.current;
    f.set(THREE.MathUtils.lerp(camera.position.x, v.x, z), 0, THREE.MathUtils.lerp(camera.position.z, v.z, z));
    const lim = { grass: preset.grassDist * (1 - 0.25 * z), crop: preset.cropDist + z * 60, bush: preset.bushDist + z * 50 };
    const thin = { grass: 1 - 0.6 * z, crop: 1 - 0.55 * z, bush: 1 - 0.3 * z }, camY2 = Math.max(0, camera.position.y) ** 2;
    for (const m of chunks.current) {
      const kind = m.userData.kind, c = m.userData.center;
      let k;
      if (kind === 'outline') {                                 // ink hulls: true distance to the lens
        const d2 = (c.x - camera.position.x) ** 2 + (c.z - camera.position.z) ** 2 + camY2;
        k = d2 < preset.outlineDist ** 2 ? 1 : 0;
      } else {
        k = density(Math.hypot(c.x - f.x, c.z - f.z), lim[kind]) * thin[kind];
      }
      const n = Math.ceil(m.userData.full * k);
      m.visible = n > 0; m.count = n;
    }
  });

  return <primitive object={group} />;
}
