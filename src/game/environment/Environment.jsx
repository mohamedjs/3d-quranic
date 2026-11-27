// <Environment/>: golden-hour sky (warm-graded sun.json gradient on Lite–Med, 2k equirect HDRI
// on High–Ultra), warm-graded PMREM IBL on every tier (disposing old targets on tier switch),
// 3-layer horizon escarpment ring (`backdrop_hills.glb`), directional haze uniforms, and atmosphere.
import { useEffect, useMemo, useState } from 'react';
import * as THREE from 'three';
import { useThree, useFrame } from '@react-three/fiber';
import { Atmosphere } from './Atmosphere.jsx';
import { createSky } from './Sky.js';
import { getSkyPMREM, loadSkyTexture, sampleWarmGradient, warmGrade, SKY_REFL } from '../lighting/environmentMap.js';
import { AERIAL, updateAerialFog } from '../shaders/stylizedPbr.js';
import { refs } from '../systems/refs.js';
import { useGame, usePreset } from '../systems/store.js';

const WHITE = new THREE.Color('#ffffff');
const OCHRE = new THREE.Color('#c48952');

function derivePalette(sun) {
  const hor0 = sampleWarmGradient(sun, 0);
  const hor5 = sampleWarmGradient(sun, 5);
  const hor10 = sampleWarmGradient(sun, 10);
  const hor20 = sampleWarmGradient(sun, 20);
  const sky35 = sampleWarmGradient(sun, 35);
  const sky55 = sampleWarmGradient(sun, 55);
  const sunCol = new THREE.Color(sun?.sunColor || '#ffd488').lerp(WHITE, 0.35);
  return {
    aerialWarm: hor5.clone().lerp(hor10, 0.35),
    aerialCool: hor20.clone().lerp(sky35, 0.32).lerp(WHITE, 0.18),
    aerialGlow: hor0.clone().lerp(sunCol, 0.55),
    fogCol:     hor5.clone().lerp(hor10, 0.55),
    bgCol:      hor10.clone(),
    sunCol,
    shadowCol:  sky35.clone().lerp(sky55, 0.5),
    bounceCol:  warmGrade(sun?.ground || '#c48952', -10).lerp(OCHRE, 0.65),
  };
}

function createBackdropMaterial(sunDir, palette, lite) {
  return new THREE.ShaderMaterial({
    fog: false,
    vertexColors: true,
    uniforms: {
      uSunDir:        { value: sunDir.clone().normalize() },
      uAerialWarm:    AERIAL.uAerialWarm,
      uAerialCool:    AERIAL.uAerialCool,
      uAerialSunGlow: AERIAL.uAerialSunGlow,
      uSunCol:        { value: palette.sunCol.clone() },
      uShadowCol:     { value: palette.shadowCol.clone() },
      uBounceCol:     { value: palette.bounceCol.clone() },
      uLite:          { value: lite ? 1.0 : 0.0 },
    },
    vertexShader: /* glsl */`
      varying vec3 vWPos;
      varying vec3 vWNorm;
      varying vec2 vUv;
      varying vec3 vCol;
      void main() {
        vUv = uv;
        #ifdef USE_COLOR_ALPHA
          vCol = color.rgb;
        #else
          vCol = color;
        #endif
        vec4 wp = modelMatrix * vec4(position, 1.0);
        vWPos = wp.xyz;
        vWNorm = normalize(mat3(modelMatrix) * normal);
        gl_Position = projectionMatrix * viewMatrix * wp;
      }`,
    fragmentShader: /* glsl */`
      uniform vec3 uSunDir, uAerialWarm, uAerialCool, uAerialSunGlow;
      uniform vec3 uSunCol, uShadowCol, uBounceCol;
      uniform float uLite;
      varying vec3 vWPos, vWNorm, vCol;
      varying vec2 vUv;
      void main() {
        vec3 n = normalize(vWNorm);
        float layer = clamp(vUv.x, 0.0, 1.0); // 0.0 near foothills, 0.5 mid cliffs, 1.0 far peaks
        float hNorm = clamp(vUv.y, 0.0, 1.0); // 0.0 skirt base -> 1.0 ridge crest

        // Subtle horizontal geological strata on mid Egyptian limestone escarpments
        float strataWave = sin(vWPos.y * 0.48 + sin(vWPos.x * 0.016 + vWPos.z * 0.016) * 2.4);
        float strata = 1.0 + strataWave * 0.08 * (1.0 - abs(layer - 0.5) * 2.0) * smoothstep(0.18, 0.80, hNorm);
        vec3 albedo = vCol * strata;

        // Soft painterly golden-hour shading with clear ridge/cliff definition across all 3 layers
        float ndl = dot(n, uSunDir);
        float sunMask = smoothstep(-0.28, 0.48, ndl);
        vec3 skyAmb = mix(uBounceCol * 0.96, mix(uShadowCol, uAerialCool, 0.28), clamp(n.y * 0.5 + 0.5, 0.0, 1.0));
        vec3 lit = albedo * (skyAmb * 0.72 + uSunCol * sunMask * 0.72);

        // Gentle aerial perspective toward the warm-graded horizon so all 3 layers read as crisp
        // separated silhouettes (warm near foothills -> dusty mid cliffs -> cool pale-blue far peaks).
        vec3 viewDir = normalize(vWPos - cameraPosition);
        float sunAlign = clamp(dot(viewDir, uSunDir) * 0.5 + 0.5, 0.0, 1.0);
        vec3 horizonTint = mix(uAerialCool, uAerialWarm, smoothstep(0.20, 0.92, sunAlign) * (1.0 - 0.45 * layer));
        float mie = pow(max(dot(viewDir, uSunDir), 0.0), 5.0);
        horizonTint += uAerialSunGlow * mie * 0.11;

        // Subtle crest rim light to keep silhouette edges legible against the sky
        lit += uAerialSunGlow * smoothstep(0.72, 1.0, hNorm) * (0.04 + 0.12 * pow(max(dot(viewDir, uSunDir), 0.0), 3.0));

        // Three clearly separated silhouette bands (soft golden-hour horizon blend, no hard cliff contrast)
        float layerHaze = mix(mix(0.22, 0.48, layer * 2.0), mix(0.48, 0.72, (layer - 0.5) * 2.0), step(0.5, layer));
        float valleyMist = (1.0 - smoothstep(0.04, 0.45, hNorm)) * mix(0.18, 0.24, layer);
        vec3 col = mix(lit, horizonTint, clamp(layerHaze + valleyMist, 0.0, 0.82));

        gl_FragColor = vec4(col, 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
}

export function Environment({ env }) {
  const scene = useThree(s => s.scene);
  const gl = useThree(s => s.gl);
  const quality = useGame(s => s.quality);
  const preset = usePreset(), lite = !!preset.lite;
  const skyOct = preset.skyOct ?? (lite ? 2 : 4);
  const pbr = preset.shading === 'pbr';
  const hiSky = quality === 'high' || quality === 'ultra';
  const skyRes = hiSky ? '2k' : '1k';

  const [skyTex, setSkyTex] = useState({ res: null, tex: null });
  useEffect(() => {
    let alive = true;
    loadSkyTexture(env.sun?.hdri, skyRes).then(tex => { if (alive) setSkyTex({ res: skyRes, tex }); });
    return () => { alive = false; };
  }, [env.sun?.hdri, skyRes]);

  const palette = useMemo(() => derivePalette(env.sun), [env.sun]);
  const hiMap = hiSky && skyTex.res === '2k' ? skyTex.tex : null;

  const sky = useMemo(
    () => createSky(env.sun, { dir: env.sunDir, octaves: skyOct, map: hiMap }),
    [env, skyOct, hiMap]
  );
  useEffect(() => () => { sky.geometry.dispose(); sky.material.dispose(); }, [sky]);

  const backdrop = useMemo(() => {
    if (!env.backdropGeo) return null;
    const mat = createBackdropMaterial(env.sunDir, palette, lite);
    const mesh = new THREE.Mesh(env.backdropGeo, mat);
    mesh.name = 'backdrop-hills';
    mesh.frustumCulled = false;
    mesh.castShadow = false;
    mesh.receiveShadow = false;
    mesh.renderOrder = 0;
    return mesh;
  }, [env, palette, lite]);
  useEffect(() => () => { backdrop?.material.dispose(); }, [backdrop]);

  const [fogNear, fogFar] = preset.fog ?? [90, 600];
  useEffect(() => {
    updateAerialFog(env.sunDir);
    AERIAL.uAerialWarm.value.copy(palette.aerialWarm);
    AERIAL.uAerialCool.value.copy(palette.aerialCool);
    AERIAL.uAerialSunGlow.value.copy(palette.aerialGlow);
    scene.environment = getSkyPMREM(gl, env.sunDir, skyTex.tex);
    scene.environmentIntensity = pbr ? 0.42 : 0.45;
    SKY_REFL.uSkyMap.value = skyTex.tex ?? null;
    SKY_REFL.uHasSkyMap.value = skyTex.tex ? 1.0 : 0.0;
    SKY_REFL.uSunColor.value.set(env.sun?.sunColor || '#ffd488');
    scene.background = palette.bgCol.clone();
    scene.fog = new THREE.Fog(palette.fogCol, fogNear, fogFar);
  }, [scene, gl, env, palette, skyTex.tex, pbr, fogNear, fogFar]);

  useEffect(() => () => {
    SKY_REFL.uSkyMap.value = null;
    SKY_REFL.uHasSkyMap.value = 0.0;
  }, []);

  // Haze pushes back smoothly with camera height and NEVER begins inside 25 m (keeps close-ups crystal clear)
  useFrame(() => {
    sky.material.uniforms.uTime.value = refs.clock.wind;
    const f = scene.fog;
    if (f) { const d = Math.max(0, refs.view.dist, refs.view.height * 2.2); f.near = Math.max(25, fogNear + d * 1.4); f.far = Math.max(f.near + 60, fogFar + d * 4.5); }
  });
  return (
    <>
      <primitive object={sky} />
      {backdrop && <primitive object={backdrop} />}
      <Atmosphere />
    </>
  );
}
