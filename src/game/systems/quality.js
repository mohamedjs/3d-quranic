// Quality presets. Everything expensive reads from here; AUTO starts from a device guess
// and <PerformanceMonitor> steps it down (or back up) from measured frame rate.
export const LEVELS = ['low', 'medium', 'high', 'ultra'];

export const PRESETS = {
  low:    { dpr: 0.8,  shadowMap: 1024, shadowRange: 30, grass: 20000, grassDist: 55,  trees: 0.55, antiTile: false, water: 'env',     reflectRes: 0,   refractRes: 0,   ao: false, bloom: false, godrays: false, dof: false, particles: 0.4 },
  medium: { dpr: 1,    shadowMap: 2048, shadowRange: 40, grass: 40000, grassDist: 75,  trees: 0.8,  antiTile: true,  water: 'refract', reflectRes: 0,   refractRes: 0.5, ao: true,  bloom: true,  godrays: false, dof: true,  particles: 0.7 },
  high:   { dpr: 1.25, shadowMap: 2048, shadowRange: 45, grass: 65000, grassDist: 95,  trees: 1,    antiTile: true,  water: 'full',    reflectRes: 0.5, refractRes: 0.5, ao: true,  bloom: true,  godrays: true,  dof: true,  particles: 1 },
  ultra:  { dpr: 1.75, shadowMap: 4096, shadowRange: 55, grass: 100000, grassDist: 120, trees: 1,    antiTile: true,  water: 'full',    reflectRes: 1,   refractRes: 1,   ao: true,  bloom: true,  godrays: true,  dof: true,  particles: 1 },
};

// A cheap first guess from what the browser tells us; the monitor corrects it within seconds.
// Computed once: every probe creates a WebGL context, and browsers cap how many exist.
let guess;
export function guessLevel() { return (guess ??= probe()); }
function probe() {
  try {
    if (matchMedia('(pointer: coarse)').matches || innerWidth < 800) return 'low';
    const gl = document.createElement('canvas').getContext('webgl2');
    if (!gl) return 'low';
    const ext = gl.getExtension('WEBGL_debug_renderer_info');
    const gpu = (ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER)) || '';
    gl.getExtension('WEBGL_lose_context')?.loseContext();
    if (/swiftshader|llvmpipe|software/i.test(gpu)) return 'low';
    if (/intel|mali|adreno|powervr|apple gpu/i.test(gpu)) return 'medium';
    if (/rtx|radeon rx [67]|apple m[2-9]|rx 7|rx 6/i.test(gpu)) return 'ultra';
    return 'high';
  } catch { return 'medium'; }
}
