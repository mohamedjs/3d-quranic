// Post-processing, kept deliberately subtle: AO for contact shading, a gentle bloom only
// on real highlights (sun glints, sky), light shafts from the sun on HIGH+, warm grading,
// ACES tone mapping, a soft vignette, and depth of field only during dialogue.
import { EffectComposer, N8AO, Bloom, ToneMapping, Vignette, HueSaturation, BrightnessContrast, DepthOfField, GodRays, SMAA } from '@react-three/postprocessing';
import { ToneMappingMode, BlendFunction, KernelSize } from 'postprocessing';
import { useRef } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { useGame, usePreset } from '../systems/store.js';

const farAway = new THREE.Vector3(0, 0, -1e4);

export function Effects({ sun }) {
  const preset = usePreset();
  const mode = useGame(s => s.mode);
  const dof = useRef();
  // DoF stays mounted (no shader recompile at the cut); its blur eases in only for cinematics
  useFrame((_, dt) => {
    const d = dof.current; if (!d) return;
    const { focus, mode: m } = useGame.getState(), on = (m === 'dialogue' || m === 'quran') && focus;
    d.bokehScale += ((on ? 3 : 0) - d.bokehScale) * (1 - Math.exp(-dt * 2.5));
    d.target = on ? focus : farAway;
  });
  return (
    <EffectComposer multisampling={0} enableNormalPass={false}>
      {preset.ao ? <N8AO aoRadius={1.6} distanceFalloff={1.2} intensity={2.2} quality={preset.dpr > 1.3 ? 'high' : 'medium'} halfRes={preset.dpr <= 1.25} color="#2a1a0c" /> : <></>}
      {preset.godrays && sun ? <GodRays sun={sun} samples={40} density={0.92} decay={0.93} weight={0.35} exposure={0.28} clampMax={1} kernelSize={KernelSize.SMALL} blur /> : <></>}
      {preset.dof ? <DepthOfField ref={dof} target={farAway} focalLength={0.02} bokehScale={0} /> : <></>}
      {preset.bloom ? <Bloom mipmapBlur intensity={0.22} luminanceThreshold={1.1} luminanceSmoothing={0.2} /> : <></>}
      <HueSaturation saturation={0.06} />
      <BrightnessContrast contrast={0.06} brightness={-0.01} />
      <ToneMapping mode={ToneMappingMode.ACES_FILMIC} />
      <Vignette offset={0.28} darkness={mode === 'quran' ? 0.75 : 0.42} blendFunction={BlendFunction.NORMAL} />
      <SMAA />
    </EffectComposer>
  );
}
