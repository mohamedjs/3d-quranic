// Blender models placed around the world (houses, well, stalls, canal props…).
import { useMemo } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { instanceModels } from './instancing.js';
import { useDetail } from '../systems/store.js';

export function Props({ assets, placements, blocker = false, lodDistance = 45 }) {
  const camera = useThree(s => s.camera);
  const outlines = useDetail().outlines;
  const inst = useMemo(() => instanceModels(assets, placements, { blocker, lodDistance, outlines }), [assets, placements, blocker, lodDistance, outlines]);
  let t = 0;
  useFrame((_, dt) => { if ((t += dt) > 0.4) { t = 0; inst.update(camera.position); } });
  useMemo(() => inst.update(camera.position), [inst]); // eslint-disable-line react-hooks/exhaustive-deps
  return <primitive object={inst.group} />;
}
