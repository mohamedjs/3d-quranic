// Draws placed models as instanced meshes (one per model × material × LOD) and moves each
// instance between the detailed and the simplified mesh by distance from the camera.
// Ink outline hulls are optional (off on LOW) and never cast or receive shadows.
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { toonMaterial } from '../shaders/toon.js';

const _q = new THREE.Quaternion(), _e = new THREE.Euler(), _p = new THREE.Vector3(), _s = new THREE.Vector3();

export function instanceModels(assets, placements, { shadow = true, blocker = false, lodDistance = 45, outlines = true, merge = null } = {}) {
  if (merge) return mergeModels(assets, placements, { shadow, blocker, ...merge });
  const group = new THREE.Group(), sets = [];
  const byModel = new Map();
  for (const pl of placements) { if (!byModel.has(pl.model)) byModel.set(pl.model, []); byModel.get(pl.model).push(pl); }
  for (const [model, list] of byModel) {
    const a = assets[model]; if (!a) { console.warn('missing model', model); continue; }
    const matrices = list.map(pl => new THREE.Matrix4().compose(_p.set(pl.x, pl.y, pl.z), _q.setFromEuler(_e.set(pl.tilt ?? 0, pl.rot ?? 0, 0, 'YXZ')), _s.set(pl.sx ?? 1, pl.sy ?? pl.sx ?? 1, pl.sz ?? pl.sx ?? 1)));
    const mk = parts => parts?.filter(p => outlines || !p.outline).map(({ geometry, material, outline }) => {
      const m = new THREE.InstancedMesh(geometry, material, list.length);
      matrices.forEach((mx, i) => m.setMatrixAt(i, mx));
      m.computeBoundingSphere();                  // over all instances: stays valid as we re-sort
      m.castShadow = shadow && !outline; m.receiveShadow = !outline;
      m.userData.blocker = blocker && !outline; m.userData.shared = true; // geometry/material belong to the asset cache
      group.add(m); return m;
    });
    sets.push({ list, matrices, near: mk(a.lod0), far: mk(a.lod1) });
  }
  const cam = new THREE.Vector3();
  function update(cameraPos) {
    cam.copy(cameraPos);
    const d2 = lodDistance * lodDistance;
    for (const s of sets) {
      if (!s.far) continue;
      let n = 0, f = 0;
      s.list.forEach((pl, i) => {
        const near = (pl.x - cam.x) ** 2 + (pl.z - cam.z) ** 2 < d2;
        for (const m of near ? s.near : s.far) m.setMatrixAt(near ? n : f, s.matrices[i]);
        near ? n++ : f++;
      });
      for (const m of s.near) { m.count = n; m.visible = n > 0; m.instanceMatrix.needsUpdate = true; }   // empty sets cost no draw call
      for (const m of s.far) { m.count = f; m.visible = f > 0; m.instanceMatrix.needsUpdate = true; }
    }
  }
  return { group, update };
}

// LITE: static models baked into merged meshes per chunk × material instead of one instanced
// mesh per model. Three tiers by distance from the camera:
//   near  (< near m, 24 m cells)  the detailed meshes of everything
//   mid   (24 m cells)            LOD1 (or LOD0 when a model has none), tiny props left out
//   far   (from `mid` m)             LOD1 of the big shapes only (houses, palms, trees…); a 48 m
//                                    super-cell wholly beyond `mid` is merged as one
// beyond `far` nothing — the fog has swallowed it. All toon parts share two materials
// (single- / double-sided vertex colour); wind is dropped (a merged frond no longer knows
// where its trunk is) and ink hulls are skipped, so a cell costs 2 draw calls. Merges are
// built lazily (a couple per update, never leaving a hole) and kept.
const LITE_MAT = {
  s: () => toonMaterial('vc|s|', { vertexColors: true, side: THREE.FrontSide }),
  d: () => toonMaterial('vc|d|', { vertexColors: true, side: THREE.DoubleSide }),
};
const radius = a => (a._r ??= Math.max(0, ...(a.lod0 ?? []).map(p => (p.geometry.boundingSphere ?? (p.geometry.computeBoundingSphere(), p.geometry.boundingSphere)).radius)));
export const liteBlockers = new Set();                  // near-tier walls/trunks the camera must not pass through
function mergeModels(assets, placements, { shadow, blocker, chunk = 32, near = 25, mid = 60, far = 130 }) {
  const group = new THREE.Group(), supers = new Map(), owned = [], S = chunk * 2;
  for (const pl of placements) {
    const a = assets[pl.model]; if (!a) { console.warn('missing model', pl.model); continue; }
    const sk = `${Math.floor(pl.x / S)},${Math.floor(pl.z / S)}`, ck = `${Math.floor(pl.x / chunk)},${Math.floor(pl.z / chunk)}`;
    if (!supers.has(sk)) { const [x, z] = sk.split(',').map(Number); supers.set(sk, { x0: x * S, z0: z * S, size: S, list: [], subs: new Map(), built: {}, shown: null }); }
    const sup = supers.get(sk);
    if (!sup.subs.has(ck)) { const [x, z] = ck.split(',').map(Number); sup.subs.set(ck, { x0: x * chunk, z0: z * chunk, size: chunk, list: [], built: {}, shown: null }); }
    const item = { a, r: radius(a), block: pl.blocker ?? blocker, m: new THREE.Matrix4().compose(_p.set(pl.x, pl.y, pl.z), _q.setFromEuler(_e.set(pl.tilt ?? 0, pl.rot ?? 0, 0, 'YXZ')), _s.set(pl.sx ?? 1, pl.sy ?? pl.sx ?? 1, pl.sz ?? pl.sx ?? 1)) };
    sup.list.push(item); sup.subs.get(ck).list.push(item);
  }
  const build = (cell, tier) => {
    const groups = new Map();
    for (const { a, r, block, m } of cell.list) {
      if (tier === 'mid' && r < 1.2) continue;                          // jars, baskets, hoes: only up close
      if (tier === 'far' && !a.lod1 && r < 3) continue;                 // far: the big silhouettes only
      const parts = (tier === 'near' ? null : a.lod1) ?? a.lod0 ?? [];
      for (const part of parts) {
        if (part.outline) continue;
        const g = part.geometry, water = !g.attributes.color;             // UV'd stream ribbon keeps its own shader
        const side = part.material.side === THREE.DoubleSide ? 'd' : 's';
        const key = water ? 'w:' + part.material.uuid : side + (block && side === 's' ? 'b' : '');
        if (!groups.has(key)) groups.set(key, { list: [], material: water ? part.material : LITE_MAT[side](), block: key === 'sb' });
        groups.get(key).list.push(g.clone().applyMatrix4(m));
      }
    }
    const meshes = [];
    for (const { list, material, block } of groups.values()) {
      const indexed = list.every(g => g.index);
      const geo = list.length > 1 ? mergeGeometries(indexed ? list : list.map(g => (g.index ? g.toNonIndexed() : g))) : list[0];
      if (!geo) continue;
      geo.computeBoundingSphere(); owned.push(geo);
      const mesh = new THREE.Mesh(geo, material);
      mesh.castShadow = shadow; mesh.receiveShadow = true; mesh.matrixAutoUpdate = false;
      mesh.userData.shared = true; mesh.name = `lite-${tier}`;              // freed by dispose()
      if (block && tier === 'near') liteBlockers.add(mesh);
      mesh.visible = false; group.add(mesh); meshes.push(mesh);
    }
    return meshes;
  };
  const cam = new THREE.Vector3();
  const dist = c => Math.hypot(Math.max(c.x0 - cam.x, 0, cam.x - c.x0 - c.size), Math.max(c.z0 - cam.z, 0, cam.z - c.z0 - c.size));
  let budget = 0;
  const show = (cell, want) => {
    if (want && !cell.built[want]) {
      if (budget > 0 || !cell.shown) { budget--; cell.built[want] = build(cell, want); }   // never leave a hole
      else return;                                                        // not built yet: keep what is shown a moment
    }
    if (want === cell.shown) return;
    for (const m of cell.built[cell.shown] ?? []) m.visible = false;
    for (const m of cell.built[want] ?? []) m.visible = true;
    cell.shown = want;
  };
  function update(cameraPos, b = 2) {
    cam.copy(cameraPos); budget = b;
    for (const sup of supers.values()) {
      const d = dist(sup);
      if (d >= mid) { for (const c of sup.subs.values()) show(c, null); show(sup, d < far ? 'far' : null); continue; }
      show(sup, null);
      for (const c of sup.subs.values()) { const dc = dist(c); show(c, dc < near ? 'near' : dc < mid ? 'mid' : dc < far ? 'far' : null); }
    }
  }
  const dispose = () => { owned.forEach(g => g.dispose()); group.traverse(o => liteBlockers.delete(o)); };
  return { group, update, dispose, merged: true };
}
