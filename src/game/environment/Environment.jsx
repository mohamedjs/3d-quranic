// <Environment/>: HDR sky as background and image-based light, warm distance haze, and
// the living atmosphere (dust, gnats, birds) plus the sun disc for light shafts.
import { useEffect } from 'react';
import * as THREE from 'three';
import { useThree } from '@react-three/fiber';
import { Atmosphere, SunDisc } from './Atmosphere.jsx';
import { usePreset } from '../systems/store.js';

export function Environment({ env, onSun }) {
  const scene = useThree(s => s.scene);
  const godrays = usePreset().godrays;
  useEffect(() => {
    scene.environment = env.env; scene.background = env.equirect;
    scene.environmentIntensity = 0.8; scene.backgroundIntensity = 1;
    scene.fog = new THREE.Fog('#d8b48e', 110, 700);
  }, [scene, env]);
  return (
    <>
      <Atmosphere />
      <SunDisc ref={onSun} dir={env.sunDir} visible={godrays} />
    </>
  );
}
