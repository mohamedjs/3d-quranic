// Scatters all vegetation. Placement follows the land (grass where it is lush, dry tufts
// toward the desert, reeds on wet banks, crops in rows per plot, palms around water and
// homes). Everything is instanced; grass is split into chunks so frustum culling and a
// distance cut-off skip what you can't see.
import { useMemo, useRef, useEffect } from 'react';
import * as THREE from 'three';
import { useFrame, useThree } from '@react-three/fiber';
import { height, fieldPlot, pathDist, riverZ, waterDist, OASIS, RUINS, rng, fbm, smooth, WATER_Y, ROAD_CANALS } from '../terrain/heightfield.js';
import { grassClump, wheatClump, leafyCrop, reedClump, tree, bush, lump, flowerBush } from './plants.js';
import { instanceModels } from '../world/instancing.js';
import { windy } from '../shaders/wind.js';
import { triplanarMaterial } from '../shaders/triplanar.js';
import { pbrSet } from '../systems/textures.js';
import { usePreset, useDetail } from '../systems/store.js';
import { LAYER_NO_REFLECT } from '../systems/layers.js';

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
  return m;
}
const leafMat = (key, opts) => windy(new THREE.MeshStandardMaterial({ vertexColors: true, side: THREE.DoubleSide, roughness: 0.75 }), key, opts);

export function Vegetation({ colliders, clearings, assets, gardens = [] }) {
  const preset = usePreset(), detail = useDetail();
  const camera = useThree(s => s.camera);
  const chunks = useRef([]), palms = useRef(null);

  const group = useMemo(() => {
    const r = rng(7), g = new THREE.Group(), c = new THREE.Color();
    const add = (...o) => o.forEach(x => x && g.add(x));
    colliders.length = colliders.baseLength ??= colliders.length;   // rebuilds (quality change) replace, not append, tree colliders
    const blocked = (x, z, pad) => colliders.some(b => x > b.x0 - pad && x < b.x1 + pad && z > b.z0 - pad && z < b.z1 + pad)
      || clearings.some(([cx, cz, cr]) => Math.hypot(x - cx, z - cz) < cr + pad);
    const lush = (x, z, h) => h > WATER_Y + 0.55 && h < 14 && fieldPlot(x, z) < 0 && pathDist(x, z) > 2.2 && Math.hypot(x, z) > 22;

    // ---- grass, chunked -----------------------------------------------------
    const CH = 24, cells = new Map(), dryCells = new Map();
    const grassGeo = grassClump(1), dryGeo = grassClump(9, true);
    const grassMat = leafMat('grass', { strength: 0.16, factor: 'position.y / .6', translucency: 0.35 });
    for (let i = 0, n = 0; i < detail.grass * 3 && n < detail.grass; i++) {
      const x = (r() - 0.5) * 360, z = (r() - 0.5) * 360 - 10, h = height(x, z);
      if (!lush(x, z, h) || blocked(x, z, 0.15)) continue;
      const patch = fbm(x * 0.05, z * 0.05);
      if (patch < -0.5 && r() < 0.6) continue;                 // a few natural bare patches
      const dry = patch > 0.62;                                   // only the odd straw-coloured tuft
      const key = `${Math.floor(x / CH)},${Math.floor(z / CH)}`, map = dry ? dryCells : cells;
      if (!map.has(key)) map.set(key, { m: [], c: [] });
      map.get(key).m.push(M(x, h - 0.04, z, r() * 6.3, 0.8 + r() * 0.7, 0.7 + r() * 0.8 + (waterDist(x, z) < 5 ? 0.4 : 0)));
      map.get(key).c.push(c.setHSL(dry ? 0.12 : 0.2 + r() * 0.05, dry ? 0.35 : 0.3 + r() * 0.2, 0.5 + r() * 0.15).clone());
      n++;
    }
    const list = [];
    for (const [map, geo] of [[cells, grassGeo], [dryCells, dryGeo]]) for (const [key, v] of map) {
      const m = inst(geo, grassMat, v.m, { colors: v.c, layer: LAYER_NO_REFLECT });
      const [cx, cz] = key.split(',').map(Number);
      m.userData.center = new THREE.Vector3((cx + 0.5) * CH, 0, (cz + 0.5) * CH);
      g.add(m); list.push(m);
    }
    chunks.current = list;

    // ---- crops, planted in rows ---------------------------------------------------
    const wheat = [], wheatC = [], greens = [], greensC = [];
    for (let x = -204.6; x < 205; x += 0.75) for (let z = -149.7; z < 150; z += 0.55) {
      const far = Math.hypot(x, z);
      const near = detail.grass < 30000 ? 45 : 75;                       // lighter on LOW
      if (far > near + 65 || (far > near && r() < (far - near) / 80)) continue;   // terrain colour carries the far fields
      const t = fieldPlot(x, z); if (t < 0 || t === 4) continue;
      if (blocked(x, z, 0.4)) continue;
      const jx = x + (r() - 0.5) * 0.2, h = height(jx, z);
      if (t === 1) { wheat.push(M(jx, h - 0.03, z, r() * 6.3, 0.9 + r() * 0.3, 0.85 + r() * 0.3)); wheatC.push(c.setHSL(0.11 + r() * 0.02, 0.5, 0.62 + r() * 0.1).clone()); }
      else if (t === 2) { if ((Math.round(z / 0.55) & 1) && r() < 0.8) { greens.push(M(jx, h - 0.02, z, r() * 6.3, 1.3, 5.5 + r() * 1.5)); greensC.push(c.setHSL(0.25, 0.45, 0.42 + r() * 0.08).clone()); } }   // maize
      else { greens.push(M(jx, h - 0.02, z, r() * 6.3, t === 0 ? 1.3 : 0.9, t === 0 ? 1.2 : 0.8)); greensC.push(c.setHSL(0.26 + r() * 0.03, 0.55, 0.48 + r() * 0.1).clone()); }
    }
    add(inst(wheatClump(), leafMat('wheat', { strength: 0.12, factor: 'position.y' }), wheat, { colors: wheatC, layer: LAYER_NO_REFLECT }));
    add(inst(leafyCrop(), leafMat('greens', { strength: 0.08, factor: 'position.y * 3.', translucency: 0.4 }), greens, { colors: greensC, layer: LAYER_NO_REFLECT }));

    // ---- reeds on wet banks ---------------------------------------------------------
    const reeds = [];
    for (let i = 0; i < 16000 && reeds.length < 1500; i++) {
      let x, z;
      if (r() < 0.5) { x = (r() - 0.5) * 320; z = riverZ(x) + (r() - 0.5) * 22; }
      else { const seg = ROAD_CANALS[(r() * ROAD_CANALS.length) | 0], k = (r() * (seg.length - 1)) | 0, t = r();
        x = seg[k][0] + (seg[k + 1][0] - seg[k][0]) * t + (r() - 0.5) * 6; z = seg[k][1] + (seg[k + 1][1] - seg[k][1]) * t + (r() - 0.5) * 6; }
      const h = height(x, z), wd = waterDist(x, z);
      if (h < WATER_Y - 0.25 || h > WATER_Y + 1.6 || wd > 2.5 || blocked(x, z, 0.3)) continue;
      reeds.push(M(x, h - 0.05, z, r() * 6.3, 0.8 + r() * 0.5, 0.8 + r() * 0.5));
    }
    add(inst(reedClump(), leafMat('reeds', { strength: 0.16, factor: 'position.y / 1.6' }), reeds, { shadow: true }));

    // ---- palms (three variants) ------------------------------------------------------
    const spots = [];
    const tryPalm = (x, z) => {
      const h = height(x, z);
      if (h < WATER_Y + 0.4 || h > 9 || pathDist(x, z) < 2.6 || fieldPlot(x, z) >= 0 || blocked(x, z, 1.3)) return;
      if (spots.some(p => Math.hypot(p[0] - x, p[1] - z) < 3.2)) return;
      spots.push([x, z, h]);
    };
    const k = detail.trees;
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
    // Blender date palms (three variants, detailed near / simplified far)
    const palmPl = spots.map(([x, z, h], i) => { const sc = 0.85 + r() * 0.35; return { model: `palm_${'abc'[i % 3]}`, x, y: h - 0.1, z, rot: r() * 6.3, sx: sc }; });
    palms.current = instanceModels(assets, palmPl, { lodDistance: 60 });
    add(palms.current.group);
    spots.forEach(([x, z]) => colliders.push({ x0: x - 0.4, x1: x + 0.4, z0: z - 0.4, z1: z + 0.4 }));

    // ---- broadleaf trees (three structures, tinted per instance) -------------------------
    const treeSpots = [];
    for (const [[ax, az], [bx, bz]] of [[[0, -95], [0, -60]], [[-44, -9], [-96, -19]], [[44, -11], [130, -34]], [[0, 50], [0, 64]], [[-75, 12], [-50, 12]], [[50, 12], [75, 12]]]) {
      const L = Math.hypot(bx - ax, bz - az), nx = -(bz - az) / L, nz = (bx - ax) / L;
      for (let d = 4; d < L; d += 11 + r() * 6) for (const side of [-1, 1]) {
        const x = ax + (bx - ax) * d / L + nx * side * 5.2, z = az + (bz - az) * d / L + nz * side * 5.2, h = height(x, z);
        if (r() < 0.65 && h > WATER_Y + 0.6 && !blocked(x, z, 1.4) && fieldPlot(x, z) < 0 && !spots.some(p => Math.hypot(p[0] - x, p[1] - z) < 3.5)) treeSpots.push([x, z, h]);
      }
    }
    for (let i = 0; i < 1500 && treeSpots.length < 120 * k; i++) {
      const x = (r() - 0.5) * 360, z = (r() - 0.5) * 300 - 10, h = height(x, z);
      if (!lush(x, z, h) || blocked(x, z, 1.6) || spots.some(p => Math.hypot(p[0] - x, p[1] - z) < 4.5) || treeSpots.some(p => Math.hypot(p[0] - x, p[1] - z) < 5)) continue;
      treeSpots.push([x, z, h]);
    }
    const woodMat = new THREE.MeshStandardMaterial({ ...pbrSet('bark_brown_02', 1), vertexColors: true });
    const treeLeafMat = leafMat('leaves', { strength: 0.1, flutter: 0.01, factor: '(position.y - 1.) / 3.', translucency: 0.5 });
    const trees = [tree(21, { height: 4.2 }), tree(22, { height: 5, spread: 1.3, leafHue: -0.03 }), tree(23, { height: 3.4, spread: 0.8, leafHue: 0.02 })];
    trees.forEach((t, vi) => {
      const mine = treeSpots.filter((_, i) => i % 3 === vi), mats = mine.map(([x, z, h]) => M(x, h - 0.1, z, r() * 6.3, 0.8 + r() * 0.6));
      const tints = mine.map(() => new THREE.Color().setHSL(0, 0, 0.8 + r() * 0.4));
      add(inst(t.wood, woodMat, mats, { shadow: true }), inst(t.leaves, treeLeafMat, mats, { shadow: true, colors: tints }));
      mine.forEach(([x, z]) => colliders.push({ x0: x - 0.4, x1: x + 0.4, z0: z - 0.4, z1: z + 0.4 }));
    });

    // ---- bushes ----------------------------------------------------------------------------
    const bushM = [], bushC = [];
    for (let i = 0; i < 4000 && bushM.length < 500 * k; i++) {
      const x = (r() - 0.5) * 380, z = (r() - 0.5) * 320 - 10, h = height(x, z), dry = smooth(8, 20, h) * 0.5;
      if (h < WATER_Y + 0.5 || h > 11 || pathDist(x, z) < 2 || fieldPlot(x, z) >= 0 || blocked(x, z, 0.8) || Math.hypot(x, z) < 18) continue;
      bushM.push(M(x, h - 0.05, z, r() * 6.3, 0.7 + r() * 0.9, 0.6 + r() * 0.6));
      bushC.push(new THREE.Color().setHSL(THREE.MathUtils.lerp(0.25, 0.1, dry), THREE.MathUtils.lerp(0.4, 0.25, dry), 0.55 + r() * 0.2));
    }
    add(inst(bush(31), leafMat('bush', { strength: 0.05, flutter: 0.006, factor: 'position.y * 2.', translucency: 0.35 }), bushM, { colors: bushC, shadow: true }));

    // ---- flowering shrubs in the street gardens (bougainvillea pink, oleander coral) -------------
    const fb = gardens.flatMap(([x, z]) => [0, 1].map(() => { const fx = x + (r() - 0.5) * 1.6, fz = z + (r() - 0.5) * 2.2; return M(fx, height(fx, fz) - 0.05, fz, r() * 6.3, 0.8 + r() * 0.5, 0.8 + r() * 0.6); }));
    add(inst(flowerBush(51), leafMat('flowerBush', { strength: 0.05, flutter: 0.008, factor: 'position.y', translucency: 0.45 }), fb.filter((_, i) => i % 3), { shadow: true }));
    add(inst(flowerBush(52, 0.03), leafMat('flowerBush2', { strength: 0.05, flutter: 0.008, factor: 'position.y', translucency: 0.45 }), fb.filter((_, i) => !(i % 3)), { shadow: true }));

    // ---- rocks: along banks, mountain feet, desert and ruins ------------------------------------
    const rockM = [], rockC = [];
    for (let i = 0; i < 6000 && rockM.length < 450; i++) {
      const x = (r() - 0.5) * 480, z = (r() - 0.5) * 480, h = height(x, z), wd = waterDist(x, z);
      const wild = z > 125 || Math.max(Math.abs(x), Math.abs(z)) > 180, bank = wd > 0 && wd < 1.6;
      if (!(wild || (bank && r() < 0.5)) || h < WATER_Y - 0.4 || pathDist(x, z) < 2.3 || blocked(x, z, 0.6) || fieldPlot(x, z) >= 0) continue;
      const s = bank ? 0.15 + r() * 0.35 : 0.3 + r() ** 3 * 3.5;
      rockM.push(M(x, h + s * 0.12, z, r() * 6.3, s, s * (0.55 + r() * 0.4), (r() - 0.5) * 0.4));
      rockC.push(new THREE.Color().setHSL(0.08, 0.12 + r() * 0.1, 0.55 + r() * 0.15));
    }
    const rockMat = triplanarMaterial(pbrSet('aerial_rocks_02', 1), { scale: 1.6, key: 'rock', roughness: 1 });
    add(inst(lump(5), rockMat, rockM, { colors: rockC, shadow: true }));

    // ---- fallen leaves and dates under trees; wild flowers near homes and the oasis ------------------
    const litter = [], litterC = [];
    for (const [x, z, h] of [...spots, ...treeSpots]) for (let j = 0; j < 14; j++) {
      const a = r() * 6.3, d = 0.4 + r() * 2.2, lx = x + Math.cos(a) * d, lz = z + Math.sin(a) * d;
      litter.push(M(lx, height(lx, lz) + 0.02, lz, r() * 6.3, 0.09 + r() * 0.06, 1, Math.PI / 2 - 0.1));
      litterC.push(new THREE.Color().setHSL(0.07 + r() * 0.06, 0.5, 0.3 + r() * 0.2));
    }
    add(inst(new THREE.CircleGeometry(1, 5), new THREE.MeshStandardMaterial({ roughness: 0.9, side: THREE.DoubleSide }), litter, { colors: litterC }));
    const fl = [], flC = [], hues = [0.95, 0.13, 0.02, 0.75, 0.58];
    for (let i = 0; i < 14000 && fl.length < 2500; i++) {
      const [ox, oz] = r() < 0.5 ? [0, 0] : [OASIS.x, OASIS.z], a = r() * 6.3, d = 14 + r() * 50;
      const x = ox + Math.cos(a) * d, z = oz + Math.sin(a) * d, h = height(x, z);
      if (!lush(x, z, h) || blocked(x, z, 0.3) || fbm(x * 0.07, z * 0.07) < 0.1) continue;
      fl.push(M(x, h + 0.3 + r() * 0.15, z, r() * 6.3, 0.04 + r() * 0.03));
      flC.push(new THREE.Color().setHSL(hues[(r() * hues.length) | 0], 0.7, r() < 0.3 ? 0.88 : 0.6));
    }
    add(inst(new THREE.IcosahedronGeometry(1, 0), new THREE.MeshStandardMaterial({ roughness: 0.6 }), fl, { colors: flC, layer: LAYER_NO_REFLECT }));
    return g;
  }, [detail]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => () => group.traverse(o => {   // free GPU buffers when Settings rebuilds
    if (!o.isMesh) return; o.dispose?.(); if (o.userData.shared) return; o.geometry.dispose(); o.material.dispose();
  }), [group]);

  let acc = 0;
  useFrame((_, dt) => {
    if ((acc += dt) < 0.25) return; acc = 0;
    palms.current?.update(camera.position);
    const d2 = preset.grassDist ** 2;
    for (const m of chunks.current) m.visible = m.userData.center.distanceToSquared(_p.set(camera.position.x, 0, camera.position.z)) < d2;
  });

  return <primitive object={group} />;
}
