// Blender models placed around the world (houses, well, stalls, canal props…).
import { useMemo, useEffect } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { instanceModels } from './instancing.js';
import { useDetail } from '../systems/store.js';

export function Props({ assets, placements, blocker = false, lodDistance = 45 }) {
  const camera = useThree(s => s.camera);
  const { outlines, lite, envDist } = useDetail();
  // LITE: merged per chunk × material (see instancing.js mergeModels) instead of instanced per model
  const inst = useMemo(() => instanceModels(assets, placements, { blocker, lodDistance, outlines, merge: lite ? { chunk: 24, near: 14, mid: 35, far: envDist } : null }), [assets, placements, blocker, lodDistance, outlines, lite, envDist]);
  let t = 0;
  useFrame((_, dt) => { if ((t += dt) > 0.4) { t = 0; inst.update(camera.position); } });
  useMemo(() => inst.update(camera.position, Infinity), [inst]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => () => inst.dispose?.(), [inst]);
  return <primitive object={inst.group} />;
}
