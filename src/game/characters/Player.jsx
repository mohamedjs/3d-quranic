// <Player/>: the child you play. Procedural rig until models/player.glb exists, then the
// GLB (with idle/walk/run blending). Owns the movement controller and the camera rig.
import { useMemo, useState, useLayoutEffect, useEffect } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { makeChild } from './procedural.js';
import { loadGlbRig } from './glbRig.js';
import { PlayerController } from './PlayerController.js';
import { CameraRig } from '../camera/CameraRig.js';
import { refs } from '../systems/refs.js';
import { LAYER_NO_REFLECT } from '../systems/layers.js';

export function Player({ colliders }) {
  const { scene, camera, gl } = useThree();
  const [rig, setRig] = useState(makeChild);
  const sys = useMemo(() => {
    const ctl = new PlayerController(rig, camera, gl.domElement, colliders, null, scene);
    return { ctl, cam: new CameraRig(camera, ctl), t: 0 };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useLayoutEffect(() => {
    sys.ctl.terrain = scene.getObjectByName('terrain');
    const blockers = []; scene.traverse(o => { if (o.userData.blocker) blockers.push(o); });
    sys.cam.blockers = blockers;
    camera.layers.enable(LAYER_NO_REFLECT);
    refs.player = sys.ctl; refs.cameraRig = sys.cam;
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    loadGlbRig('models/player.glb', 1.25).then(g => {
      if (!g) return;
      g.root.position.copy(sys.ctl.rig.root.position); g.root.rotation.copy(sys.ctl.rig.root.rotation);
      sys.ctl.rig = g; setRig(g);
    }).catch(e => console.error('player.glb:', e));
  }, [sys]);

  useFrame((_, dt) => {
    dt = Math.min(dt, 0.05); sys.t += dt;
    sys.ctl.update(dt, sys.t);
    sys.cam.update(dt);
  });
  return <primitive object={rig.root} />;
}
