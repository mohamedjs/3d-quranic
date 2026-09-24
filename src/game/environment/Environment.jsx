// <Environment/>: the painted toon sky, warm distance haze matched to its horizon, and the
// living atmosphere (dust, gnats, birds).
import { useEffect, useMemo } from 'react';
import * as THREE from 'three';
import { useThree, useFrame } from '@react-three/fiber';
import { Atmosphere } from './Atmosphere.jsx';
import { createSky } from './Sky.js';
import { refs } from '../systems/refs.js';

export function Environment({ env }) {
  const scene = useThree(s => s.scene);
  const sky = useMemo(() => createSky(env.sunDir), [env]);
  useEffect(() => {
    scene.environment = null; scene.background = new THREE.Color('#f3d3a6');
    scene.fog = new THREE.Fog('#efd2a8', 90, 620);
  }, [scene, env]);
  useFrame(() => { sky.material.uniforms.uTime.value = refs.clock.wind; });
  return (
    <>
      <primitive object={sky} />
      <Atmosphere />
    </>
  );
}
