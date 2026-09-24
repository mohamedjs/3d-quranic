// Blender models placed around the world (houses, well, stalls, canal props…).
import { useMemo } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { instanceModels } from './instancing.js';
import { materialFor } from './envAssets.js';
import { refs } from '../systems/refs.js';

export function Props({ assets, placements, blocker = false, lodDistance = 45 }) {
  const camera = useThree(s => s.camera);
  const inst = useMemo(() => instanceModels(assets, placements, { blocker, lodDistance }), [assets, placements, blocker, lodDistance]);
  let t = 0;
  const stream = materialFor('stream_water').normalMap;
  useFrame((_, dt) => {
    stream.offset.set(0.02 * refs.clock.water, -0.35 * refs.clock.water);   // water runs down the channel
    if ((t += dt) > 0.4) { t = 0; inst.update(camera.position); }
  });
  useMemo(() => inst.update(camera.position), [inst]); // eslint-disable-line react-hooks/exhaustive-deps
  return <primitive object={inst.group} />;
}
