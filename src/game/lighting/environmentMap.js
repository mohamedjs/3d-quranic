// Golden-hour sun direction (~16 deg elevation, keeping the title composition's azimuth),
// procedural sky-baked PMREM IBL (zero HDRI download, cached per renderer), and the
// 3-layer horizon ring (`backdrop_hills.glb`) loaded in the Suspense chain so frame 1 is complete.
import * as THREE from 'three';
import { gltfLoader } from '../world/loaders.js';

// ~16 deg elevation (sin 16° = 0.2756), preserving the classic NE azimuth (~53.9°) for long golden alley shadows
export const SUN_DIR = new THREE.Vector3(0.7764, 0.2756, 0.5668).normalize();

const pmremCache = new WeakMap();

// Bake a smooth golden-hour sky + warm ochre ground bounce sphere into a PMREM cubemap
// for Stylized PBR materials (Medium–Ultra). Zero network cost; ~5 ms once on first PBR mount.
export function getSkyPMREM(gl, sunDir = SUN_DIR) {
  if (pmremCache.has(gl)) return pmremCache.get(gl);
  const pmrem = new THREE.PMREMGenerator(gl);
  pmrem.compileEquirectangularShader?.();
  const iblScene = new THREE.Scene();
  const geo = new THREE.SphereGeometry(10, 24, 16);
  const mat = new THREE.ShaderMaterial({
    side: THREE.BackSide, depthWrite: false,
    uniforms: { uSun: { value: sunDir.clone().normalize() } },
    vertexShader: /* glsl */`
      varying vec3 vDir;
      void main() { vDir = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: /* glsl */`
      uniform vec3 uSun; varying vec3 vDir;
      vec3 srgb(vec3 c) { return pow(c, vec3(2.2)); }
      void main() {
        vec3 d = normalize(vDir);
        float y = d.y;
        // Upper hemisphere: apricot horizon -> cream -> cerulean zenith + dusty rose opposite sun
        vec3 sky = mix(srgb(vec3(.969, .725, .420)), srgb(vec3(.969, .851, .659)), smoothstep(0.0, 0.14, max(y, 0.0)));
        sky = mix(sky, srgb(vec3(.65, .74, .82)), smoothstep(0.12, 0.38, max(y, 0.0)));
        sky = mix(sky, srgb(vec3(.302, .494, .659)), smoothstep(0.32, 0.85, max(y, 0.0)));
        float anti = pow(max(-dot(d, uSun), 0.0), 1.5);
        sky = mix(sky, srgb(vec3(.76, .58, .63)), anti * (1.0 - smoothstep(0.05, 0.55, max(y, 0.0))) * 0.45);
        float s = max(dot(d, uSun), 0.0);
        sky += srgb(vec3(1.0, .80, .48)) * (pow(s, 5.0) * 0.55 + pow(s, 36.0) * 1.4);
        // Lower hemisphere: warm ochre ground bounce (#C48952) fading into golden-tan valley earth
        vec3 gnd = mix(srgb(vec3(.84, .63, .40)), srgb(vec3(.58, .44, .28)), smoothstep(0.0, 0.65, max(-y, 0.0)));
        vec3 col = mix(gnd, sky, smoothstep(-0.10, 0.08, y));
        gl_FragColor = vec4(col, 1.0);
      }`,
  });
  iblScene.add(new THREE.Mesh(geo, mat));
  const rt = pmrem.fromScene(iblScene, 0.04);
  geo.dispose(); mat.dispose(); pmrem.dispose();
  pmremCache.set(gl, rt.texture);
  return rt.texture;
}

let promise;
export function loadEnvironment() {
  promise ??= gltfLoader().loadAsync('./models/env/backdrop_hills.glb')
    .then(gltf => {
      let geo = null;
      gltf.scene.updateMatrixWorld(true);
      gltf.scene.traverse(o => { if (o.isMesh && !geo) geo = o.geometry.clone().applyMatrix4(o.matrixWorld); });
      return { sunDir: SUN_DIR.clone(), backdropGeo: geo };
    })
    .catch(e => {
      console.warn('[env] backdrop_hills.glb unavailable:', e?.message || e);
      return { sunDir: SUN_DIR.clone(), backdropGeo: null };
    });
  return promise;
}
