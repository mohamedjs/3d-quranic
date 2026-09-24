// Blender-made environment models (public/models/env/*.glb, built by blender/v2/env/*.py).
// Geometry comes from the GLB; materials are chosen here by material *name* from the toon
// art contract (toon_* → cel material with palette colour, `outline` → ink hull), so the
// whole world shares one small set of shaders.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { toonFor, toonMaterial, outlineMaterial, windFor, WIND } from '../shaders/toon.js';
import { TOON } from '../shaders/toonPalette.js';
import { toonStreamWaterMaterial } from '../shaders/waterMaterial.js';

export const ENV_MODELS = ['house_a', 'house_b', 'house_c', 'mastaba', 'palm_a', 'palm_b', 'palm_c', 'sycamore', 'bougainvillea',
  'well', 'shaduf', 'sluice', 'jar', 'jar_b', 'basket', 'hoe', 'fence', 'footbridge', 'stall', 'hay', 'stream', 'garden_wall',
  'pot_plant', 'canal_bank', 'canal_stones', 'field_bund',
  'crop_berseem', 'crop_maize', 'crop_wheat', 'crop_cotton', 'crop_cabbage', 'grass_a', 'grass_b', 'grass_c', 'reeds', 'wildflowers'];

// ink hulls that must sway with the foliage they surround
const OUTLINE_WIND = { palm: WIND.frond, sycamore: WIND.leaf };

let promise;
export function loadEnvModels() {
  promise ??= (async () => {
    const loader = new GLTFLoader().setDRACOLoader(new DRACOLoader().setDecoderPath('./draco/'));
    const out = {};
    await Promise.all(ENV_MODELS.map(async name => {
      const gltf = await loader.loadAsync(`./models/env/${name}.glb`).catch(e => { throw new Error(`models/env/${name}.glb: ${e.message || e}`); });
      out[name] = extract(gltf.scene, name);
    }));
    return out;
  })();
  return promise;
}

const baseName = n => n.replace(/\.\d+$/, '');
// Flatten a GLB into { lod0: [{geometry, material, outline}], lod1: [...] } with node transforms
// baked. Toon parts are merged per (side, wind) with their palette colour as a vertex colour,
// so a house with 16 toon_* materials costs ~2 draw calls (+1 for its ink hull), not 16.
function extract(root, model) {
  root.updateMatrixWorld(true);
  const raw = { lod0: [], lod1: [] };
  const isLow = o => { for (let p = o; p; p = p.parent) if (/_LOD1/.test(p.name)) return true; return false; };
  root.traverse(o => {
    if (!o.isMesh) return;
    const geometry = o.geometry.clone().applyMatrix4(o.matrixWorld);
    (isLow(o) ? raw.lod1 : raw.lod0).push({ geometry, matName: baseName(o.material.name) });
  });
  const lods = {};
  for (const [lod, parts] of Object.entries(raw)) {
    if (!parts.length) { lods[lod] = null; continue; }
    const groups = new Map(), out = [];
    const add = (key, geo, material, outline = false) => { if (!groups.has(key)) groups.set(key, { list: [], material, outline }); groups.get(key).list.push(geo); };
    for (const { geometry, matName } of parts) {
      if (matName === 'outline') add('outline', strip(geometry), outlineMaterial('env', OUTLINE_WIND[model.split('_')[0]]), true);
      else if (matName === 'toon_water' && geometry.attributes.uv) { geometry.computeBoundingSphere(); out.push({ geometry, material: materialFor(matName, geometry), outline: false }); }
      else {
        const [color, flags] = TOON[matName] ?? [0x888888, ''];
        const side = flags.includes('d') ? THREE.DoubleSide : THREE.FrontSide, wind = windFor(matName), wk = wind ? windKey(wind) : '';
        const key = `vc|${side === THREE.DoubleSide ? 'd' : 's'}|${wk}`;
        add(key, strip(geometry, color), toonMaterial(key, { vertexColors: true, side, wind }));
      }
    }
    for (const { list, material, outline } of groups.values()) {
      const geometry = list.length > 1 ? mergeGeometries(list) : list[0];
      geometry.computeBoundingSphere();
      out.push({ geometry, material, outline });
    }
    lods[lod] = out;
  }
  return lods;
}
const windKey = w => Object.entries(WIND).find(([, v]) => v === w)?.[0] ?? 'w';

export function materialFor(name, geometry) {
  name = baseName(name);
  if (name === 'toon_water' && geometry?.attributes.uv) return toonStreamWaterMaterial();   // UV'd ribbon: u across, v metres along
  return toonFor(name);
}

// Keep only what the toon shaders read (position, normal, + palette colour as vertex colour).
const C = new THREE.Color();
function strip(g, color) {
  const out = new THREE.BufferGeometry();
  out.setAttribute('position', g.attributes.position); out.setAttribute('normal', g.attributes.normal);
  if (g.index) out.setIndex(g.index);
  if (color !== undefined) {
    C.setHex(color); const n = g.attributes.position.count, a = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) a.set([C.r, C.g, C.b], i * 3);
    out.setAttribute('color', new THREE.BufferAttribute(a, 3));
  }
  return out;
}
const merged = new Map();
export function mergedPlant(assets, model) {
  if (!merged.has(model)) {
    const parts = assets[model].lod0, body = parts.filter(p => !p.outline && p.geometry.attributes.color), hull = parts.find(p => p.outline);
    const geometry = body.length > 1 ? mergeGeometries(body.map(p => p.geometry)) : body[0].geometry;
    geometry.computeBoundingSphere();
    merged.set(model, { body: geometry, outline: hull?.geometry ?? null });
  }
  return merged.get(model);
}
