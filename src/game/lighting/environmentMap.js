// Golden-hour sun direction (azimuth from Poly Haven sun.json, elevation clamped >= 16 deg),
// warm-graded equirectangular PMREM IBL (1k Lite–Med, 2k High–Ultra, warm ground bounce),
// Lite/Low CustomToneMapping warm grade, and 3-layer horizon ring (`backdrop_hills.glb`).
import * as THREE from 'three';
import { gltfLoader } from '../world/loaders.js';

// Module-level CustomToneMapping for Lite/Low (no post-processing): runs before any material
// compiles, wrapping Three's NeutralToneMapping with a gentle golden highlight lift, subtle
// cool-teal shadow harmony, and +5% saturation in one zero-pass renderer curve.
const CUSTOM_TM_DEFAULT = 'vec3 CustomToneMapping( vec3 color ) { return color; }';
if (THREE.ShaderChunk.tonemapping_pars_fragment.includes(CUSTOM_TM_DEFAULT)) {
  THREE.ShaderChunk.tonemapping_pars_fragment = THREE.ShaderChunk.tonemapping_pars_fragment.replace(
    CUSTOM_TM_DEFAULT,
    /* glsl */`vec3 CustomToneMapping( vec3 color ) {
	vec3 c = NeutralToneMapping( color );
	float l = dot( c, vec3( 0.2126, 0.7152, 0.0722 ) );
	c *= mix( vec3( 1.0 ), vec3( 1.035, 1.008, 0.955 ), smoothstep( 0.06, 0.55, l ) );
	float lo = ( 1.0 - smoothstep( 0.0, 0.08, l ) ) * smoothstep( 0.0, 0.015, l );
	c += vec3( -0.002, 0.002, 0.005 ) * lo;
	float l2 = dot( c, vec3( 0.2126, 0.7152, 0.0722 ) );
	return saturate( mix( vec3( l2 ), c, 1.05 ) );
}`
  );
}

// ~16 deg elevation (sin 16° = 0.2756), preserving the classic NE azimuth (~36°) for long golden alley shadows
export const SUN_DIR = new THREE.Vector3(0.7764, 0.2756, 0.5668).normalize();
export const MIN_SUN_ELEV_DEG = 16;

export const FALLBACK_SUN = {
  hdri: null,
  sunDirection: [SUN_DIR.x, SUN_DIR.y, SUN_DIR.z],
  sunColor: '#ffd488',
  sunElevationDeg: 16,
  exposure: 1,
  gradient: [
    { elevationDeg: -10, color: '#d1a16b' },
    { elevationDeg: 0,   color: '#f7b96b' },
    { elevationDeg: 5,   color: '#f7c989' },
    { elevationDeg: 10,  color: '#f7d9a8' },
    { elevationDeg: 20,  color: '#b3cbd7' },
    { elevationDeg: 35,  color: '#7da0bd' },
    { elevationDeg: 55,  color: '#5b83ab' },
    { elevationDeg: 75,  color: '#4d7ea8' },
    { elevationDeg: 90,  color: '#4d7ea8' },
  ],
  ground: '#c48952',
};

const WARM_HORIZON = new THREE.Color('#F2B86B');
const COOL_ZENITH = new THREE.Color('#4D7EA8');

function smoothstep(a, b, x) {
  const t = Math.max(0, Math.min(1, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
}

// Shared warm golden-dusk grade (JS for gradient stops, identical GLSL below for equirect skies):
// mix toward #F2B86B by 0.65 at <=5°, 0.35 at 10°, 0.12 at 20°, 0 from 30° up (smooth between),
// and mix toward #4D7EA8 by 0.2 above 45°.
export function warmGrade(color, elevationDeg) {
  const c = color instanceof THREE.Color ? color.clone() : new THREE.Color(color);
  let wWarm = 0.65;
  wWarm = THREE.MathUtils.lerp(wWarm, 0.35, smoothstep(5, 10, elevationDeg));
  wWarm = THREE.MathUtils.lerp(wWarm, 0.12, smoothstep(10, 20, elevationDeg));
  wWarm = THREE.MathUtils.lerp(wWarm, 0.0, smoothstep(20, 30, elevationDeg));
  const wCool = 0.2 * smoothstep(30, 45, elevationDeg);
  return c.lerp(WARM_HORIZON, wWarm).lerp(COOL_ZENITH, wCool);
}

export const WARM_GRADE_GLSL = /* glsl */`
  vec3 warmGrade(vec3 c, float elevDeg) {
    float wWarm = 0.65;
    wWarm = mix(wWarm, 0.35, smoothstep(5.0, 10.0, elevDeg));
    wWarm = mix(wWarm, 0.12, smoothstep(10.0, 20.0, elevDeg));
    wWarm = mix(wWarm, 0.0,  smoothstep(20.0, 30.0, elevDeg));
    float wCool = 0.2 * smoothstep(30.0, 45.0, elevDeg);
    c = mix(c, vec3(${WARM_HORIZON.r.toFixed(5)}, ${WARM_HORIZON.g.toFixed(5)}, ${WARM_HORIZON.b.toFixed(5)}), wWarm);
    c = mix(c, vec3(${COOL_ZENITH.r.toFixed(5)}, ${COOL_ZENITH.g.toFixed(5)}, ${COOL_ZENITH.b.toFixed(5)}), wCool);
    return c;
  }
`;

// Sample the warm-graded gradient from `sun.json` at any elevation in degrees.
export function sampleWarmGradient(sun, elevationDeg) {
  const stops = sun?.gradient?.length ? sun.gradient : FALLBACK_SUN.gradient;
  const col = warmGrade(stops[0].color, stops[0].elevationDeg);
  for (let i = 0; i < stops.length - 1; i++) {
    const t = smoothstep(stops[i].elevationDeg, stops[i + 1].elevationDeg, elevationDeg);
    if (t > 0) col.lerp(warmGrade(stops[i + 1].color, stops[i + 1].elevationDeg), t);
  }
  return col;
}

// Preserve azimuth from sun.json while clamping elevation >= 16° so streets and faces stay readable.
function clampSunDir(sun) {
  const d = sun?.sunDirection;
  if (!Array.isArray(d) || d.length < 3) return SUN_DIR.clone();
  const rawElev = typeof sun.sunElevationDeg === 'number'
    ? sun.sunElevationDeg
    : THREE.MathUtils.radToDeg(Math.asin(THREE.MathUtils.clamp(d[1], -1, 1)));
  const elevRad = THREE.MathUtils.degToRad(Math.max(rawElev, MIN_SUN_ELEV_DEG));
  const hLen = Math.hypot(d[0], d[2]);
  if (hLen < 1e-5) return SUN_DIR.clone();
  const c = Math.cos(elevRad);
  return new THREE.Vector3((d[0] / hLen) * c, Math.sin(elevRad), (d[2] / hLen) * c).normalize();
}

// Cached TextureLoader helper for equirect sky textures (_1k for Lite–Med, _2k for High–Ultra).
const texLoader = new THREE.TextureLoader();
const skyTexCache = new Map();

export function loadSkyTexture(hdri, res = '1k') {
  if (!hdri) return Promise.resolve(null);
  const key = `${hdri}_${res}`;
  if (!skyTexCache.has(key)) {
    const p = texLoader.loadAsync(`./textures/v4/sky/${key}.webp`)
      .then(tex => {
        tex.colorSpace = THREE.SRGBColorSpace;
        tex.wrapS = THREE.RepeatWrapping;
        tex.wrapT = THREE.ClampToEdgeWrapping;
        // Disable mipmaps to avoid the atan() UV-seam mip jump along -X on equirect spheres
        tex.generateMipmaps = false;
        tex.minFilter = THREE.LinearFilter;
        tex.magFilter = THREE.LinearFilter;
        tex.needsUpdate = true;
        return tex;
      })
      .catch(e => {
        console.warn(`[env] sky texture ${key}.webp unavailable:`, e?.message || e);
        skyTexCache.delete(key);
        return null;
      });
    skyTexCache.set(key, p);
  }
  return skyTexCache.get(key);
}

const pmremCache = new WeakMap();

// Bake a PMREM cubemap from a sphere whose upper hemisphere is the warm-graded equirect sky
// (or procedural golden-hour fallback) and whose lower hemisphere is warm ochre ground bounce
// (#C48952 -> golden-tan, never the HDRI's dark blue ground). Disposes any prior target on swap.
export function getSkyPMREM(gl, sunDir = SUN_DIR, map = null) {
  const key = map ? map.uuid : 'procedural';
  const prev = pmremCache.get(gl);
  if (prev && prev.key === key) return prev.rt.texture;
  if (prev) prev.rt.dispose();

  const pmrem = new THREE.PMREMGenerator(gl);
  pmrem.compileEquirectangularShader?.();
  const iblScene = new THREE.Scene();
  const geo = new THREE.SphereGeometry(10, 32, 16);
  const mat = new THREE.ShaderMaterial({
    side: THREE.BackSide,
    depthWrite: false,
    defines: map ? { USE_SKY_MAP: 1 } : {},
    uniforms: {
      uSun: { value: sunDir.clone().normalize() },
      ...(map ? { uMap: { value: map } } : {}),
    },
    vertexShader: /* glsl */`
      varying vec3 vDir;
      void main() { vDir = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: /* glsl */`
      uniform vec3 uSun;
      ${map ? 'uniform sampler2D uMap;' : ''}
      varying vec3 vDir;
      vec3 srgb(vec3 c) { return pow(c, vec3(2.2)); }
      ${WARM_GRADE_GLSL}
      void main() {
        vec3 d = normalize(vDir);
        float y = d.y;
        float s = max(dot(d, uSun), 0.0);
        #ifdef USE_SKY_MAP
          // Clamp sample direction above horizon so the HDRI's dark blue lower hemisphere never leaks
          vec3 upDir = normalize(vec3(d.x, max(y, 0.01), d.z));
          vec2 uv = vec2(atan(upDir.z, upDir.x) * 0.15915494309 + 0.5, asin(clamp(upDir.y, -1.0, 1.0)) * 0.31830988618 + 0.5);
          float elevDeg = degrees(asin(clamp(upDir.y, 0.0, 1.0)));
          vec3 sky = warmGrade(texture2D(uMap, uv).rgb, elevDeg);
          sky += srgb(vec3(1.0, .82, .52)) * (pow(s, 8.0) * 0.32 + pow(s, 36.0) * 0.95);
        #else
          vec3 sky = mix(srgb(vec3(.969, .725, .420)), srgb(vec3(.969, .851, .659)), smoothstep(0.0, 0.14, max(y, 0.0)));
          sky = mix(sky, srgb(vec3(.65, .74, .82)), smoothstep(0.12, 0.38, max(y, 0.0)));
          sky = mix(sky, srgb(vec3(.302, .494, .659)), smoothstep(0.32, 0.85, max(y, 0.0)));
          float anti = pow(max(-dot(d, uSun), 0.0), 1.5);
          sky = mix(sky, srgb(vec3(.76, .58, .63)), anti * (1.0 - smoothstep(0.05, 0.55, max(y, 0.0))) * 0.45);
          sky += srgb(vec3(1.0, .80, .48)) * (pow(s, 5.0) * 0.55 + pow(s, 36.0) * 1.4);
        #endif
        // Lower hemisphere: warm ochre ground bounce (#C48952) fading into golden-tan valley earth
        vec3 gnd = mix(srgb(vec3(.84, .63, .40)), srgb(vec3(.58, .44, .28)), smoothstep(0.0, 0.65, max(-y, 0.0)));
        vec3 col = mix(gnd, sky, smoothstep(-0.08, 0.06, y));
        gl_FragColor = vec4(col, 1.0);
      }`,
  });
  iblScene.add(new THREE.Mesh(geo, mat));
  const rt = pmrem.fromScene(iblScene, 0.04);
  geo.dispose(); mat.dispose(); pmrem.dispose();
  pmremCache.set(gl, { key, rt });
  return rt.texture;
}

let promise;
export function loadEnvironment() {
  promise ??= Promise.all([
    fetch('./textures/v4/sky/sun.json')
      .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .catch(e => { console.warn('[env] sun.json unavailable, using fallback:', e?.message || e); return FALLBACK_SUN; }),
    gltfLoader().loadAsync('./models/env/backdrop_hills.glb')
      .then(gltf => {
        let geo = null;
        gltf.scene.updateMatrixWorld(true);
        gltf.scene.traverse(o => { if (o.isMesh && !geo) geo = o.geometry.clone().applyMatrix4(o.matrixWorld); });
        return geo;
      })
      .catch(e => { console.warn('[env] backdrop_hills.glb unavailable:', e?.message || e); return null; }),
  ]).then(([sun, backdropGeo]) => {
    const safeSun = sun && Array.isArray(sun.gradient) ? sun : FALLBACK_SUN;
    return { sunDir: clampSunDir(safeSun), sun: safeSun, backdropGeo };
  });
  return promise;
}
