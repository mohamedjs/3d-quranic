// Post-processing for the toon look, kept light: no SSAO or light shafts (they fight the
// flat cel shading), a subtle bloom on the brightest highlights (sun disc, foam, lit lime
// walls), neutral tone mapping so the painted palette keeps its hues, a soft warm vignette,
// SMAA for clean ink lines, and depth of field only during dialogue.
import { EffectComposer, Bloom, ToneMapping, Vignette, HueSaturation, BrightnessContrast, DepthOfField, SMAA } from '@react-three/postprocessing';
import { ToneMappingMode, BlendFunction } from 'postprocessing';
import { useRef } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { useGame, usePreset } from '../systems/store.js';

const farAway = new THREE.Vector3(0, 0, -1e4);

export function Effects() {
  const preset = usePreset();
  const mode = useGame(s => s.mode);
  const dof = useRef();
  // DoF stays mounted (no shader recompile at the cut); its blur eases in only for cinematics
  useFrame((_, dt) => {
    const d = dof.current; if (!d) return;
    const { focus, mode: m } = useGame.getState(), on = (m === 'dialogue' || m === 'quran') && focus;
    d.bokehScale += ((on ? 2.5 : 0) - d.bokehScale) * (1 - Math.exp(-dt * 2.5));
    d.target = on ? focus : farAway;
  });
  return (
    <EffectComposer multisampling={0} enableNormalPass={false}>
      {preset.dof ? <DepthOfField ref={dof} target={farAway} focalLength={0.02} bokehScale={0} /> : <></>}
      {preset.bloom ? <Bloom mipmapBlur intensity={0.14} luminanceThreshold={0.92} luminanceSmoothing={0.12} /> : <></>}
      <HueSaturation saturation={0.08} />
      <BrightnessContrast contrast={0.04} brightness={0} />
      <ToneMapping mode={ToneMappingMode.NEUTRAL} />
      <Vignette offset={0.32} darkness={mode === 'quran' ? 0.7 : 0.3} blendFunction={BlendFunction.NORMAL} />
      <SMAA />
    </EffectComposer>
  );
}
