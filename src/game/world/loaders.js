// Shared asset loaders: single Draco + Meshopt GLTF loader and cached WebGL2 DataArrayTexture loader.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';

let loader;
export function gltfLoader() {
  if (!loader) {
    const draco = new DRACOLoader().setDecoderPath('./draco/');
    draco.preload();                                   // start fetching the decoder with the first model
    loader = new GLTFLoader().setDRACOLoader(draco).setMeshoptDecoder(MeshoptDecoder);
  }
  return loader;
}

const SRGB_TO_LIN = new Float32Array(256);
for (let i = 0; i < 256; i++) {
  const s = i / 255;
  SRGB_TO_LIN[i] = s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
}

async function decodeImage(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
  const blob = await res.blob();
  if (typeof createImageBitmap === 'function') {
    try { return await createImageBitmap(blob); } catch { /* fallback to Image */ }
  }
  return new Promise((resolve, reject) => {
    const objUrl = URL.createObjectURL(blob);
    const img = new Image();
    img.onload = () => { URL.revokeObjectURL(objUrl); resolve(img); };
    img.onerror = () => { URL.revokeObjectURL(objUrl); reject(new Error(`Decode failed: ${url}`)); };
    img.src = objUrl;
  });
}

const texArrayCache = new Map();

// Decodes a list of URLs into one packed WebGL2 THREE.DataArrayTexture (repeat wrap, mipmaps,
// anisotropy 4 on Medium+) plus each layer's average linear RGB colour. Evicts on dispose so a
// later tier switch can cleanly recreate GPU storage.
export function loadTextureArray(urls, { srgb = false, size = 512, anisotropy } = {}) {
  const aniso = anisotropy ?? (size >= 1024 ? 4 : 1);
  const key = `${size}|${srgb ? 1 : 0}|${aniso}|${urls.join(',')}`;
  if (texArrayCache.has(key)) return texArrayCache.get(key);

  const p = Promise.all(urls.map(decodeImage)).then(imgs => {
    const depth = imgs.length;
    const stride = size * size * 4;
    const data = new Uint8Array(stride * depth);
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = size;
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    const averages = [];
    const step = size > 1024 ? 2 : 1;

    for (let i = 0; i < depth; i++) {
      const img = imgs[i];
      ctx.drawImage(img, 0, 0, size, size);
      img.close?.();
      const px = ctx.getImageData(0, 0, size, size).data;
      data.set(px, i * stride);

      let sr = 0, sg = 0, sb = 0, n = 0;
      for (let y = 0; y < size; y += step) {
        const row = y * size * 4;
        for (let x = 0; x < size; x += step) {
          const o = row + x * 4;
          if (srgb) {
            sr += SRGB_TO_LIN[px[o]];
            sg += SRGB_TO_LIN[px[o + 1]];
            sb += SRGB_TO_LIN[px[o + 2]];
          } else {
            sr += px[o] / 255;
            sg += px[o + 1] / 255;
            sb += px[o + 2] / 255;
          }
          n++;
        }
      }
      averages.push(new THREE.Vector3(
        Math.max(0.005, sr / n),
        Math.max(0.005, sg / n),
        Math.max(0.005, sb / n),
      ));
    }

    const texture = new THREE.DataArrayTexture(data, size, size, depth);
    texture.format = THREE.RGBAFormat;
    texture.type = THREE.UnsignedByteType;
    texture.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
    texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
    texture.magFilter = THREE.LinearFilter;
    texture.minFilter = THREE.LinearMipmapLinearFilter;
    texture.generateMipmaps = true;
    texture.anisotropy = aniso;
    texture.needsUpdate = true;
    texture.addEventListener('dispose', () => {
      if (texArrayCache.get(key) === p) texArrayCache.delete(key);
    });
    return { texture, averages };
  }).catch(err => {
    if (texArrayCache.get(key) === p) texArrayCache.delete(key);
    throw err;
  });

  texArrayCache.set(key, p);
  return p;
}

const texLoader = new THREE.TextureLoader();
const waterNorCache = new Map();

// Cached seamlessly tileable water normal map loader (512 Lite/Low, 1024 Medium+).
// Evicts on dispose so a later tier switch can cleanly recreate GPU storage.
export function loadWaterNormal(size = 512, { anisotropy } = {}) {
  const aniso = anisotropy ?? (size >= 1024 ? 4 : 1);
  const key = `${size}|${aniso}`;
  if (waterNorCache.has(key)) return waterNorCache.get(key);
  const p = texLoader.loadAsync(`./textures/v4/${size}/water_nor.webp`).then(tex => {
    tex.colorSpace = THREE.NoColorSpace;
    tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
    tex.magFilter = THREE.LinearFilter;
    tex.minFilter = THREE.LinearMipmapLinearFilter;
    tex.generateMipmaps = true;
    tex.anisotropy = aniso;
    tex.needsUpdate = true;
    tex.addEventListener('dispose', () => {
      if (waterNorCache.get(key) === p) waterNorCache.delete(key);
    });
    return tex;
  }).catch(err => {
    if (waterNorCache.get(key) === p) waterNorCache.delete(key);
    throw err;
  });
  waterNorCache.set(key, p);
  return p;
}
