// The toon world has no image-based lighting: the painted sky (environment/Sky.js) is drawn
// procedurally and the cel materials are lit by the sun + a tinted hemisphere only. This
// just provides the golden-hour sun direction (the one the old HDR sky had, ~19° up,
// so the title composition and shadows stay the same). Kept async for the Suspense chain.
import * as THREE from 'three';

const SUN_DIR = new THREE.Vector3(0.7634, 0.3268, 0.5572).normalize();
let promise;
export function loadEnvironment() {
  promise ??= Promise.resolve({ sunDir: SUN_DIR.clone() });
  return promise;
}
