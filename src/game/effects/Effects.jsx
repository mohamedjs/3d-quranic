// Post-processing for Medium / High / Ultra:
//  - Far-background-only cinematic DoF in dialogue (characters and stage within >=12 m stay
//    100% razor-crisp with zero near-blur bleed; only the far background softens gently).
//  - High-threshold Bloom so only true emissives / sun disc / water glints glow (never walls or faces).
//  - Neutral tone mapping + subtle post-tonemap polish + gentle vignette + SMAA.
import { EffectComposer, Bloom, ToneMapping, Vignette, HueSaturation, BrightnessContrast, DepthOfField, SMAA } from '@react-three/postprocessing';
import { ToneMappingMode, BlendFunction } from 'postprocessing';
import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { useGame, usePreset } from '../systems/store.js';

const farAway = new THREE.Vector3(0, 0, -1e4);

// Patch postprocessing's CircleOfConfusionMaterial once on mount so dialogue DoF:
//  1) Never applies near-blur (prevents foreground child/shoulder from blurring or bleeding halos).
//  2) Keeps a full-sharpness dead zone out to max(12.0 m, focusDistance + 3.5 m) so every speaker,
//     companion, and character within ~12 m is guaranteed 100% bit-exact crisp.
//  3) Softens ONLY the far background smoothly beyond the sharp zone.
function configureDialogueCoC(dofEffect) {
  const coc = dofEffect?.cocMaterial;
  if (!coc || coc.userData?.v3Patched) return;
  const orig = coc.fragmentShader;
  const patched = orig.replace(
    /float signedDistance=distance-focusDistance;float magnitude=smoothstep\(0\.0,focusRange,abs\(signedDistance\)\);gl_FragColor\.rg=magnitude\*vec2\(step\(signedDistance,0\.0\),step\(0\.0,signedDistance\)\);/,
    'float sharpEnd=max(12.0,focusDistance+3.5);float farMag=smoothstep(sharpEnd,sharpEnd+max(focusRange,18.0),distance);gl_FragColor.rg=vec2(0.0,farMag);'
  );
  if (patched !== orig) {
    coc.fragmentShader = patched;
    coc.userData.v3Patched = true;
    coc.needsUpdate = true;
  }
}

export function Effects() {
  const preset = usePreset();
  const mode = useGame(s => s.mode);
  const dof = useRef();

  useEffect(() => {
    if (dof.current) configureDialogueCoC(dof.current);
  }, [preset.dof]);

  // DoF stays mounted (no shader recompile at the cut); its far-background blur eases in only for cinematics
  useFrame((_, dt) => {
    const d = dof.current; if (!d) return;
    if (!d.cocMaterial?.userData?.v3Patched) configureDialogueCoC(d);
    const { focus, mode: m } = useGame.getState(), on = (m === 'dialogue' || m === 'quran') && focus;
    const wantScale = on ? (m === 'quran' ? 2.2 : 1.75) : 0;
    d.bokehScale += (wantScale - d.bokehScale) * (1 - Math.exp(-dt * 3.0));
    d.target = on ? focus : farAway;
    d.cocMaterial.focusRange = 22.0;   // world meters (postprocessing v6.38 uses world units!)
  });

  return (
    <EffectComposer multisampling={0} enableNormalPass={false}>
      {preset.dof ? <DepthOfField ref={dof} target={farAway} focusRange={22} bokehScale={0} /> : <></>}
      {preset.bloom ? <Bloom mipmapBlur intensity={0.11} luminanceThreshold={1.75} luminanceSmoothing={0.22} /> : <></>}
      <ToneMapping mode={ToneMappingMode.NEUTRAL} />
      <HueSaturation saturation={0.05} />
      <BrightnessContrast contrast={0.02} brightness={0} />
      <Vignette offset={0.36} darkness={mode === 'quran' ? 0.55 : 0.20} blendFunction={BlendFunction.NORMAL} />
      <SMAA />
    </EffectComposer>
  );
}
