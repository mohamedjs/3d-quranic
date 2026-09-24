import { use, useMemo, useEffect } from 'react';
import { useThree } from '@react-three/fiber';
import { createTerrainMaterial } from '../shaders/terrainMaterial.js';
import { loadTerrainArrays } from '../systems/textures.js';
import { usePreset } from '../systems/store.js';

let arraysPromise;
export function Terrain({ data, onReady }) {
  const gl = useThree(s => s.gl);
  arraysPromise ??= loadTerrainArrays(Math.min(8, gl.capabilities.getMaxAnisotropy()));
  const arrays = use(arraysPromise);
  const { antiTile } = usePreset();
  const material = useMemo(() => createTerrainMaterial(arrays, antiTile), [arrays, antiTile]);
  useEffect(() => { onReady?.(); }, [onReady]);
  return <mesh name="terrain" geometry={data.geometry} material={material} receiveShadow />;
}
