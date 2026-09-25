// Quality presets. Everything expensive reads from here; AUTO starts from a device guess
// (Low or Medium, High only for clearly strong desktop GPUs) and <PerformanceMonitor> first
// trims the resolution, then steps the level down (or back up) from measured frame rate.
export const LEVELS = ['low', 'medium', 'high', 'ultra'];

// dpr: resolution scale (capped by the screen, and at 1.5 on phones)
// shadowEvery: re-render the shadow map every N frames (1 = every frame)
// post: post-processing at all (off on LOW: tone mapping is then done by the renderer)
// grass / grassDist: tufts built / drawn · cropDist, bushDist: chunk draw distances (thinned
// toward the edge) · outlineDist: crop ink hulls · npcDist: cast drawn/animated within
// terrainSeg: terrain grid resolution (built once)
export const PRESETS = {
  low:    { dpr: 0.8,  shadowMap: 1024, shadowRange: 28, shadowEvery: 3, post: false, grass: 12000, grassDist: 42,  cropDist: 38, bushDist: 70,  outlineDist: 0,  npcDist: 60,  terrainSeg: 256, trees: 0.5,  outlines: false, bloom: false, dof: false, particles: 0.35 },
  medium: { dpr: 1,    shadowMap: 2048, shadowRange: 40, shadowEvery: 2, post: true,  grass: 34000, grassDist: 65,  cropDist: 55, bushDist: 110, outlineDist: 22, npcDist: 90,  terrainSeg: 320, trees: 0.8,  outlines: true,  bloom: true,  dof: true,  particles: 0.7 },
  high:   { dpr: 1.25, shadowMap: 2048, shadowRange: 45, shadowEvery: 1, post: true,  grass: 65000, grassDist: 95,  cropDist: 70, bushDist: 160, outlineDist: 30, npcDist: 140, terrainSeg: 360, trees: 1,    outlines: true,  bloom: true,  dof: true,  particles: 1 },
  ultra:  { dpr: 1.75, shadowMap: 4096, shadowRange: 55, shadowEvery: 1, post: true,  grass: 100000, grassDist: 120, cropDist: 90, bushDist: 220, outlineDist: 40, npcDist: 200, terrainSeg: 360, trees: 1,    outlines: true,  bloom: true,  dof: true,  particles: 1 },
};

export const isMobile = () => typeof navigator !== 'undefined' && (/Android|iPhone|iPad|iPod|Mobile|Silk|Kindle/i.test(navigator.userAgent)
  || (navigator.maxTouchPoints > 1 && /Macintosh/.test(navigator.userAgent)));   // iPadOS reports as a Mac

// A cheap first guess from what the browser tells us; the monitor corrects it within seconds.
// Computed once: every probe creates a WebGL context, and browsers cap how many exist.
let guess;
export function guessLevel() { return (guess ??= probe()); }
export function deviceInfo() {
  const n = typeof navigator === 'undefined' ? {} : navigator;
  return { mem: n.deviceMemory ?? 8, cores: n.hardwareConcurrency ?? 4, mobile: isMobile(), coarse: typeof matchMedia !== 'undefined' && matchMedia('(pointer: coarse)').matches };
}
function probe() {
  try {
    const { mem, cores, mobile, coarse } = deviceInfo();
    const gl = document.createElement('canvas').getContext('webgl2', { failIfMajorPerformanceCaveat: false });
    if (!gl) return 'low';
    const ext = gl.getExtension('WEBGL_debug_renderer_info');
    const gpu = (ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER)) || '';
    const maxTex = gl.getParameter(gl.MAX_TEXTURE_SIZE);
    gl.getExtension('WEBGL_lose_context')?.loseContext();
    if (/swiftshader|llvmpipe|software|basic render|microsoft basic/i.test(gpu)) return 'low';
    if (mem <= 2 || cores <= 2 || maxTex < 8192) return 'low';
    if (mobile || coarse) {
      // phones/tablets: recent Apple GPUs and Adreno 7xx/8xx, Mali-G7xx/Immortalis with plenty of RAM can take Medium
      if (mem >= 6 && cores >= 8 && /apple gpu|adreno \(tm\) [78]\d\d|adreno [78]\d\d|immortalis|mali-g7[1-9]|mali-g[6-9]\d\d/i.test(gpu)) return 'medium';
      if (/apple gpu/i.test(gpu) && cores >= 6) return 'medium';
      return 'low';
    }
    if (/intel/i.test(gpu)) return mem >= 8 && cores >= 8 ? 'medium' : 'low';   // integrated: Medium only with RAM/cores to spare
    if (/mali|adreno|powervr|videocore|vivante/i.test(gpu)) return 'low';
    // strong desktop GPUs start one step higher; the monitor can still climb to Ultra
    if (mem >= 8 && cores >= 8 && /rtx|radeon rx [67]\d{3}|rx [67]\d{3}|apple m[1-9] (pro|max|ultra)|apple m[3-9]/i.test(gpu)) return 'high';
    return 'medium';
  } catch { return 'low'; }
}
