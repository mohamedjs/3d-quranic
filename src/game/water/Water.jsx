// The world water plane: one opaque toon pass (see shaders/waterMaterial.js). The bank
// texture is baked once from the heightfield; streak/foam time runs on the water clock.
import { useMemo } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { createWaterMaterial, bindWater, waterTime } from '../shaders/waterMaterial.js';
import { buildWaterBank } from './waterBank.js';
import { SIZE, WATER_Y } from '../terrain/heightfield.js';

export function Water({ clock }) {
  const material = useMemo(() => bindWater(createWaterMaterial({ size: SIZE }), buildWaterBank()), []);
  const geometry = useMemo(() => new THREE.PlaneGeometry(SIZE, SIZE, 1, 1).rotateX(-Math.PI / 2), []);
  useFrame(() => { waterTime.value = clock.water; });
  return <mesh name="water" geometry={geometry} material={material} position-y={WATER_Y} renderOrder={2} />;
}
