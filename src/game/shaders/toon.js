// The toon look, shared by everything in the world: cel-shaded MeshToonMaterial with a
// 3-step gradient (core shadow / thin half-tone / lit), a soft rim light, fog and sun
// shadows, cached by name. Shadow colour comes from the (lavender-warm) hemisphere light,
// so shaded sides and cast shadows share one tint. Outlines are inverted hulls authored in
// Blender (`<mesh>_outline`, material `outline`), drawn unlit in ink.
import * as THREE from 'three';
import { TOON, INK } from './toonPalette.js';
import { injectWind } from './wind.js';
import { AERIAL, injectAerialFog } from './stylizedPbr.js';

let gradient;
export function toonGradient() {
  if (!gradient) {
    // Softly feathered 3-band painterly ramp over dot(N, L) in [-1, 1]: clean shade band,
    // warm mid-tone step, and smooth-yet-crisp transition into golden sunlight.
    const steps = [0, 0, 0, 0, 0, 0, 0.04, 0.36, 0.46, 0.50, 0.64, 0.96, 1, 1, 1, 1];
    gradient = new THREE.DataTexture(new Uint8Array(steps.flatMap(v => [Math.round(v * 255), Math.round(v * 255), Math.round(v * 255), 255])), steps.length, 1);
    gradient.minFilter = gradient.magFilter = THREE.LinearFilter; gradient.generateMipmaps = false; gradient.needsUpdate = true;
  }
  return gradient;
}

export const RIM = { value: new THREE.Color('#ffd58e') };

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
  if (/shrub/.test(name)) return WIND.shrub;
  if (/grass/.test(name)) return WIND.grass;
  if (/wheat/.test(name)) return WIND.wheat;
  if (/maize/.test(name)) return WIND.maize;
  if (/berseem|cabbage|cotton|crop/.test(name)) return WIND.crop;
  if (/reed|papyrus/.test(name)) return WIND.reed;
  return null;
}

const cache = new Map();
// opts: color, map, side, vertexColors, wind (preset object), rim (strength), alphaTest, sss, rootBlend
export function toonMaterial(key, {
  color = 0xffffff, map = null, side = THREE.FrontSide, vertexColors = false,
  wind = null, rim = 0.22, alphaTest = 0, sss = 0, sssColor = 0xb8d954, rootBlend = 0,
} = {}) {
  if (cache.has(key)) return cache.get(key);
  const m = new THREE.MeshToonMaterial({ color, map, side, vertexColors, alphaTest, gradientMap: toonGradient() });
  m.name = key;
  const w = wind ? `${wind.strength}|${wind.factor}|${wind.flutter ?? 0}` : '';
  m.customProgramCacheKey = () => `toon_v3|${w}|${rim.toFixed(2)}|${sss.toFixed(2)}|${rootBlend.toFixed(1)}|${alphaTest > 0 ? 1 : 0}`;
  m.onBeforeCompile = sh => {
    if (wind) injectWind(sh, wind);
    injectAerialFog(sh);
    if (sss > 0) sh.uniforms.uSssColor = { value: new THREE.Color(sssColor) };
    if (rootBlend > 0) {
      sh.uniforms.uRootColor = AERIAL.uRootColor;
      sh.vertexShader = sh.vertexShader
        .replace('#include <common>', '#include <common>\nvarying float vRootY;')
        .replace('#include <begin_vertex>', '#include <begin_vertex>\nvRootY = position.y;');
    }
    if (rim || sss > 0 || rootBlend > 0) {
      sh.uniforms.uRimColor = RIM;
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <common>', `#include <common>
          uniform vec3 uRimColor;${sss > 0 ? '\nuniform vec3 uSssColor;' : ''}${rootBlend > 0 ? '\nuniform vec3 uRootColor;\nvarying float vRootY;' : ''}`)
        .replace('#include <color_fragment>', `#include <color_fragment>
          ${rootBlend > 0 ? `{ float rb = 1.0 - smoothstep(0.0, 0.18, vRootY); diffuseColor.rgb = mix(diffuseColor.rgb, uRootColor * 0.92, rb * ${(0.55 * rootBlend).toFixed(3)}); }` : ''}`)
        .replace('#include <lights_fragment_end>', `#include <lights_fragment_end>
          { ${rim ? `float rimF = 1. - clamp(abs(dot(normalize(vViewPosition), normal)), 0., 1.);
            reflectedLight.directDiffuse += diffuseColor.rgb * uRimColor * smoothstep(.62, .86, rimF) * ${rim.toFixed(3)};` : ''}
            ${sss > 0 ? `vec3 wDir = normalize(vAerialPos - cameraPosition);
            float back = pow(clamp(dot(wDir, uAerialSunDir), 0.0, 1.0), 2.5);
            reflectedLight.directDiffuse += diffuseColor.rgb * uSssColor * (back * 0.55 + 0.10) * ${sss.toFixed(3)};` : ''} }`);
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

// Ink outline for an inverted hull. Character hulls are exported with flipped normals (→ FrontSide).
// Unlit, aerial-fogged, no shadows.
export function outlineMaterial(kind = 'env', wind = null) {
  const key = `outline_v3|${kind}|${wind ? wind.strength + wind.factor : ''}`;
  if (cache.has(key)) return cache.get(key);
  const m = new THREE.MeshBasicMaterial({ color: INK, side: kind === 'char' ? THREE.FrontSide : THREE.BackSide });
  m.name = 'outline';
  m.customProgramCacheKey = () => key;
  m.onBeforeCompile = sh => {
    if (wind) injectWind(sh, wind);
    injectAerialFog(sh);
  };
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
