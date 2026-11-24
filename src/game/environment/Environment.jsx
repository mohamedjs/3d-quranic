// <Environment/>: painterly golden-hour sky, procedural sky-baked PMREM IBL (Med–Ultra),
// 3-layer horizon escarpment ring (`backdrop_hills.glb`, custom aerial-perspective shader so
// Lite's 140 m gameplay fog never erases it), directional haze uniforms, and living atmosphere.
import { useEffect, useMemo } from 'react';
import * as THREE from 'three';
import { useThree, useFrame } from '@react-three/fiber';
import { Atmosphere } from './Atmosphere.jsx';
import { createSky } from './Sky.js';
import { getSkyPMREM } from '../lighting/environmentMap.js';
import { AERIAL, updateAerialFog } from '../shaders/stylizedPbr.js';
import { refs } from '../systems/refs.js';
import { usePreset } from '../systems/store.js';

function createBackdropMaterial(sunDir, lite) {
  return new THREE.ShaderMaterial({
    fog: false,
    vertexColors: true,
    uniforms: {
      uSunDir:        { value: sunDir.clone().normalize() },
      uAerialWarm:    AERIAL.uAerialWarm,
      uAerialCool:    AERIAL.uAerialCool,
      uAerialSunGlow: AERIAL.uAerialSunGlow,
      uSunCol:        { value: new THREE.Color('#ffd08a') },
      uShadowCol:     { value: new THREE.Color('#6e7fa3') },
      uBounceCol:     { value: new THREE.Color('#c48952') },
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

        // Gentle aerial perspective toward a pale warm-blue horizon so all 3 layers read as crisp
        // separated silhouettes (warm near foothills -> dusty mid cliffs -> cool pale-blue far peaks).
        vec3 viewDir = normalize(vWPos - cameraPosition);
        float sunAlign = clamp(dot(viewDir, uSunDir) * 0.5 + 0.5, 0.0, 1.0);
        vec3 horizonTint = mix(uAerialCool, uAerialWarm, smoothstep(0.20, 0.92, sunAlign) * (1.0 - 0.45 * layer));
        float mie = pow(max(dot(viewDir, uSunDir), 0.0), 5.0);
        horizonTint += uAerialSunGlow * mie * 0.11;

        // Subtle crest rim light to keep silhouette edges legible against the sky
        lit += uAerialSunGlow * smoothstep(0.72, 1.0, hNorm) * (0.04 + 0.12 * pow(max(dot(viewDir, uSunDir), 0.0), 3.0));

        // Three clearly separated silhouette bands (identical readability on Lite and High)
        float layerHaze = mix(mix(0.20, 0.44, layer * 2.0), mix(0.44, 0.66, (layer - 0.5) * 2.0), step(0.5, layer));
        float valleyMist = (1.0 - smoothstep(0.04, 0.42, hNorm)) * mix(0.18, 0.24, layer);
        vec3 col = mix(lit, horizonTint, clamp(layerHaze + valleyMist, 0.0, 0.78));

        gl_FragColor = vec4(col, 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
}

export function Environment({ env }) {
  const scene = useThree(s => s.scene);
  const gl = useThree(s => s.gl);
  const preset = usePreset(), lite = !!preset.lite;
  const skyOct = preset.skyOct ?? (lite ? 2 : 4);
  const pbr = preset.shading === 'pbr';

  const sky = useMemo(() => createSky(env.sunDir, skyOct), [env, skyOct]);
  useEffect(() => () => { sky.geometry.dispose(); sky.material.dispose(); }, [sky]);

  const backdrop = useMemo(() => {
    if (!env.backdropGeo) return null;
    const mat = createBackdropMaterial(env.sunDir, lite);
    const mesh = new THREE.Mesh(env.backdropGeo, mat);
    mesh.name = 'backdrop-hills';
    mesh.frustumCulled = false;
    mesh.castShadow = false;
    mesh.receiveShadow = false;
    mesh.renderOrder = 0;
    return mesh;
  }, [env, lite]);
  useEffect(() => () => { backdrop?.material.dispose(); }, [backdrop]);

  const [fogNear, fogFar] = preset.fog ?? [90, 600];
  useEffect(() => {
    updateAerialFog(env.sunDir);
    scene.environment = pbr ? getSkyPMREM(gl, env.sunDir) : null;
    scene.environmentIntensity = pbr ? 0.48 : 1.0;
    scene.background = new THREE.Color('#dce0e4');
    scene.fog = new THREE.Fog('#dcd6ca', fogNear, fogFar);
  }, [scene, gl, env, pbr, fogNear, fogFar]);

  // Haze pushes back smoothly with camera height so lookout hill & bird's-eye views stay clear on Lite too
  useFrame(() => {
    sky.material.uniforms.uTime.value = refs.clock.wind;
    const f = scene.fog;
    if (f) { const d = Math.max(refs.view.dist, refs.view.height * 2.2); f.near = fogNear + d * 1.4; f.far = fogFar + d * 4.5; }
  });
  return (
    <>
      <primitive object={sky} />
      {backdrop && <primitive object={backdrop} />}
      <Atmosphere />
    </>
  );
}
