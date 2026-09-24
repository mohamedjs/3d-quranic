// Water surface + the two extra passes it needs (refraction/depth, planar reflection).
// Passes run at useFrame priority 0, before the EffectComposer renders at priority 1.
import { useMemo, useEffect, useRef } from 'react';
import * as THREE from 'three';
import { useFrame, useThree } from '@react-three/fiber';
import { createWaterMaterial } from '../shaders/waterMaterial.js';
import { waterNormalTexture } from '../systems/textures.js';
import { SIZE, WATER_Y } from '../terrain/heightfield.js';
import { usePreset } from '../systems/store.js';

const up = new THREE.Vector3(0, 1, 0), mirrorPoint = new THREE.Vector3(0, WATER_Y, 0);
const _cam = new THREE.Vector3(), _view = new THREE.Vector3(), _look = new THREE.Vector3(), _target = new THREE.Vector3();
const _rot = new THREE.Matrix4(), _plane = new THREE.Plane(), _clip = new THREE.Vector4(), _q = new THREE.Vector4();

export function Water({ env, sunDir, clock }) {
  const { gl, scene, camera, size } = useThree();
  const preset = usePreset();
  const mesh = useRef();
  const material = useMemo(() => createWaterMaterial({ normalTex: waterNormalTexture(), envTex: env.equirect, sunDir }), [env, sunDir]);
  const geometry = useMemo(() => new THREE.PlaneGeometry(SIZE, SIZE, 1, 1).rotateX(-Math.PI / 2), []);
  const mirrorCam = useMemo(() => { const c = new THREE.PerspectiveCamera(); c.layers.set(0); return c; }, []);

  const targets = useMemo(() => {
    const dpr = gl.getPixelRatio(), w = Math.max(2, Math.floor(size.width * dpr)), h = Math.max(2, Math.floor(size.height * dpr));
    const mk = (scale, depth) => {
      if (!scale) return null;
      const rt = new THREE.WebGLRenderTarget(Math.floor(w * scale), Math.floor(h * scale), { type: THREE.HalfFloatType });
      if (depth) { rt.depthTexture = new THREE.DepthTexture(rt.width, rt.height); rt.depthTexture.type = THREE.UnsignedIntType; }
      return rt;
    };
    return { reflect: mk(preset.reflectRes), refract: mk(preset.refractRes, true) };
  }, [gl, size, preset.reflectRes, preset.refractRes]);
  useEffect(() => () => { targets.reflect?.dispose(); targets.refract?.dispose(); }, [targets]);

  useFrame(() => {
    const u = material.uniforms, m = mesh.current; if (!m) return;
    u.uTime.value = clock.water;
    u.uNear.value = camera.near; u.uFar.value = camera.far;
    u.uRes.value.set(gl.domElement.width, gl.domElement.height);
    u.uEnvI.value = scene.environmentIntensity ?? 1;
    u.uHasRefract.value = targets.refract ? 1 : 0;
    u.uHasReflect.value = targets.reflect ? 1 : 0;
    m.visible = false;
    const prevTarget = gl.getRenderTarget(), shadows = gl.shadowMap.autoUpdate;
    gl.shadowMap.autoUpdate = false;   // reuse last frame's shadow maps for the extra passes
    if (targets.refract) {
      gl.setRenderTarget(targets.refract); gl.clear(); gl.render(scene, camera);
      u.tRefract.value = targets.refract.texture; u.tDepth.value = targets.refract.depthTexture;
    }
    if (targets.reflect) renderMirror(gl, scene, camera, mirrorCam, targets.reflect, m, u.uTexMat.value);
    u.tReflect.value = targets.reflect?.texture ?? null;
    gl.setRenderTarget(prevTarget); gl.shadowMap.autoUpdate = shadows;
    m.visible = true;
  });

  return <mesh ref={mesh} name="water" geometry={geometry} material={material} position-y={WATER_Y} renderOrder={2} />;
}

// Planar mirror with an oblique near plane (after three's Reflector): renders the scene
// reflected about the water plane, skipping grass/particles (layer 0 only) to stay cheap.
function renderMirror(gl, scene, camera, vc, target, mesh, texMat) {
  mesh.updateMatrixWorld();
  _cam.setFromMatrixPosition(camera.matrixWorld);
  _view.subVectors(mirrorPoint, _cam);
  if (_view.dot(up) > 0) return;                         // camera under the surface
  _view.reflect(up).negate().add(mirrorPoint);
  _rot.extractRotation(camera.matrixWorld);
  _look.set(0, 0, -1).applyMatrix4(_rot).add(_cam);
  _target.subVectors(mirrorPoint, _look).reflect(up).negate().add(mirrorPoint);
  vc.position.copy(_view);
  vc.up.set(0, 1, 0).applyMatrix4(_rot).reflect(up);
  vc.lookAt(_target);
  vc.far = camera.far; vc.near = camera.near;
  vc.updateMatrixWorld();
  vc.projectionMatrix.copy(camera.projectionMatrix);
  texMat.set(0.5, 0, 0, 0.5, 0, 0.5, 0, 0.5, 0, 0, 0.5, 0.5, 0, 0, 0, 1)
    .multiply(vc.projectionMatrix).multiply(vc.matrixWorldInverse).multiply(mesh.matrixWorld);
  _plane.setFromNormalAndCoplanarPoint(up, mirrorPoint).applyMatrix4(vc.matrixWorldInverse);
  _clip.set(_plane.normal.x, _plane.normal.y, _plane.normal.z, _plane.constant);
  const p = vc.projectionMatrix.elements;
  _q.set((Math.sign(_clip.x) + p[8]) / p[0], (Math.sign(_clip.y) + p[9]) / p[5], -1, (1 + p[10]) / p[14]);
  _clip.multiplyScalar(2 / _clip.dot(_q));
  p[2] = _clip.x; p[6] = _clip.y; p[10] = _clip.z + 1 - 0.003; p[14] = _clip.w;
  gl.setRenderTarget(target); gl.clear(); gl.render(scene, vc);
}
