// Draws placed models as instanced meshes (one per model × material × LOD) or chunk-merged
// meshes per cell × material (used for ALL static models on Lite, and for dressing props on
// every tier to keep draw calls low). Ink outline hulls are dropped on env models in v3+.
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { toonMaterial } from '../shaders/toon.js';
import { getFoliageAlbedo, registerFoliageMaterial } from './envAssets.js';
import { LAYER_NO_REFLECT } from '../systems/layers.js';

const _q = new THREE.Quaternion(), _e = new THREE.Euler(), _p = new THREE.Vector3(), _s = new THREE.Vector3();

// Small ground-flush props whose tiny shadows cost draw calls in the shadow map without
// contributing visible silhouettes (they sit on ground with baked AO + contact shading).
const NO_SHADOW_MODELS = new Set([
  'jar', 'jar_b', 'basket', 'hoe', 'pot_plant', 'canal_stones', 'canal_bank', 'stream_channel', 'hay',
  'ph_brass_pot_01', 'ph_brass_diya_lantern', 'ph_ceramic_pot', 'ph_wooden_stool_02', 'ph_wicker_basket_01',
  'ph_grass_medium_01', 'ph_flower_gazania', 'rock_small', 'bush_a', 'bush_b',
  'bougainvillea', 'bougainvillea_bush', 'bougainvillea_vine',
]);

// Village street/square/desert props & small dressing skipped from the High/Ultra planar water reflection pass
// (Nile/oasis banks still reflect houses, bridge, arish, palms, sycamores, terrain & sky).
const NO_REFLECT_MODELS = new Set([
  'jar', 'jar_b', 'basket', 'hoe', 'pot_plant', 'canal_stones', 'canal_bank', 'hay',
  'garden_wall', 'mastaba', 'well', 'stall', 'stream_channel',
  'bougainvillea', 'bougainvillea_bush', 'bougainvillea_vine',
  'acacia', 'ruins_wall_a', 'ruins_wall_b', 'ruins_wall_c', 'ruins_column', 'ruins_arch',
  'ph_brass_pot_01', 'ph_brass_diya_lantern', 'ph_ceramic_pot', 'ph_wooden_stool_02', 'ph_wicker_basket_01',
  'ph_grass_medium_01', 'ph_flower_gazania', 'rock_small', 'bush_a', 'bush_b',
]);

function safeMergeGeos(list) {
  if (!list.length) return null;
  if (list.length === 1) return list[0];
  const indexed = list.every(g => g.index);
  const src = indexed ? list : list.map(g => (g.index ? g.toNonIndexed() : g));
  // Align optional attribute keys across parts in the same material bucket
  const common = Object.keys(src[0].attributes).filter(k => src.every(g => g.attributes[k]));
  for (const g of src) {
    for (const k of Object.keys(g.attributes)) {
      if (!common.includes(k)) g.deleteAttribute(k);
    }
  }
  return mergeGeometries(src);
}

export function instanceModels(assets, placements, { shadow = true, blocker = false, lodDistance = 45, outlines = true, merge = null } = {}) {
  if (merge) return mergeModels(assets, placements, { shadow, blocker, ...merge });
  const group = new THREE.Group(), sets = [];
  const byModel = new Map();
  for (const pl of placements) { if (!byModel.has(pl.model)) byModel.set(pl.model, []); byModel.get(pl.model).push(pl); }
  for (const [model, list] of byModel) {
    const a = assets[model]; if (!a) { console.warn('missing model', model); continue; }
    const castModel = shadow && !NO_SHADOW_MODELS.has(model);
    const noRef = NO_REFLECT_MODELS.has(model);
    const matrices = list.map(pl => new THREE.Matrix4().compose(_p.set(pl.x, pl.y, pl.z), _q.setFromEuler(_e.set(pl.tilt ?? 0, pl.rot ?? 0, 0, 'YXZ')), _s.set(pl.sx ?? 1, pl.sy ?? pl.sx ?? 1, pl.sz ?? pl.sx ?? 1)));
    const mk = (parts, isFar = false) => parts?.filter(p => outlines || !p.outline).map(({ geometry, material, outline }) => {
      const m = new THREE.InstancedMesh(geometry, material, list.length);
      matrices.forEach((mx, i) => m.setMatrixAt(i, mx));
      m.computeBoundingSphere();                  // over all instances: stays valid as we re-sort
      // Far LOD1 instances live beyond lodDistance (outside the shadow camera box), so skip shadow pass on them.
      m.castShadow = castModel && !isFar && !outline && !material.userData?.noShadow;
      m.receiveShadow = !outline && !material.userData?.noShadow;
      if (noRef || material.userData?.noReflect) m.layers.set(LAYER_NO_REFLECT);
      m.userData.blocker = blocker && !outline; m.userData.shared = true; // geometry/material belong to the asset cache
      group.add(m); return m;
    });
    // Skip splitting tiny models (< 250 tris, e.g. bougainvillea/canal_bank) into 2 separate LOD draw calls!
    const lod0Tris = (a.lod0 ?? []).reduce((s, p) => s + (p.geometry.index ? p.geometry.index.count : p.geometry.attributes.position.count) / 3, 0);
    const useFar = Boolean(a.lod1) && lod0Tris >= 280;
    sets.push({ list, matrices, near: mk(a.lod0, false), far: useFar ? mk(a.lod1, true) : null });
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

// Chunk-merged static models per cell × material:
// - Used on LITE for all placed models (houses, trees, canal & story props) so a 24 m cell
//   costs only a handful of draw calls.
// - Used on EVERY tier (`dressing: true`) for village/canal/story dressing props so distant
//   story spots cull cleanly to 0 calls & 0 tris and nearby props batch per chunk × material.
const LITE_MAT = {
  s:  () => toonMaterial('vc|s|', { vertexColors: true, side: THREE.FrontSide }),
  d:  () => toonMaterial('vc|d|', { vertexColors: true, side: THREE.DoubleSide }),
  fa: () => registerFoliageMaterial(toonMaterial('lite_fol_cut', { vertexColors: true, map: getFoliageAlbedo(), alphaTest: 0.44, side: THREE.DoubleSide, rim: 0.16, sss: 0.45 })),
  fb: () => registerFoliageMaterial(toonMaterial('lite_fol_bark', { vertexColors: true, map: getFoliageAlbedo(), alphaTest: 0, side: THREE.FrontSide, rim: 0.12 })),
};
const radius = a => (a._r ??= Math.max(0, ...(a.lod0 ?? []).map(p => (p.geometry.boundingSphere ?? (p.geometry.computeBoundingSphere(), p.geometry.boundingSphere)).radius)));
export const liteBlockers = new Set();                  // near-tier walls/trunks the camera must not pass through
function mergeModels(assets, placements, { shadow, blocker, chunk = 32, near = 25, mid = 60, far = 130, lite = true, dressing = false }) {
  const group = new THREE.Group(), supers = new Map(), owned = [], S = chunk * 2;
  for (const pl of placements) {
    const a = assets[pl.model]; if (!a) { console.warn('missing model', pl.model); continue; }
    const sk = `${Math.floor(pl.x / S)},${Math.floor(pl.z / S)}`, ck = `${Math.floor(pl.x / chunk)},${Math.floor(pl.z / chunk)}`;
    if (!supers.has(sk)) { const [x, z] = sk.split(',').map(Number); supers.set(sk, { x0: x * S, z0: z * S, size: S, list: [], subs: new Map(), built: {}, shown: null }); }
    const sup = supers.get(sk);
    if (!sup.subs.has(ck)) { const [x, z] = ck.split(',').map(Number); sup.subs.set(ck, { x0: x * chunk, z0: z * chunk, size: chunk, list: [], built: {}, shown: null }); }
    const sx = pl.sx ?? 1, sy = pl.sy ?? sx, sz = pl.sz ?? sx;
    const item = {
      model: pl.model, a, r: radius(a) * Math.max(sx, sy, sz),
      block: pl.blocker ?? blocker,
      noShadow: NO_SHADOW_MODELS.has(pl.model),
      noReflect: NO_REFLECT_MODELS.has(pl.model),
      m: new THREE.Matrix4().compose(_p.set(pl.x, pl.y, pl.z), _q.setFromEuler(_e.set(pl.tilt ?? 0, pl.rot ?? 0, 0, 'YXZ')), _s.set(sx, sy, sz)),
    };
    sup.list.push(item); sup.subs.get(ck).list.push(item);
  }
  const build = (cell, tier) => {
    const groups = new Map();
    for (const { a, r, block, noShadow, noReflect, m } of cell.list) {
      if (tier === 'mid' && r < (dressing ? 0.65 : 1.15)) continue;     // tiny jars/stools/pots: only up close
      if (tier === 'far' && !a.lod1 && r < (dressing ? 1.8 : 3.0)) continue;
      const parts = (tier === 'near' ? null : a.lod1) ?? a.lod0 ?? [];
      for (const part of parts) {
        if (part.outline) continue;
        const g = part.geometry;
        const isProp = !!part.material.userData?.prop;
        const isBuilding = !!part.material.userData?.building;
        const isFolAtlas = part.material.userData?.atlas === 'foliage';
        const water = !isProp && !g.attributes.color;                   // UV'd stream ribbon keeps its own shader
        const skipSh = noShadow || !!part.material.userData?.noShadow || tier !== 'near';
        const skipRef = !lite && (dressing || noReflect || !!part.material.userData?.noReflect);
        let key, mat, isBlocker = false;
        if (water) {
          key = 'w:' + part.material.uuid;
          mat = part.material;
        } else if (isBuilding) {
          // v4 Poly Haven buildings & palm trunks (`ph_bark`) share one building material & vertex layout
          isBlocker = lite && tier === 'near' && block;
          key = (isBlocker ? 'bb' : 'b') + (skipSh ? ':ns' : '');
          mat = part.material;
        } else if (isProp) {
          // v4 textured Poly Haven props, one-atlas trees, shrubs & boulders keep their embedded maps
          isBlocker = lite && tier === 'near' && block;
          key = `p:${part.material.uuid}:${isBlocker ? 1 : 0}:${skipSh ? 1 : 0}:${skipRef ? 1 : 0}`;
          mat = part.material;
        } else if (isFolAtlas) {
          key = lite ? 'fa' : `fa:${part.material.uuid}:${skipSh ? 1 : 0}:${skipRef ? 1 : 0}`;
          mat = lite ? LITE_MAT.fa() : part.material;
        } else if (lite) {
          const side = part.material.side === THREE.DoubleSide ? 'd' : 's';
          isBlocker = tier === 'near' && block && side === 's';
          key = `${side}:${isBlocker ? 1 : 0}:${skipSh ? 1 : 0}:${skipRef ? 1 : 0}`;
          mat = LITE_MAT[side]();
        } else {
          // Non-Lite dressing props keep their original PBR/toon material, merged per chunk × material
          key = `m:${part.material.uuid}:${skipSh ? 1 : 0}:${skipRef ? 1 : 0}`;
          mat = part.material;
        }
        if (!groups.has(key)) groups.set(key, { list: [], material: mat, block: isBlocker, skipSh, skipRef });
        groups.get(key).list.push(g.clone().applyMatrix4(m));
      }
    }
    const meshes = [];
    for (const { list, material, block, skipSh, skipRef } of groups.values()) {
      const geo = safeMergeGeos(list);
      if (!geo) continue;
      geo.computeBoundingSphere(); owned.push(geo);
      const mesh = new THREE.Mesh(geo, material);
      const noShMat = !!material.userData?.noShadow;
      mesh.castShadow = shadow && !skipSh && !noShMat;
      mesh.receiveShadow = !noShMat;
      if (skipRef) mesh.layers.set(LAYER_NO_REFLECT);
      mesh.matrixAutoUpdate = false;
      mesh.userData.shared = true; mesh.name = `${dressing ? 'prop' : 'lite'}-${tier}`;
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
