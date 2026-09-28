// <Environment/>: the painted toon sky, warm distance haze matched to its horizon, and the
// living atmosphere (dust, gnats, birds).
import { useEffect, useMemo } from 'react';
import * as THREE from 'three';
import { useThree, useFrame } from '@react-three/fiber';
import { Atmosphere } from './Atmosphere.jsx';
import { createSky } from './Sky.js';
import { refs } from '../systems/refs.js';
import { usePreset } from '../systems/store.js';

export function Environment({ env }) {
  const scene = useThree(s => s.scene);
  const preset = usePreset(), lite = !!preset.lite;
  const sky = useMemo(() => createSky(env.sunDir, lite), [env, lite]);
  const [fogNear, fogFar] = preset.fog ?? [90, 620];      // LITE: a closer haze hides its short draw distance
  useEffect(() => {
    scene.environment = null; scene.background = new THREE.Color('#f3d3a6');
    scene.fog = new THREE.Fog('#efd2a8', 90, 620);
  }, [scene, env]);
  // the haze starts further out as the camera climbs, so the bird's-eye view stays crisp
  useFrame(() => {
    sky.material.uniforms.uTime.value = refs.clock.wind;
    const f = scene.fog; if (f) { const d = refs.view.dist; f.near = fogNear + d * 1.2; f.far = fogFar + d * 3; }
  });
  return (
    <>
      <primitive object={sky} />
      <Atmosphere />
    </>
  );
}
