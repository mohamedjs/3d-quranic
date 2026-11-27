// Post-processing for Medium / High / Ultra:
//  - Far-background-only cinematic DoF in dialogue (characters and stage within >=12 m stay
//    100% razor-crisp with zero near-blur bleed; only the far background softens gently).
//  - High-threshold Bloom so only true emissives / sun disc / water glints glow (never walls or faces).
//  - ACES Filmic tone mapping + procedural 17^3 warm grade LUT + gentle vignette + SMAA.
import { EffectComposer, Bloom, ToneMapping, LUT, Vignette, DepthOfField, SMAA } from '@react-three/postprocessing';
import { ToneMappingMode, BlendFunction, LookupTexture } from 'postprocessing';
import { useEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { useGame, usePreset } from '../systems/store.js';

const farAway = new THREE.Vector3(0, 0, -1e4);

function smoothstep(a, b, x) {
  const t = Math.max(0, Math.min(1, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
}

// Build a 17^3 sRGB 3D LUT procedurally: gently warms highlights toward #F4C766 (luminance-
// preserved so white galabiyas stay clean ivory), adds subtle cool-teal depth in shadows,
// and lifts saturation ~+5%. Converted to Uint8 so WebGL2 linear filtering works universally.
function buildWarmLUT(size = 17) {
  const data = new Float32Array(size * size * size * 4);
  const sizeSq = size * size;
  const inv = 1 / (size - 1);
  // #F4C766 in sRGB = (0.957, 0.780, 0.400), luma = 0.7905 -> luma-normalized warm ratios
  const wr = 0.9569 / 0.7905;
  const wg = 0.7804 / 0.7905;
  const wb = 0.4000 / 0.7905;

  for (let b = 0; b < size; b++) {
    const sb = b * inv;
    for (let g = 0; g < size; g++) {
      const sg = g * inv;
      for (let r = 0; r < size; r++) {
        const sr = r * inv;
        const luma = 0.2126 * sr + 0.7152 * sg + 0.0722 * sb;

        // +5% saturation
        let cr = luma + (sr - luma) * 1.05;
        let cg = luma + (sg - luma) * 1.05;
        let cb = luma + (sb - luma) * 1.05;

        // Gently warm upper midtones & highlights toward #F4C766 without darkening whites
        const hiW = smoothstep(0.32, 0.88, luma) * 0.14;
        cr += (cr * wr - cr) * hiW;
        cg += (cg * wg - cg) * hiW;
        cb += (cb * wb - cb) * hiW;

        // Subtle cool-teal tint in deep shadows (vanishes at pure black to keep blacks crisp)
        const loW = (1 - smoothstep(0.03, 0.32, luma)) * smoothstep(0.0, 0.04, luma);
        cr -= 0.012 * loW;
        cg += 0.004 * loW;
        cb += 0.015 * loW;

        const i4 = (r + g * size + b * sizeSq) * 4;
        data[i4 + 0] = Math.max(0, Math.min(1, cr));
        data[i4 + 1] = Math.max(0, Math.min(1, cg));
        data[i4 + 2] = Math.max(0, Math.min(1, cb));
        data[i4 + 3] = 1;
      }
    }
  }
  const lut = new LookupTexture(data, size);
  lut.name = 'warm_golden_v4';
  lut.convertToUint8();
  return lut;
}

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
  const warmLut = useMemo(() => buildWarmLUT(17), []);
  useEffect(() => () => { warmLut.dispose(); }, [warmLut]);

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
      <ToneMapping mode={ToneMappingMode.ACES_FILMIC} />
      <LUT lut={warmLut} />
      <Vignette offset={0.36} darkness={mode === 'quran' ? 0.55 : 0.20} blendFunction={BlendFunction.NORMAL} />
      <SMAA />
    </EffectComposer>
  );
}
