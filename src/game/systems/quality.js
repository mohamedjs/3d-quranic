// Quality presets. Everything expensive reads from here; AUTO starts from a device guess
// (Lite on old/weak phones, Low or Medium, High only for clearly strong desktop GPUs) and
// <PerformanceMonitor> first trims the resolution, then steps the level down (or back up)
// from measured frame rate.
export const LEVELS = ['lite', 'low', 'medium', 'high', 'ultra'];

// dpr: resolution scale (capped by the screen, and at 1.5 on phones)
// shadowEvery: re-render the shadow map every N frames (1 = every frame)
// post: post-processing at all (off on LOW: tone mapping is then done by the renderer)
// grass / grassDist: tufts built / drawn · cropDist, bushDist: chunk draw distances (thinned
// toward the edge) · outlineDist: crop ink hulls · npcDist: cast drawn/animated within
// terrainSeg: terrain grid resolution (built once)
// LITE (خفيف جدًا) — for ~5-year-old phones: 30 fps cap, DPR ≤ 1, the sun shadow map is
// rendered once for the static world (re-baked only when the child walks far) and the cast
// get soft blob shadows; env models are merged per chunk × material (no per-model instancing,
// no wind on trees, no ink hulls); grass/crops only round the child; NPCs within 30 m; no
// birds/motes/post; simplest water; shorter fog. See README "Quality levels".
export const PRESETS = {
  lite:   { dpr: 1,    shadowMap: 2048, shadowRange: 70, shadowEvery: Infinity, staticShadow: true, post: false, grass: 2600, grassDist: 20, cropDist: 24, bushDist: 38, outlineDist: 0, npcDist: 30, terrainSeg: 224, trees: 0.45, outlines: false, bloom: false, dof: false, particles: 0, birds: 0, lite: true, fps: 30, fog: [30, 125], envDist: 100, rocks: 110, litter: false, cropThin: 0.75, coinSeg: 10 },
  low:    { dpr: 0.8,  shadowMap: 1024, shadowRange: 28, shadowEvery: 3, post: false, grass: 12000, grassDist: 42,  cropDist: 38, bushDist: 70,  outlineDist: 0,  npcDist: 60,  terrainSeg: 256, trees: 0.5,  outlines: false, bloom: false, dof: false, particles: 0.35 },
  medium: { dpr: 1,    shadowMap: 2048, shadowRange: 40, shadowEvery: 2, post: true,  grass: 34000, grassDist: 65,  cropDist: 55, bushDist: 110, outlineDist: 22, npcDist: 90,  terrainSeg: 320, trees: 0.8,  outlines: true,  bloom: true,  dof: true,  particles: 0.7 },
  high:   { dpr: 1.25, shadowMap: 2048, shadowRange: 45, shadowEvery: 1, post: true,  grass: 65000, grassDist: 95,  cropDist: 70, bushDist: 160, outlineDist: 30, npcDist: 140, terrainSeg: 360, trees: 1,    outlines: true,  bloom: true,  dof: true,  particles: 1 },
  ultra:  { dpr: 1.75, shadowMap: 4096, shadowRange: 55, shadowEvery: 1, post: true,  grass: 100000, grassDist: 120, cropDist: 90, bushDist: 220, outlineDist: 40, npcDist: 200, terrainSeg: 360, trees: 1,    outlines: true,  bloom: true,  dof: true,  particles: 1 },
};

export const isMobile = () => typeof navigator !== 'undefined' && (/Android|iPhone|iPad|iPod|Mobile|Silk|Kindle/i.test(navigator.userAgent)
  || (navigator.maxTouchPoints > 1 && /Macintosh/.test(navigator.userAgent)));   // iPadOS reports as a Mac

// A cheap first guess from what the browser tells us; the monitor corrects it within seconds.
// Computed once: every probe creates a WebGL context, and browsers cap how many exist.
let guess, gpuName = '';
export function guessLevel() { return (guess ??= probe()); }
export const gpuRenderer = () => (guessLevel(), gpuName);
// Old / small mobile and integrated GPUs that should start on LITE. Adreno 5xx only below 530
// (505/506/508/509/510/512 are budget parts; 530/540 were flagships), Mali Midgard (T6xx–T8xx)
// and Utgard (4xx), Mali-G31/G51/G52/G57 budget Bifrost/Valhall, all PowerVR (budget phones /
// old iPhones via Safari), Intel HD 2000–5xxx and older, VideoCore/Vivante, software renderers.
export const WEAK_GPU = /mali-?4\d\d|mali-?t[678]\d\d|mali-?g(31|51|52|57)\b|adreno[^0-9]*(\(tm\) )?[34]\d\d|adreno[^0-9]*(\(tm\) )?5[0-2]\d|powervr|sgx|rogue|intel.*hd graphics (2\d{3}|3\d{3}|4\d{3}|5\d{3})?\b(?!\d)|intel.*(gma|hd graphics$)|videocore|vivante|swiftshader|llvmpipe|softpipe|software|basic render|microsoft basic/i;
// Lite's resolution: 1 (never above), 0.75 on tiny GPUs / 2 GB phones
export const liteDpr = () => (/mali-?4\d\d|mali-?t[67]\d\d|adreno[^0-9]*(\(tm\) )?[34]\d\d|sgx|videocore/i.test(gpuRenderer()) || (deviceInfo().mem <= 2 && deviceInfo().mobile) ? 0.75 : 1);
export function deviceInfo() {
  const n = typeof navigator === 'undefined' ? {} : navigator;
  return { mem: n.deviceMemory ?? 8, cores: n.hardwareConcurrency ?? 4, mobile: isMobile(), coarse: typeof matchMedia !== 'undefined' && matchMedia('(pointer: coarse)').matches };
}
function probe() {
  try {
    const { mem, cores, mobile, coarse } = deviceInfo();
    const gl = document.createElement('canvas').getContext('webgl2', { failIfMajorPerformanceCaveat: false });
    if (!gl) return 'lite';
    const ext = gl.getExtension('WEBGL_debug_renderer_info');
    const gpu = (ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER)) || '';
    const maxTex = gl.getParameter(gl.MAX_TEXTURE_SIZE);
    gl.getExtension('WEBGL_lose_context')?.loseContext();
    gpuName = gpu;
    if (/swiftshader|llvmpipe|software|basic render|microsoft basic/i.test(gpu)) return 'lite';
    if (WEAK_GPU.test(gpu)) return 'lite';
    if (mem <= 3 && (mobile || coarse || cores <= 4)) return 'lite';        // 2–3 GB phones / old laptops
    if (cores <= 2 || maxTex < 4096) return 'lite';
    if ((mobile || coarse) && cores <= 4 && !/apple gpu/i.test(gpu)) return 'lite';   // quad-core Androids are 2016–2019 era
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
  } catch { return 'lite'; }
}

// ---- device age: resolved on the loading screen, BEFORE the world is built ---------------------
// Rule: a device from before ~2021 starts on LOW (or LITE when probe() above already calls it very
// weak); 2021+ devices keep the AUTO guess. Browsers don't expose a release year, so any ONE of
// these signals marks a device as pre-2021 (each is conservative — a false "old" only costs detail):
//  · Android ≤ 10 — from UA Client Hints (platformVersion) when Chrome offers them; the UA string
//    only when it isn't Chrome's frozen "Android 10; K" (which every modern Android reports)
//  · iOS ≤ 14 (the iPhone 13 / 2021 shipped with iOS 15)
//  · iPhone screen sizes only pre-2021 models have: 320×568 (5s/SE1), 375×667 (6–8/SE2),
//    414×736 (Plus), 414×896 (XR/11/XS Max/11 Pro Max). 375×812 (X–11 Pro vs 12/13 mini) and newer
//    sizes are left alone.
//  · the GPU generation, from WEBGL_debug_renderer_info (table below)
//  · navigator.deviceMemory ≤ 2 GB (Chrome only)
// A saved manual choice in Settings always wins (store.js); a device that measured too slow once is
// remembered as LITE (store.js HINT) and wins over all of this too.
export const OLD_GPU = [
  [/adreno[^0-9]*(\(tm\) )?[2-5]\d\d\b/i, 'Adreno 2xx–5xx (≤2018)'],
  [/adreno[^0-9]*(\(tm\) )?6([0-3]\d|40|50)\b/i, 'Adreno 605–650 (Snapdragon up to the 865, ≤2020); 642L/643/644/660+ are 2021'],
  [/mali-?t\d|mali-?4\d\d/i, 'Mali-400/450, Mali T-series (Utgard/Midgard, ≤2017)'],
  [/mali-?g(31|51|52|57|71|72|76|77)\b/i, 'Mali-G31…G77 (Bifrost / first Valhall, ≤2020); G68/G78/G310/G610+ are 2021+'],
  [/powervr|sgx|rogue|ge8\d{3}/i, 'PowerVR (budget phones, old iPads)'],
  [/apple a([4-9]|1[0-2])\b/i, 'Apple A12 or older (Safari usually says just "Apple GPU": then screen/iOS decide)'],
  [/intel.*[^u]hd graphics|intel.*uhd graphics (p?6\d\d)\b|intel.*iris(\(r\))? (plus|pro|graphics [56]\d\d)/i, 'Intel HD, UHD 6xx, Iris Plus/Pro (≤2020); Iris Xe / UHD 7xx are 2021'],
  [/(gtx|geforce) ?(9\d\d|10\d\d|16\d\d)\b|geforce mx ?\d{3}|quadro [kmp]\d/i, 'GeForce GTX 9xx/10xx/16xx, MX (≤2019); RTX keeps AUTO'],
  [/radeon(\(tm\))? (r[579] |hd |rx ?[45]\d\d\b|vega)/i, 'Radeon R5–R9, HD, RX 4xx/5xx, Vega (≤2019); plain "Radeon Graphics" APUs keep AUTO'],
];
const OLD_IPHONE = [[320, 568], [375, 667], [414, 736], [414, 896]];

async function clientHints() {
  const ch = typeof navigator !== 'undefined' ? navigator.userAgentData : null;
  if (!ch?.getHighEntropyValues) return { platform: ch?.platform };
  try {
    const v = await Promise.race([ch.getHighEntropyValues(['model', 'platformVersion']), new Promise((_, no) => setTimeout(no, 500))]);
    return { platform: v.platform ?? ch.platform, platformVersion: v.platformVersion, model: v.model };
  } catch { return { platform: ch.platform }; }
}
export async function deviceAge() {
  const ua = navigator.userAgent, reasons = [], h = await clientHints();
  let android = null;
  if (/android/i.test(h.platform ?? '') && h.platformVersion) android = parseFloat(h.platformVersion);
  else { const m = ua.match(/Android (\d+)(?:\.\d+)*;? ?([^;)]*)/); if (m && !(m[1] === '10' && m[2] === 'K')) android = +m[1]; }
  if (android !== null && android <= 10) reasons.push(`Android ${android}`);
  const ios = ua.match(/(iPhone|iPad|iPod)[^)]* OS (\d+)_/);
  if (ios && +ios[2] <= 14) reasons.push(`iOS ${ios[2]}`);
  if (/iPhone/.test(ua) && typeof screen !== 'undefined') {
    const w = Math.min(screen.width, screen.height), hh = Math.max(screen.width, screen.height);
    if (OLD_IPHONE.some(([a, b]) => a === w && b === hh)) reasons.push(`iPhone screen ${w}×${hh}`);
  }
  const gpu = gpuRenderer(), g = OLD_GPU.find(([re]) => re.test(gpu));
  if (g) reasons.push(`GPU: ${g[1]}`);
  if ((navigator.deviceMemory ?? 8) <= 2) reasons.push(`${navigator.deviceMemory} GB RAM`);
  return { old: reasons.length > 0, reasons, gpu, model: h.model || '' };
}
// Called once by main.jsx while the loading screen is up; store.js reads the result (autoLevel).
let resolved = null;
export const resolvedQuality = () => resolved;
export async function resolveQuality() {
  if (resolved) return resolved;
  const base = guessLevel();
  let age = { old: false, reasons: [] };
  try { age = await deviceAge(); } catch { /* keep the plain guess */ }
  const level = age.old ? (base === 'lite' ? 'lite' : 'low') : base;
  resolved = { level, base, ...age, at: performance.now() };
  if (typeof window !== 'undefined') window.__quality = resolved;          // test / support probe
  console.info(`[quality] ${level} (guess ${base}${age.old ? '; pre-2021: ' + age.reasons.join(', ') : ''}) · ${age.gpu || gpuName}`);
  return resolved;
}
