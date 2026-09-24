// Triplanar PBR: projects a texture set along world X/Y/Z so merged or instanced geometry
// without good UVs (walls, rocks, ruins) still gets correctly scaled detail. Vertex and
// instance colours still tint the result, so one material serves many objects.
import * as THREE from 'three';

export function triplanarMaterial(set, { scale = 2, key, roughness = 1, normalScale = 1, color, vertexColors = true } = {}) {
  const mat = new THREE.MeshStandardMaterial({ roughness, metalness: 0, vertexColors, color });
  mat.customProgramCacheKey = () => 'tri-' + key + (vertexColors ? 'v' : '');
  mat.onBeforeCompile = sh => {
    Object.assign(sh.uniforms, { tpAlb: { value: set.map }, tpNor: { value: set.normalMap }, tpArm: { value: set.aoMap }, tpScale: { value: 1 / scale }, tpNS: { value: normalScale } });
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vTpPos; varying vec3 vTpN;')
      .replace('#include <begin_vertex>', `#include <begin_vertex>
        vec4 tpW = vec4(transformed, 1.); vec3 tpN = objectNormal;
        #ifdef USE_INSTANCING
          tpW = instanceMatrix * tpW; tpN = mat3(instanceMatrix) * tpN;
        #endif
        tpW = modelMatrix * tpW; vTpPos = tpW.xyz; vTpN = normalize(mat3(modelMatrix) * tpN);`);
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>
        uniform sampler2D tpAlb, tpNor, tpArm; uniform float tpScale, tpNS;
        varying vec3 vTpPos; varying vec3 vTpN;`)
      .replace('#include <map_fragment>', `
        vec3 tpw = pow(abs(vTpN), vec3(4.)); tpw /= tpw.x + tpw.y + tpw.z;
        vec2 uvX = vTpPos.zy * tpScale, uvY = vTpPos.xz * tpScale, uvZ = vTpPos.xy * tpScale;
        vec3 tpA = texture2D(tpAlb, uvX).rgb * tpw.x + texture2D(tpAlb, uvY).rgb * tpw.y + texture2D(tpAlb, uvZ).rgb * tpw.z;
        vec3 tpR = texture2D(tpArm, uvX).rgb * tpw.x + texture2D(tpArm, uvY).rgb * tpw.y + texture2D(tpArm, uvZ).rgb * tpw.z;
        diffuseColor.rgb *= tpA * 1.6;`)
      .replace('#include <roughnessmap_fragment>', 'float roughnessFactor = roughness * tpR.g;')
      .replace('#include <normal_fragment_maps>', `
        vec3 nX = texture2D(tpNor, uvX).xyz * 2. - 1., nY = texture2D(tpNor, uvY).xyz * 2. - 1., nZ = texture2D(tpNor, uvZ).xyz * 2. - 1.;
        nX.xy *= tpNS; nY.xy *= tpNS; nZ.xy *= tpNS;
        vec3 wn = normalize(vTpN);
        // whiteout blend of the three projections, in world space
        vec3 bX = vec3(0., nX.y, nX.x) * sign(wn.x), bY = vec3(nY.x, 0., nY.y) * sign(wn.y), bZ = vec3(nZ.x, nZ.y, 0.) * sign(wn.z);
        vec3 wN = normalize(wn + bX * tpw.x + bY * tpw.y + bZ * tpw.z);
        normal = normalize((viewMatrix * vec4(wN, 0.)).xyz);`)
      .replace('#include <aomap_fragment>', `
        reflectedLight.indirectDiffuse *= tpR.r; reflectedLight.indirectSpecular *= tpR.r;`);
  };
  return mat;
}
