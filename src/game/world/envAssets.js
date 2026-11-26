// Blender-made environment models (public/models/env/*.glb) & tiered WebP painterly atlases.
// - Lite / Low (`texRes: 512`, `shading: 'toon'`): loads ONLY the 512px core albedo atlas (~74 KB)
//   and uses painterly toon + baked vertex AO + backlit sunlight rim.
// - Medium / High / Ultra (`texRes: 1024|2048`, `shading: 'pbr'`): lazy-loads 1024/2048px albedo +
//   normal WebP atlases on demand (excluded from core PWA precache) and uses Stylized PBR + backlit SSS.
import * as THREE from 'three';
import { gltfLoader } from './loaders.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { toonFor, toonMaterial, windFor, WIND } from '../shaders/toon.js';
import { envMaterial } from '../shaders/stylizedPbr.js';
import { BUILDING_LAYER_INDEX, getBuildingMaterial, ensureBuildingTextures } from '../shaders/buildingMaterial.js';
import { TOON } from '../shaders/toonPalette.js';
import { toonStreamWaterMaterial } from '../shaders/waterMaterial.js';
import { PRESETS } from '../systems/quality.js';
import { useGame } from '../systems/store.js';

export const ENV_MODELS = [
  'house_a', 'house_b', 'house_c', 'house_d', 'house_e', 'house_f', 'mastaba',
  'oasis_arish', 'ruins_wall_a', 'ruins_wall_b', 'ruins_wall_c', 'ruins_column', 'ruins_arch',
  'palm_a', 'palm_b', 'palm_c', 'palm_d',
  'sycamore', 'sycamore_a', 'sycamore_b', 'acacia',
  'bougainvillea', 'bougainvillea_bush', 'bougainvillea_vine',
  'bush_a', 'bush_b', 'lotus_pad',
  'well', 'shaduf', 'sluice', 'jar', 'jar_b', 'basket', 'hoe', 'fence',
  'river_bridge', 'footbridge', 'stall', 'hay', 'stream_channel', 'garden_wall',
  'pot_plant', 'canal_bank', 'canal_stones', 'field_bund',
  'crop_berseem', 'crop_maize', 'crop_wheat', 'crop_cotton', 'crop_cabbage',
  'grass_a', 'grass_b', 'grass_c', 'reeds', 'papyrus', 'wildflowers',
];

// ---- Shared Tiered WebP Foliage Atlas (512 core -> lazy 1024/2048 PBR) ---------------------
const texLoader = new THREE.TextureLoader();
const atlasMaterials = new Set();
let foliageAlbedo = null;
let foliageNormal = null;
let loadedFoliageRes = 0;

function configureTex(tex, isColor, aniso = 1) {
  tex.flipY = false;   // glTF UV origin matches top-left image layout without V flip
  tex.wrapS = THREE.ClampToEdgeWrapping;
  tex.wrapT = THREE.ClampToEdgeWrapping;
  tex.colorSpace = isColor ? THREE.SRGBColorSpace : THREE.NoColorSpace;
  tex.anisotropy = aniso;
  tex.generateMipmaps = true;
  tex.minFilter = THREE.LinearMipmapLinearFilter;
  tex.magFilter = THREE.LinearFilter;
  tex.needsUpdate = true;
  return tex;
}

export function getFoliageAlbedo() {
  if (!foliageAlbedo) {
    loadedFoliageRes = 512;
    foliageAlbedo = configureTex(texLoader.load('./textures/env/512/foliage_albedo.webp'), true, 1);
  }
  return foliageAlbedo;
}

export function registerFoliageMaterial(mat) {
  if (!mat) return mat;
  atlasMaterials.add(mat);
  if (foliageAlbedo && mat.map !== foliageAlbedo) {
    mat.map = foliageAlbedo;
    mat.needsUpdate = true;
  }
  if (foliageNormal && mat.isMeshStandardMaterial && mat.normalMap !== foliageNormal) {
    mat.normalMap = foliageNormal;
    mat.needsUpdate = true;
  }
  return mat;
}

// Lazy-load 1024px (Medium) or 2048px (High/Ultra) foliage albedo + normal maps on demand.
// Lite/Low never touch 1024/2048 folders so mobile bandwidth & PWA core stay lean.
export function upgradeFoliageAtlas(texRes = 512, maxAniso = 1) {
  getFoliageAlbedo();
  if (texRes < 1024 || texRes <= loadedFoliageRes) {
    if (foliageAlbedo && maxAniso > foliageAlbedo.anisotropy) {
      foliageAlbedo.anisotropy = maxAniso;
      foliageAlbedo.needsUpdate = true;
    }
    return;
  }
  loadedFoliageRes = texRes;
  const dir = `./textures/env/${texRes}`;
  texLoader.load(`${dir}/foliage_albedo.webp`, tex => {
    configureTex(tex, true, maxAniso);
    const old = foliageAlbedo;
    foliageAlbedo = tex;
    for (const m of atlasMaterials) { m.map = tex; m.needsUpdate = true; }
    if (old && old !== tex) old.dispose();
  });
  texLoader.load(`${dir}/foliage_normal.webp`, tex => {
    configureTex(tex, false, maxAniso);
    const old = foliageNormal;
    foliageNormal = tex;
    for (const m of atlasMaterials) {
      if (m.isMeshStandardMaterial) { m.normalMap = tex; m.needsUpdate = true; }
    }
    if (old && old !== tex) old.dispose();
  });
}

// ---- GLB Loader & Material Router ----------------------------------------------------------
let promise;
export function loadEnvModels() {
  promise ??= (async () => {
    // Ensure the core 512px foliage atlas is ready before first render; upgrade lazily on Med–Ultra
    const detailPreset = PRESETS[useGame.getState().detail] ?? PRESETS.lite;
    const initRes = detailPreset.texRes ?? 512;
    const initShading = detailPreset.shading ?? 'toon';
    getFoliageAlbedo();
    if (initRes >= 1024) upgradeFoliageAtlas(initRes, detailPreset.waterMode === 'ultra' ? 8 : 4);
    ensureBuildingTextures(initShading);

    const loader = gltfLoader();
    const out = {};
    await Promise.all(ENV_MODELS.map(async name => {
      const gltf = await loader.loadAsync(`./models/env/${name}.glb`).catch(e => { throw new Error(`models/env/${name}.glb: ${e.message || e}`); });
      out[name] = extract(gltf.scene, name, initShading);
    }));
    return out;
  })();
  return promise;
}

const baseName = n => n.replace(/\.\d+$/, '');
const windKey = w => Object.entries(WIND).find(([, v]) => v === w)?.[0] ?? 'w';

function cropWindFor(model) {
  if (/wheat/.test(model)) return WIND.wheat;
  if (/maize/.test(model)) return WIND.maize;
  if (/reed|papyrus/.test(model)) return WIND.reed;
  if (/grass/.test(model)) return WIND.grass;
  if (/wildflower|bush|bougainvillea|lotus/.test(model)) return WIND.shrub;
  return WIND.crop;
}

function foliageSpec(matName, model) {
  if (matName === 'foliage_frond')     return { atlas: true,  alphaTest: 0.44, side: THREE.DoubleSide, wind: WIND.frond,        sss: 0.62, rim: 0.18, rootBlend: 0 };
  if (matName === 'foliage_leaf')      return { atlas: true,  alphaTest: 0.44, side: THREE.DoubleSide, wind: WIND.leaf,         sss: 0.54, rim: 0.16, rootBlend: 0 };
  if (matName === 'foliage_shrub')     return { atlas: true,  alphaTest: 0.44, side: THREE.DoubleSide, wind: /lotus/.test(model) ? null : WIND.shrub, sss: 0.48, rim: 0.14, rootBlend: 0 };
  if (matName === 'foliage_crop_card') return { atlas: true,  alphaTest: 0.44, side: THREE.DoubleSide, wind: cropWindFor(model), sss: 0.52, rim: 0.14, rootBlend: 0 };
  if (matName === 'foliage_bark')      return { atlas: true,  alphaTest: 0,    side: THREE.FrontSide,  wind: null,              sss: 0,    rim: 0.12, rootBlend: 0 };
  if (matName === 'foliage_grass')     return { atlas: false, alphaTest: 0,    side: THREE.DoubleSide, wind: WIND.grass,        sss: 0.50, rim: 0.12, rootBlend: 1 };
  if (matName === 'foliage_crop_vc')   return { atlas: false, alphaTest: 0,    side: THREE.DoubleSide, wind: cropWindFor(model), sss: 0.46, rim: 0.12, rootBlend: 0 };
  if (matName === 'foliage_solid')     return { atlas: false, alphaTest: 0,    side: THREE.FrontSide,  wind: null,              sss: 0,    rim: 0.14, rootBlend: 0 };
  return null;
}

// Flatten a GLB into { lod0: [{geometry, material, outline}], lod1: [...] } with node transforms
// baked. Parts sharing a material bucket are merged so each tree/house costs minimal draw calls.
function extract(root, model, shading = 'toon') {
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
    const add = (key, geo, material, outline = false) => {
      if (!groups.has(key)) groups.set(key, { list: [], material, outline });
      groups.get(key).list.push(geo);
    };
    for (const { geometry, matName } of parts) {
      // Environment ink hulls are dropped in v3 (§R.1); cel-shaded characters keep their outlines.
      if (matName === 'outline') continue;
      if (matName === 'toon_water' && geometry.attributes.uv) {
        geometry.computeBoundingSphere();
        out.push({ geometry, material: materialFor(matName, geometry), outline: false });
        continue;
      }
      const bLayer = BUILDING_LAYER_INDEX[matName];
      if (bLayer !== undefined) {
        add('ph_building', stripBuilding(geometry, bLayer), getBuildingMaterial(shading));
        continue;
      }
      const fspec = foliageSpec(matName, model);
      if (fspec) {
        const wk = fspec.wind ? windKey(fspec.wind) : '';
        const key = `f3|${shading}|${fspec.atlas ? 'a' : 'v'}|${fspec.alphaTest ? 'c' : 'o'}|${fspec.side === THREE.DoubleSide ? 'd' : 's'}|${wk}|${fspec.rootBlend}`;
        const mat = envMaterial(key, {
          shading,
          vertexColors: true,
          map: fspec.atlas ? getFoliageAlbedo() : null,
          normalMap: fspec.atlas && shading === 'pbr' ? foliageNormal : null,
          alphaTest: fspec.alphaTest,
          side: fspec.side,
          wind: fspec.wind,
          rim: fspec.rim,
          sss: fspec.sss,
          rootBlend: fspec.rootBlend,
          roughness: fspec.atlas && !fspec.alphaTest ? 0.92 : 0.80,
          envMapIntensity: fspec.sss > 0 ? 0.42 : 0.34,
        });
        if (fspec.atlas) {
          mat.userData.atlas = 'foliage';
          registerFoliageMaterial(mat);
        }
        add(key, strip(geometry, undefined, fspec.atlas), mat);
      } else {
        const [color, flags] = TOON[matName] ?? [0x888888, ''];
        const side = flags.includes('d') ? THREE.DoubleSide : THREE.FrontSide, wind = windFor(matName), wk = wind ? windKey(wind) : '';
        const key = `vc|${side === THREE.DoubleSide ? 'd' : 's'}|${wk}`;
        add(key, strip(geometry, color, false), toonMaterial(key, { vertexColors: true, side, wind }));
      }
    }
    for (const { list, material, outline } of groups.values()) {
      const indexed = list.every(g => g.index);
      const geometry = list.length > 1 ? mergeGeometries(indexed ? list : list.map(g => (g.index ? g.toNonIndexed() : g))) : list[0];
      geometry.computeBoundingSphere();
      out.push({ geometry, material, outline });
    }
    lods[lod] = out;
  }
  return lods;
}

export function materialFor(name, geometry) {
  name = baseName(name);
  if (name === 'toon_water' && geometry?.attributes.uv) return toonStreamWaterMaterial();
  return toonFor(name);
}

// Keep position, normal, optional UV (for atlas meshes), and baked v3 vertex colors + AO
// (or fill flat TOON hex for legacy v2 GLBs).
const C = new THREE.Color();
function strip(g, color, keepUv = false) {
  const out = new THREE.BufferGeometry();
  out.setAttribute('position', g.attributes.position);
  out.setAttribute('normal', g.attributes.normal);
  const n = g.attributes.position.count;
  if (keepUv) {
    if (g.attributes.uv) out.setAttribute('uv', g.attributes.uv);
    else out.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(n * 2), 2));
  }
  if (g.index) out.setIndex(g.index);
  const srcCol = g.attributes.color;
  if (srcCol) {
    const a = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) { C.fromBufferAttribute(srcCol, i); a[i * 3] = C.r; a[i * 3 + 1] = C.g; a[i * 3 + 2] = C.b; }
    out.setAttribute('color', new THREE.BufferAttribute(a, 3));
  } else if (color !== undefined) {
    C.setHex(color); const a = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) { a[i * 3] = C.r; a[i * 3 + 1] = C.g; a[i * 3 + 2] = C.b; }
    out.setAttribute('color', new THREE.BufferAttribute(a, 3));
  } else {
    const a = new Float32Array(n * 3).fill(1);
    out.setAttribute('color', new THREE.BufferAttribute(a, 3));
  }
  return out;
}

// v4 building path: keep position, normal, metric UV, linear vertex colour, and write per-vertex aLayer
// so all ph_* material parts of a LOD merge into one geometry and one draw call.
function stripBuilding(g, layerIdx) {
  const out = strip(g, undefined, true);
  const n = out.attributes.position.count;
  const aLayer = new Float32Array(n);
  aLayer.fill(layerIdx);
  out.setAttribute('aLayer', new THREE.BufferAttribute(aLayer, 1));
  return out;
}

const merged = new Map();
export function mergedPlant(assets, model) {
  if (!merged.has(model)) {
    const parts = assets[model].lod0;
    const body = parts.filter(p => !p.outline && p.geometry.attributes.color);
    const hull = parts.find(p => p.outline);
    const indexed = body.every(p => p.geometry.index);
    const geometry = body.length > 1
      ? mergeGeometries(body.map(p => (indexed ? p.geometry : (p.geometry.index ? p.geometry.toNonIndexed() : p.geometry))))
      : body[0].geometry;
    geometry.computeBoundingSphere();
    merged.set(model, { body: geometry, outline: hull?.geometry ?? null, material: body[0]?.material ?? null });
  }
  return merged.get(model);
}
