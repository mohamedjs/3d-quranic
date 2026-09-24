// Golden-hour toon lighting: a warm sun (the cel materials step it into lit / half-tone /
// shade) and a light lavender-warm hemisphere that *is* the shadow colour, so shaded sides
// and cast shadows read as one soft tint instead of going dark. The shadow frustum follows
// the player and is snapped to shadow-map texels (no shimmering edges while walking).
import { useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { usePreset } from '../systems/store.js';
import { refs } from '../systems/refs.js';

export const SUN_COLOR = new THREE.Color('#ffe0b0');

export function Lighting({ env }) {
  const preset = usePreset();
  const sun = useRef();
  const basis = useMemo(() => {
    const f = env.sunDir.clone().negate(), right = new THREE.Vector3().crossVectors(f, new THREE.Vector3(0, 1, 0)).normalize();
    return { right, up: new THREE.Vector3().crossVectors(right, f).normalize() };
  }, [env]);

  useFrame(() => {
    const l = sun.current, p = refs.player?.pos; if (!l || !p) return;
    const r = preset.shadowRange, texel = (2 * r) / preset.shadowMap;
    const a = Math.round(p.dot(basis.right) / texel) * texel - p.dot(basis.right);
    const b = Math.round(p.dot(basis.up) / texel) * texel - p.dot(basis.up);
    const c = new THREE.Vector3().copy(p).addScaledVector(basis.right, a).addScaledVector(basis.up, b);
    l.target.position.copy(c); l.position.copy(c).addScaledVector(env.sunDir, 150);
    l.target.updateMatrixWorld();
  });

  const r = preset.shadowRange;
  return (
    <>
      <directionalLight key={preset.shadowMap + '-' + r} ref={sun} color={SUN_COLOR} intensity={1.75} castShadow
        shadow-mapSize={[preset.shadowMap, preset.shadowMap]} shadow-bias={-0.0004} shadow-normalBias={0.04} shadow-radius={2}
        shadow-camera-left={-r} shadow-camera-right={r} shadow-camera-top={r} shadow-camera-bottom={-r}
        shadow-camera-near={1} shadow-camera-far={320} />
      <hemisphereLight args={['#cbbcd4', '#bfa58c', Math.PI * 1.0]} />
    </>
  );
}
