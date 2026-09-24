import { useMemo, useEffect } from 'react';
import { createTerrainMaterial } from '../shaders/terrainMaterial.js';

export function Terrain({ data, onReady }) {
  const material = useMemo(() => createTerrainMaterial(), []);
  useEffect(() => { onReady?.(); }, [onReady]);
  return <mesh name="terrain" geometry={data.geometry} material={material} receiveShadow />;
}
