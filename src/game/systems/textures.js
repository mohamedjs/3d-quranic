// Texture loading. Terrain layers are packed into texture arrays (one sampler per map type,
// all layers inside) so six PBR ground materials cost 3 samplers instead of 18.
import * as THREE from 'three';

const BASE = './textures/';
export const TERRAIN_LAYERS = ['aerial_grass_rock', 'dry_ground_01', 'farm_soil', 'brown_mud_02', 'aerial_rocks_02', 'aerial_sand'];

const loadImage = src => new Promise((res, rej) => {
  const img = new Image(); img.decoding = 'async';
  img.onload = () => res(img); img.onerror = () => rej(new Error('Texture failed to load: ' + src)); img.src = src;
});

async function arrayTexture(map, size, srgb, anisotropy) {
  const imgs = await Promise.all(TERRAIN_LAYERS.map(n => loadImage(`${BASE}${n}/${map}.jpg`)));
  const cv = document.createElement('canvas'); cv.width = cv.height = size;
  const ctx = cv.getContext('2d', { willReadFrequently: true });
  const data = new Uint8Array(size * size * 4 * imgs.length);
  imgs.forEach((img, i) => { ctx.drawImage(img, 0, 0, size, size); data.set(ctx.getImageData(0, 0, size, size).data, i * size * size * 4); });
  const t = new THREE.DataArrayTexture(data, size, size, imgs.length);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.minFilter = THREE.LinearMipmapLinearFilter; t.magFilter = THREE.LinearFilter;
  t.generateMipmaps = true; t.anisotropy = anisotropy;
  t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
  t.needsUpdate = true;
  return t;
}

export async function loadTerrainArrays(anisotropy = 8, size = 1024) {
  const [diff, nor, arm] = await Promise.all([
    arrayTexture('diff', size, true, anisotropy), arrayTexture('nor', size, false, anisotropy), arrayTexture('arm', size, false, anisotropy),
  ]);
  return { diff, nor, arm };
}

const loader = new THREE.TextureLoader();
const cache = new Map();
// A PBR set as { map, normalMap, aoMap, roughnessMap } — ARM packs AO (r), roughness (g), metal (b).
export function pbrSet(name, repeat = 1, anisotropy = 8) {
  const key = name + repeat;
  if (!cache.has(key)) {
    const tex = (file, srgb) => {
      const t = loader.load(`${BASE}${name}/${file}.jpg`);
      t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.setScalar(repeat); t.anisotropy = anisotropy;
      t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
      return t;
    };
    const arm = tex('arm', false);
    cache.set(key, { map: tex('diff', true), normalMap: tex('nor', false), aoMap: arm, roughnessMap: arm });
  }
  return cache.get(key);
}

// Tileable normal map for water ripples, generated once from summed sine octaves.
export function waterNormalTexture(size = 256) {
  const data = new Uint8Array(size * size * 4), H = new Float32Array(size * size);
  const waves = Array.from({ length: 24 }, (_, i) => ({ kx: Math.round(Math.cos(i * 2.4) * (2 + i)), ky: Math.round(Math.sin(i * 2.4) * (2 + i)), a: 1 / (1 + i * 0.6), p: i * 1.7 }));
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    let h = 0; for (const w of waves) h += w.a * Math.sin(2 * Math.PI * (w.kx * x + w.ky * y) / size + w.p);
    H[y * size + x] = h;
  }
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    const hx = H[y * size + (x + 1) % size] - H[y * size + (x - 1 + size) % size];
    const hy = H[((y + 1) % size) * size + x] - H[((y - 1 + size) % size) * size + x];
    const n = new THREE.Vector3(-hx * 0.35, -hy * 0.35, 1).normalize(), o = (y * size + x) * 4;
    data[o] = (n.x * 0.5 + 0.5) * 255; data[o + 1] = (n.y * 0.5 + 0.5) * 255; data[o + 2] = (n.z * 0.5 + 0.5) * 255; data[o + 3] = 255;
  }
  const t = new THREE.DataTexture(data, size, size);
  t.wrapS = t.wrapT = THREE.RepeatWrapping; t.generateMipmaps = true; t.minFilter = THREE.LinearMipmapLinearFilter; t.magFilter = THREE.LinearFilter;
  t.needsUpdate = true;
  return t;
}
