// World water plane with 5-tier quality scaling:
//  - Lite / Low : 1 normal fetch (512 water_nor) + 1 sky + 1 bank fetch, transparent Beer-Lambert water
//  - Medium     : + 2 flow-advected normal layers (1024 water_nor) + slow large swell
//  - High       : + half-res (0.5x) planar reflection RT (skips LAYER_NO_REFLECT & shadow re-render)
//  - Ultra      : + full-res (1.0x) planar reflection RT + 2048^2 bank map
// Also syncs the shared street-rill shader tier (`streamWaterTier`) and water normal map.
import { useEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';
import { useFrame, useThree } from '@react-three/fiber';
import {
  createWaterMaterial, bindWater, setWaterNormal, waterTime, streamWaterTier, WATER_TIERS,
} from '../shaders/waterMaterial.js';
import { buildWaterBank } from './waterBank.js';
import { loadWaterNormal } from '../world/loaders.js';
import { SIZE, WATER_Y, OASIS } from '../terrain/heightfield.js';
import { useGame, usePreset } from '../systems/store.js';

const _pos = new THREE.Vector3();
const _dir = new THREE.Vector3();
const _look = new THREE.Vector3();
const _up = new THREE.Vector3();
const _plane = new THREE.Plane();
const _normal = new THREE.Vector3(0, 1, 0);
const _clip4 = new THREE.Vector4();
const _q4 = new THREE.Vector4();
const _frustum = new THREE.Frustum();
const _projView = new THREE.Matrix4();
const _bias = new THREE.Matrix4().set(
  0.5, 0.0, 0.0, 0.5,
  0.0, 0.5, 0.0, 0.5,
  0.0, 0.0, 0.5, 0.5,
  0.0, 0.0, 0.0, 1.0,
);

// World water surface bounding boxes with per-body planar reflection cutoff distances
// (wide Nile & Oasis reflect from afar; narrow canals & distant bodies skip when hidden behind alleys).
const WATER_REGIONS = [
  { box: new THREE.Box3(new THREE.Vector3(-250, WATER_Y - 0.5, 54), new THREE.Vector3(250, WATER_Y + 0.5, 108)), dist: 95 },
  { box: new THREE.Box3(new THREE.Vector3(-52, WATER_Y - 0.5, 16), new THREE.Vector3(52, WATER_Y + 0.5, 76)), dist: 56 },
  { box: new THREE.Box3(new THREE.Vector3(OASIS.x - 18, WATER_Y - 0.5, OASIS.z - 18), new THREE.Vector3(OASIS.x + 18, WATER_Y + 0.5, OASIS.z + 18)), dist: 82 },
];
const _closest = new THREE.Vector3();

function waterInView(camera, scale = 1.0) {
  _projView.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
  _frustum.setFromProjectionMatrix(_projView);
  for (const { box, dist } of WATER_REGIONS) {
    box.clampPoint(camera.position, _closest);
    if (_closest.distanceTo(camera.position) <= dist * scale && _frustum.intersectsBox(box)) return true;
  }
  return false;
}

export function Water({ clock }) {
  const preset = usePreset();
  const gl = useThree(s => s.gl);
  const vpSize = useThree(s => s.size);
  const waterMode = preset.waterMode ?? (preset.lite ? 'lite' : 'medium');
  const tier = WATER_TIERS[waterMode] ?? 0;
  const usePlanar = tier >= 3;
  const reflScale = tier >= 4 ? 1.0 : 0.5;
  const bankRes = tier >= 4 ? 2048 : 1024;
  const norSize = tier >= 2 ? 1024 : 512;

  const bank = useMemo(() => buildWaterBank(bankRes), [bankRes]);
  const material = useMemo(() => bindWater(createWaterMaterial({ size: SIZE, mode: waterMode }), bank), [bank, waterMode]);
  const geometry = useMemo(() => new THREE.PlaneGeometry(SIZE, SIZE, 1, 1).rotateX(-Math.PI / 2), []);
  const meshRef = useRef();
  const mirrorCam = useMemo(() => {
    const c = new THREE.PerspectiveCamera();
    c.layers.set(0); // skips LAYER_NO_REFLECT (grass, crops, bushes, motes, birds, coins, guide)
    return c;
  }, []);

  // Half-res (High) or full-res (Ultra) linear HDR planar reflection render target
  const reflRT = useMemo(() => {
    if (!usePlanar) return null;
    const dpr = Math.min(gl.getPixelRatio(), 2);
    const w = Math.max(256, Math.round(vpSize.width * dpr * reflScale));
    const h = Math.max(144, Math.round(vpSize.height * dpr * reflScale));
    return new THREE.WebGLRenderTarget(w, h, {
      type: THREE.HalfFloatType,
      minFilter: THREE.LinearFilter,
      magFilter: THREE.LinearFilter,
      depthBuffer: true,
      stencilBuffer: false,
      generateMipmaps: false,
    });
  }, [usePlanar, gl, vpSize.width, vpSize.height, reflScale]);

  // Non-blocking water normal map load (512 Lite/Low, 1024 Medium+); disposes prior texture on tier swap.
  const activeNorRef = useRef(null);
  const wantNorRef = useRef(norSize);
  const warnedNorRef = useRef(new Set());
  wantNorRef.current = norSize;

  useEffect(() => {
    let alive = true;
    loadWaterNormal(norSize, { anisotropy: norSize >= 1024 ? 4 : 1 }).then(tex => {
      if (!alive) {
        if (wantNorRef.current !== norSize && activeNorRef.current?.tex !== tex) tex.dispose();
        return;
      }
      const prev = activeNorRef.current;
      activeNorRef.current = { size: norSize, tex };
      setWaterNormal(tex);
      if (prev && prev.tex !== tex) prev.tex.dispose();
    }).catch(err => {
      if (!warnedNorRef.current.has(norSize)) {
        warnedNorRef.current.add(norSize);
        console.warn(`[water] water_nor.webp (${norSize}) unavailable:`, err?.message || err);
      }
    });
    return () => { alive = false; };
  }, [norSize]);

  useEffect(() => () => {
    setWaterNormal(null);
    activeNorRef.current?.tex?.dispose();
    activeNorRef.current = null;
  }, []);

  useEffect(() => {
    streamWaterTier.value = tier;
  }, [tier]);

  useEffect(() => {
    material.uniforms.tReflect.value = reflRT?.texture ?? null;
    material.uniforms.uHasReflect.value = reflRT ? 1.0 : 0.0;
    return () => { reflRT?.dispose(); };
  }, [material, reflRT]);

  useEffect(() => () => { material.dispose(); }, [material]);
  useEffect(() => () => { geometry.dispose(); }, [geometry]);

  useFrame(({ gl: renderer, scene, camera }) => {
    waterTime.value = clock.water;
    const mesh = meshRef.current;
    if (!reflRT || !mesh || camera.position.y <= WATER_Y + 0.05) return;
    const mode = useGame.getState().mode;
    if (mode === 'quran' || mode === 'panel') return;

    // Skip planar reflection pass when no Nile/canal/oasis water surface is within view range,
    // or on the single frame after a live tier switch before the new directional shadow map exists.
    if (!waterInView(camera, tier >= 4 ? 1.25 : 1.0)
      || scene.children.some(o => o.isDirectionalLight && o.castShadow && !o.shadow?.map)) {
      material.uniforms.uHasReflect.value = 0.0;
      return;
    }
    material.uniforms.uHasReflect.value = 1.0;

    // Reflect main camera position, forward target, and up vector across horizontal plane y = WATER_Y
    camera.getWorldPosition(_pos);
    camera.getWorldDirection(_dir);
    _look.copy(_pos).addScaledVector(_dir, 10);
    _up.set(0, 1, 0).applyQuaternion(camera.quaternion);

    mirrorCam.fov = camera.fov;
    mirrorCam.aspect = camera.aspect;
    mirrorCam.near = camera.near;
    mirrorCam.far = Math.min(camera.far, tier >= 4 ? 320 : 240);
    mirrorCam.position.set(_pos.x, 2 * WATER_Y - _pos.y, _pos.z);
    mirrorCam.up.set(_up.x, -_up.y, _up.z);
    mirrorCam.lookAt(_look.x, 2 * WATER_Y - _look.y, _look.z);
    mirrorCam.updateMatrixWorld(true);
    mirrorCam.projectionMatrix.copy(camera.projectionMatrix);

    // Texture projection matrix (world pos -> mirrorCam UV) computed before oblique clip
    const tm = material.uniforms.uTexMatrix.value;
    tm.copy(_bias).multiply(mirrorCam.projectionMatrix).multiply(mirrorCam.matrixWorldInverse);

    // Oblique near-plane clipping at y = WATER_Y (Lengyel's method)
    _plane.set(_normal, -WATER_Y + 0.03);
    _plane.applyMatrix4(mirrorCam.matrixWorldInverse);
    _clip4.set(_plane.normal.x, _plane.normal.y, _plane.normal.z, _plane.constant);
    const el = mirrorCam.projectionMatrix.elements;
    _q4.x = (Math.sign(_clip4.x) + el[8]) / el[0];
    _q4.y = (Math.sign(_clip4.y) + el[9]) / el[5];
    _q4.z = -1.0;
    _q4.w = (1.0 + el[10]) / el[14];
    const dotCQ = _clip4.dot(_q4);
    if (Math.abs(dotCQ) > 1e-5) {
      _clip4.multiplyScalar(2.0 / dotCQ);
      el[2] = _clip4.x;
      el[6] = _clip4.y;
      el[10] = _clip4.z + 1.0;
      el[14] = _clip4.w;
    }

    // Reuse main pass's already-rendered shadow map during planar reflection (prevent stealing
    // Lighting.jsx's `shadowMap.needsUpdate = true` flag into the reflection pass!).
    const prevRT = renderer.getRenderTarget();
    const prevXr = renderer.xr.enabled;
    const prevShadowAuto = renderer.shadowMap.autoUpdate;
    const prevShadowNeeds = renderer.shadowMap.needsUpdate;
    renderer.xr.enabled = false;
    renderer.shadowMap.autoUpdate = false;
    renderer.shadowMap.needsUpdate = false;
    mesh.visible = false;
    renderer.setRenderTarget(reflRT);
    renderer.clear();
    renderer.render(scene, mirrorCam);
    mesh.visible = true;
    renderer.setRenderTarget(prevRT);
    renderer.shadowMap.autoUpdate = prevShadowAuto;
    renderer.shadowMap.needsUpdate = prevShadowNeeds;
    renderer.xr.enabled = prevXr;
  });

  // renderOrder=-1 ensures transparent water draws first in the transparent pass (after all opaque
  // riverbed/terrain/bridge/reed meshes, and before lantern halos, motes, blobs, guide trails & markers).
  return <mesh ref={meshRef} name="water" geometry={geometry} material={material} position-y={WATER_Y} renderOrder={-1} />;
}
