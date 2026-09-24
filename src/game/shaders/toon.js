// The toon look, shared by everything in the world: cel-shaded MeshToonMaterial with a
// 3-step gradient (core shadow / thin half-tone / lit), a soft rim light, fog and sun
// shadows, cached by name. Shadow colour comes from the (lavender-warm) hemisphere light,
// so shaded sides and cast shadows share one tint. Outlines are inverted hulls authored in
// Blender (`<mesh>_outline`, material `outline`), drawn unlit in ink.
import * as THREE from 'three';
import { TOON, INK } from './toonPalette.js';
import { injectWind } from './wind.js';

let gradient;
export function toonGradient() {
  if (!gradient) {
    // 8 texels over dot(N, L) in [-1, 1]: facing away → 0 (ambient only), 0–0.25 → half-tone, above → full sun
    const steps = [0, 0, 0, 0, 0.45, 1, 1, 1];
    gradient = new THREE.DataTexture(new Uint8Array(steps.flatMap(v => [v * 255, v * 255, v * 255, 255])), steps.length, 1);
    gradient.minFilter = gradient.magFilter = THREE.NearestFilter; gradient.generateMipmaps = false; gradient.needsUpdate = true;
  }
  return gradient;
}

export const RIM = { value: new THREE.Color('#ffe2b0') };

// Wind presets per plant family (GLSL factor is 0 at the root, ~1 at the tips)
export const WIND = {
  frond: { strength: 0.2, factor: 'length(position.xz) / 3.5' },
  leaf: { strength: 0.05, factor: 'position.y / 3.' },
  shrub: { strength: 0.06, factor: 'position.y / 1.2' },
  grass: { strength: 0.13, factor: 'position.y / .35' },
  wheat: { strength: 0.1, factor: 'position.y' },
  maize: { strength: 0.08, factor: 'position.y / 1.6' },
  crop: { strength: 0.05, factor: 'position.y * 3.' },
  reed: { strength: 0.14, factor: 'position.y / 1.6' },
};
export function windFor(name) {
  if (/frond/.test(name)) return WIND.frond;
  if (/leaf|flower_(pink|magenta)/.test(name)) return WIND.leaf;
  if (/grass/.test(name)) return WIND.grass;
  if (/wheat/.test(name)) return WIND.wheat;
  if (/maize/.test(name)) return WIND.maize;
  if (/berseem|cabbage|cotton/.test(name)) return WIND.crop;
  if (/reed/.test(name)) return WIND.reed;
  return null;
}

const cache = new Map();
// opts: color, map, side, vertexColors, wind (preset object), rim (strength), alphaTest
export function toonMaterial(key, { color = 0xffffff, map = null, side = THREE.FrontSide, vertexColors = false, wind = null, rim = 0.22, alphaTest = 0 } = {}) {
  if (cache.has(key)) return cache.get(key);
  const m = new THREE.MeshToonMaterial({ color, map, side, vertexColors, alphaTest, gradientMap: toonGradient() });
  m.name = key;
  const w = wind ? `${wind.strength}|${wind.factor}|${wind.flutter ?? 0}` : '';
  m.customProgramCacheKey = () => `toon|${w}|${rim}`;
  m.onBeforeCompile = sh => {
    if (wind) injectWind(sh, wind);
    if (rim) {
      sh.uniforms.uRimColor = RIM;
      sh.fragmentShader = 'uniform vec3 uRimColor;\n' + sh.fragmentShader.replace('#include <lights_fragment_end>', `#include <lights_fragment_end>
        { float rimF = 1. - clamp(dot(normalize(vViewPosition), normal), 0., 1.);
          reflectedLight.directDiffuse += diffuseColor.rgb * uRimColor * smoothstep(.62, .8, rimF) * ${rim.toFixed(3)}; }`);
    }
  };
  cache.set(key, m);
  return m;
}

// A material from the art contract by name (toon_plaster, toon_frond…): palette colour,
// double-sided for `d`, wind by plant family.
export function toonFor(name, fallback = 0x888888) {
  const [color, flags] = TOON[name] ?? [fallback, ''];
  return toonMaterial(name, { color, side: flags.includes('d') ? THREE.DoubleSide : THREE.FrontSide, wind: windFor(name) });
}

// Ink outline for an inverted hull. Environment hulls keep outward winding (→ BackSide);
// character hulls are exported with flipped normals (→ FrontSide). Unlit, fogged, no shadows.
export function outlineMaterial(kind = 'env', wind = null) {
  const key = `outline|${kind}|${wind ? wind.strength + wind.factor : ''}`;
  if (cache.has(key)) return cache.get(key);
  const m = new THREE.MeshBasicMaterial({ color: INK, side: kind === 'char' ? THREE.FrontSide : THREE.BackSide });
  m.name = 'outline';
  if (wind) { m.customProgramCacheKey = () => key; m.onBeforeCompile = sh => injectWind(sh, wind); }
  cache.set(key, m);
  return m;
}

// Swap every lit material under `root` for its toon equivalent (procedural rigs, birds…).
export function toonify(root, prefix = 'proc') {
  root.traverse(o => {
    if (!o.isMesh || !o.material || o.material.isMeshToonMaterial || o.material.isMeshBasicMaterial) return;
    const m = o.material;
    o.material = toonMaterial(`${prefix}_${m.color?.getHexString() ?? 'fff'}_${m.side}`, { color: m.color?.getHex() ?? 0xffffff, side: m.side, vertexColors: m.vertexColors });
  });
  return root;
}
