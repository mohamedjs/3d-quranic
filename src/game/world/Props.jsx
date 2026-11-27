// Blender models placed around the world (houses, well, stalls, canal & story-spot props).
import { useMemo, useEffect, useRef } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { instanceModels } from './instancing.js';
import { useDetail } from '../systems/store.js';

export function Props({ assets, placements, blocker = false, lodDistance = 45, mergeDressing = false }) {
  const camera = useThree(s => s.camera);
  const { outlines, lite, envDist, lodDist, propDist } = useDetail();
  const dist = lodDist ?? lodDistance;
  const mergeCfg = lite
    ? { chunk: 24, near: lodDist ?? 14, mid: 36, far: envDist ?? 86, lite: true, dressing: false }
    : mergeDressing
      ? { chunk: 48, near: propDist ?? 42, mid: (propDist ?? 42) + 22, far: (propDist ?? 42) + 44, lite: false, dressing: true }
      : null;
  const inst = useMemo(
    () => instanceModels(assets, placements, { blocker, lodDistance: dist, outlines, merge: mergeCfg }),
    [assets, placements, blocker, dist, outlines, lite, envDist, lodDist, propDist, mergeDressing] // eslint-disable-line react-hooks/exhaustive-deps
  );
  const tRef = useRef(0);
  useFrame((_, dt) => { if ((tRef.current += dt) > 0.35) { tRef.current = 0; inst.update(camera.position); } });
  useMemo(() => inst.update(camera.position, Infinity), [inst]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => () => inst.dispose?.(), [inst]);
  return <primitive object={inst.group} />;
}
