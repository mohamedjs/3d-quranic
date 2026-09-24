// Blender-made environment models (public/models/env/*.glb, built by blender/*.py).
// Geometry comes from the GLB; materials are chosen here by material *name*, so the game's
// PBR textures, triplanar projection and wind shaders apply — nothing is baked into files.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { triplanarMaterial } from '../shaders/triplanar.js';
import { windy } from '../shaders/wind.js';
import { pbrSet, waterNormalTexture } from '../systems/textures.js';

export const ENV_MODELS = ['house_a', 'house_b', 'house_c', 'palm_a', 'palm_b', 'palm_c', 'well', 'shaduf', 'sluice',
  'jar', 'jar_b', 'basket', 'hoe', 'fence', 'footbridge', 'stall', 'hay', 'stream', 'garden_wall', 'pot_plant'];

let promise;
export function loadEnvModels() {
  promise ??= (async () => {
    const loader = new GLTFLoader().setDRACOLoader(new DRACOLoader().setDecoderPath('./draco/'));
    const out = {};
    await Promise.all(ENV_MODELS.map(async name => {
      const gltf = await loader.loadAsync(`./models/env/${name}.glb`).catch(e => { throw new Error(`models/env/${name}.glb: ${e.message || e}`); });
      out[name] = extract(gltf.scene);
    }));
    return out;
  })();
  return promise;
}

// Flatten a GLB into { lod0: [{geometry, material}], lod1: [...] } with node transforms baked.
function extract(root) {
  root.updateMatrixWorld(true);
  const lods = { lod0: [], lod1: [] };
  const isLow = o => { for (let p = o; p; p = p.parent) if (/_LOD1/.test(p.name)) return true; return false; };
  root.traverse(o => {
    if (!o.isMesh) return;
    const geometry = o.geometry.clone().applyMatrix4(o.matrixWorld);
    geometry.computeBoundingSphere();
    (isLow(o) ? lods.lod1 : lods.lod0).push({ geometry, material: materialFor(o.material.name) });
  });
  if (!lods.lod1.length) lods.lod1 = null;
  return lods;
}

const cache = new Map();
export function materialFor(name) {
  const key = name.replace(/\.\d+$/, '');
  if (!cache.has(key)) cache.set(key, make(key));
  return cache.get(key);
}
function make(name) {
  const tri = (set, scale, color, extra = {}) => triplanarMaterial(pbrSet(set), { scale, key: name, color, vertexColors: false, ...extra });
  const plain = (color, roughness = 0.85, extra = {}) => new THREE.MeshStandardMaterial({ color, roughness, ...extra });
  switch (name) {
    case 'plaster': return tri('clay_plaster', 2.2, 0xc9a07a);
    case 'plaster_light': return tri('clay_plaster', 2.2, 0xdcbf98);
    case 'lime': return tri('clay_plaster', 1.6, 0xf2ead8);
    case 'wood': return tri('old_planks_02', 1.1, 0xc8a078, { normalScale: 1.2 });
    case 'wood_dark': return tri('old_planks_02', 1.1, 0x7a5a42, { normalScale: 1.2 });
    case 'clay': return tri('clay_plaster', 0.7, 0xc06a40, { roughness: 0.75 });
    case 'stone': return tri('large_sandstone_blocks', 2.4, 0xd8c4a0);
    case 'bark': return new THREE.MeshStandardMaterial({ ...pbrSet('palm_bark', 1), color: 0xc8b8a0 });
    case 'frond': return windy(new THREE.MeshStandardMaterial({ color: 0x5f7a34, roughness: 0.7, side: THREE.DoubleSide }), 'glbFrond',
      { strength: 0.2, flutter: 0.006, factor: 'length(position.xz) / 3.5', translucency: 0.55 });
    case 'frond_dry': return windy(new THREE.MeshStandardMaterial({ color: 0x9a7a48, roughness: 0.9, side: THREE.DoubleSide }), 'glbFrondDry',
      { strength: 0.08, factor: 'length(position.xz) / 3.5' });
    case 'dates': return plain(0x9a3f10, 0.45);
    case 'straw': return tri('cotton_jersey', 0.25, 0xd8b060, { roughness: 1 });
    case 'rope': return plain(0xa89060, 1);
    case 'iron': return plain(0x4a4a4e, 0.45, { metalness: 0.85 });
    case 'produce': return plain(0xd87a20, 0.5);
    case 'fabric_red': return tri('cotton_jersey', 0.35, 0xb04a30, { roughness: 1 });
    case 'stream_water': {   // shallow running water in the street channel; ripples scrolled by <Props/>
      const n = waterNormalTexture(); n.repeat.set(2, 6);
      return new THREE.MeshPhysicalMaterial({ color: 0x1f3d38, roughness: 0.06, transparent: true, opacity: 0.86, normalMap: n, normalScale: new THREE.Vector2(0.35, 0.35), envMapIntensity: 1.3, depthWrite: false });
    }
    case 'mud': return tri('brown_mud_02', 0.8, 0x7a6048, { roughness: 0.6 });
    case 'leaf': return windy(new THREE.MeshStandardMaterial({ color: 0x3f6a26, roughness: 0.7, side: THREE.DoubleSide }), 'glbLeaf', { strength: 0.04, factor: 'position.y', translucency: 0.5 });
    case 'water_dark': return new THREE.MeshPhysicalMaterial({ color: 0x0c1a1a, roughness: 0.05, clearcoat: 1 });
    default: return plain(0x888888);
  }
}
