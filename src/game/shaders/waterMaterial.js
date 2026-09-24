// Water: Schlick Fresnel between refracted body colour and reflection.
// - refraction + depth from a scene pass without the water: depth-based absorption
//   (red dies first), scattering tint, soft shoreline alpha and thin foam at contact
// - reflection from a planar mirror pass (HIGH/ULTRA) or the HDR sky (LOW/MEDIUM)
// - three scrolling normal-map layers at different scales and directions
// - tight + broad sun specular for glints
import * as THREE from 'three';

export function createWaterMaterial({ normalTex, envTex, sunDir }) {
  const mat = new THREE.ShaderMaterial({
    transparent: true, fog: true, depthWrite: false,
    uniforms: THREE.UniformsUtils.merge([THREE.UniformsLib.fog, {
      tReflect: { value: null }, tRefract: { value: null }, tDepth: { value: null },
      tNormal: { value: null }, tEnv: { value: null }, uTexMat: { value: new THREE.Matrix4() },
      uRes: { value: new THREE.Vector2(1, 1) }, uNear: { value: 0.1 }, uFar: { value: 1000 }, uTime: { value: 0 },
      uSunDir: { value: sunDir.clone() }, uSunColor: { value: new THREE.Color(1, 0.8, 0.55).multiplyScalar(4) },
      uDeep: { value: new THREE.Color(0x0b2a2c) }, uScatter: { value: new THREE.Color(0x2c5a4c) },
      uEnvI: { value: 1 }, uHasReflect: { value: 0 }, uHasRefract: { value: 0 },
    }]),
    vertexShader: /* glsl */`
      uniform mat4 uTexMat;
      varying vec4 vRefl; varying vec3 vW;
      #include <fog_pars_vertex>
      void main() {
        vec4 w = modelMatrix * vec4(position, 1.); vW = w.xyz;
        vRefl = uTexMat * vec4(position, 1.);
        vec4 mvPosition = viewMatrix * w; gl_Position = projectionMatrix * mvPosition;
        #include <fog_vertex>
      }`,
    fragmentShader: /* glsl */`
      uniform sampler2D tReflect, tRefract, tDepth, tNormal, tEnv;
      uniform vec2 uRes; uniform float uNear, uFar, uTime, uEnvI, uHasReflect, uHasRefract;
      uniform vec3 uSunDir, uSunColor, uDeep, uScatter;
      varying vec4 vRefl; varying vec3 vW;
      #include <common>
      #include <packing>
      #include <fog_pars_fragment>
      vec3 nrm(vec2 uv) { vec3 t = texture2D(tNormal, uv).xyz * 2. - 1.; return vec3(t.x, 0., t.y); }
      vec2 eqUv(vec3 d) { return vec2(atan(d.z, d.x) * RECIPROCAL_PI2 + .5, asin(clamp(d.y, -1., 1.)) * RECIPROCAL_PI + .5); }
      float wh(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
      float wnoise(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3. - 2. * f);
        return mix(mix(wh(i), wh(i + vec2(1, 0)), f.x), mix(wh(i + vec2(0, 1)), wh(i + vec2(1, 1)), f.x), f.y); }
      void main() {
        vec2 p = vW.xz; float t = uTime;
        vec3 ripple = nrm(p * .13 + vec2(t * .024, t * .011)) + nrm(p * .052 + vec2(-t * .013, t * .019)) * .9 + nrm(p * .37 + vec2(t * .05, -t * .035)) * .35;
        vec3 v = normalize(cameraPosition - vW);
        float dist = length(cameraPosition - vW);
        vec3 n = normalize(vec3(0., 1., 0.) * (2.2 + dist * .02) + ripple);   // calmer far away (less shimmer/aliasing)
        float cosT = clamp(dot(n, v), 0., 1.);
        float F = .02 + .98 * pow(1. - cosT, 5.);

        vec2 suv = gl_FragCoord.xy / uRes;
        float waterZ = perspectiveDepthToViewZ(gl_FragCoord.z, uNear, uFar);
        float thick = 4.; vec3 refr = uDeep;
        if (uHasRefract > .5) {
          float sceneZ = perspectiveDepthToViewZ(texture2D(tDepth, suv).x, uNear, uFar);
          thick = max(waterZ - sceneZ, 0.);
          vec2 ruv = suv + n.xz * .04 * clamp(thick, 0., 1.);
          float sceneZ2 = perspectiveDepthToViewZ(texture2D(tDepth, ruv).x, uNear, uFar);
          if (sceneZ2 > waterZ) ruv = suv; else thick = max(waterZ - sceneZ2, 0.);   // don't refract things in front
          refr = texture2D(tRefract, ruv).rgb;
        }
        float d = thick * (.3 + .7 * cosT);                                    // roughly the vertical column
        vec3 body = refr * exp(-vec3(.52, .19, .14) * d * 1.5) + uScatter * .35 * (1. - exp(-d * .8));
        if (uHasRefract < .5) body = mix(uScatter * .5, uDeep, .6);

        vec3 rd = reflect(-v, n); rd.y = abs(rd.y);
        vec3 refl = texture2D(tEnv, eqUv(rd)).rgb * uEnvI;
        if (uHasReflect > .5) { vec4 c = vRefl; c.xy += n.xz * .06 * c.w; refl = texture2DProj(tReflect, c).rgb; }

        vec3 col = mix(body, refl, F);
        vec3 h = normalize(uSunDir + v); float nh = max(dot(n, h), 0.);
        col += uSunColor * (pow(nh, 900.) * 18. + pow(nh, 90.) * .12) * smoothstep(-.05, .1, uSunDir.y);

        float alpha = 1.;
        if (uHasRefract > .5) {
          alpha = smoothstep(0., .35, thick);                                  // soft shoreline, no hard polygon edge
          float foam = (1. - smoothstep(.02, .22, thick)) * smoothstep(.35, .8, wnoise(p * 2.5 + t * .25) * wnoise(p * 6. - t * .4 + 7.));
          col = mix(col, vec3(.82, .8, .74), foam * .55);
        } else alpha = mix(.82, 1., F);
        gl_FragColor = vec4(col, alpha);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
        #include <fog_fragment>
      }`,
  });
  mat.uniforms.tNormal.value = normalTex; mat.uniforms.tEnv.value = envTex;
  return mat;
}
