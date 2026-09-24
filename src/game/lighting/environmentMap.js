// Loads the HDR sky once: PMREM for image-based lighting, the raw equirect for the water,
// and the sun direction found from the brightest pixel so the directional light, shadows
// and water glints all agree with the sky you see.
import * as THREE from 'three';
import { HDRLoader } from 'three/addons/loaders/HDRLoader.js';

let promise;
export function loadEnvironment(gl) {
  promise ??= new HDRLoader().setDataType(THREE.HalfFloatType).loadAsync('./hdri/sky_2k.hdr').then(tex => {
    tex.mapping = THREE.EquirectangularReflectionMapping;
    const pmrem = new THREE.PMREMGenerator(gl);
    const env = pmrem.fromEquirectangular(tex).texture;
    pmrem.dispose();
    return { equirect: tex, env, sunDir: findSun(tex) };
  });
  return promise;
}

function findSun(tex) {
  const { data, width, height } = tex.image;
  const f = THREE.DataUtils.fromHalfFloat;
  let best = -1, bx = 0, by = 0;
  for (let y = 0; y < height / 2; y++) for (let x = 0; x < width; x++) {   // sky half only
    const i = (y * width + x) * 4, l = f(data[i]) * 0.2126 + f(data[i + 1]) * 0.7152 + f(data[i + 2]) * 0.0722;
    if (l > best) { best = l; bx = x; by = y; }
  }
  // HDR rows are stored top-first; three samples equirect with v = asin(y)/π + .5
  const u = (bx + 0.5) / width, v = 1 - (by + 0.5) / height;
  const lat = (v - 0.5) * Math.PI, lon = (u - 0.5) * 2 * Math.PI;
  const dir = new THREE.Vector3(Math.cos(lon) * Math.cos(lat), Math.sin(lat), Math.sin(lon) * Math.cos(lat)).normalize();
  if (dir.y < 0.06) dir.y = 0.06;   // keep light above the horizon even if the sun sits on it
  return dir.normalize();
}
