// Anonymous play statistics → Supabase table `public.events` (one table, insert-only for this key).
//   visit : one row per app launch (device, browser, screen, GPU, graphics level, installed app…)
//   crash : an uncaught error / rejected promise / React error — at most 5 per launch, no repeats
//   story : a story finished (message = story id)
//   ready : the world finished loading (extra.ms = time since page start)
//   start : a story was started (message = story id)
//   time  : active (visible) play time so far in this launch (extra.sec), sent when the page is hidden
// The IP address and country are added by the database from the request itself (a trigger), so
// the page never needs to know them. Everything runs in the background: fire-and-forget fetches
// with keepalive, never awaited by the game, errors swallowed. Off on localhost unless
// localStorage['quran-journey-telemetry'] = '1'. Reading the data: Supabase dashboard (the views
// stats_daily · stats_devices · stats_countries · recent_crashes).
const URL_ = 'https://jyxlaiyiymcahxjlwyzi.supabase.co/rest/v1/events';
const KEY = 'sb_publishable_2XbnPlF49_8BE32etSn_6g__P60BFMs';   // public by design: it can only INSERT rows
const VERSION = typeof __APP_VERSION__ !== 'undefined' ? __APP_VERSION__ : 'dev';

const local = /^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname);
const store = (k, v) => { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch { return null; } return v; };
const enabled = !local || store('quran-journey-telemetry') === '1';
const rid = () => (crypto.randomUUID?.() ?? Math.random().toString(36).slice(2) + Date.now().toString(36));
const visitorId = store('quran-journey-visitor') || store('quran-journey-visitor', rid());
const sessionId = rid();

// ---- device -------------------------------------------------------------------------------------
function device() {
  const ua = navigator.userAgent, uad = navigator.userAgentData;
  const ipad = /iPad/.test(ua) || (navigator.maxTouchPoints > 1 && /Macintosh/.test(ua));
  const os = /Android ([\d.]+)/.test(ua) ? `Android ${RegExp.$1}`
    : /(iPhone|iPad|iPod).*? OS ([\d_]+)/.test(ua) ? `iOS ${RegExp.$2.replace(/_/g, '.')}` : ipad ? 'iPadOS'
    : /Windows NT ([\d.]+)/.test(ua) ? `Windows ${{ '10.0': '10/11', '6.3': '8.1', '6.1': '7' }[RegExp.$1] ?? RegExp.$1}`
    : /CrOS/.test(ua) ? 'ChromeOS' : /Mac OS X ([\d_]+)/.test(ua) ? `macOS ${RegExp.$1.replace(/_/g, '.')}` : /Linux/.test(ua) ? 'Linux' : 'other';
  const browser = /SamsungBrowser\/([\d.]+)/.test(ua) ? `Samsung ${RegExp.$1.split('.')[0]}`
    : /Edg\/([\d.]+)/.test(ua) ? `Edge ${RegExp.$1.split('.')[0]}` : /OPR\/([\d.]+)/.test(ua) ? `Opera ${RegExp.$1.split('.')[0]}`
    : /(CriOS|Chrome)\/([\d.]+)/.test(ua) ? `Chrome ${RegExp.$2.split('.')[0]}` : /(FxiOS|Firefox)\/([\d.]+)/.test(ua) ? `Firefox ${RegExp.$2.split('.')[0]}`
    : /Version\/([\d.]+).*Safari/.test(ua) ? `Safari ${RegExp.$1.split('.')[0]}` : 'other';
  const phone = /Mobi|iPhone|iPod|Android.*Mobile/.test(ua), tablet = ipad || (/Android/.test(ua) && !/Mobile/.test(ua));
  const model = /Android[^;)]*;\s*(?:[a-z]{2}[-_][a-z]{2};\s*)?([^;)]+?)(?:\s+Build\/|\))/i.test(ua) ? RegExp.$1.trim() : /iPhone/.test(ua) ? 'iPhone' : ipad ? 'iPad' : null;
  let gpu = null;
  try { const gl = document.createElement('canvas').getContext('webgl'); const x = gl?.getExtension('WEBGL_debug_renderer_info'); gpu = x ? gl.getParameter(x.UNMASKED_RENDERER_WEBGL) : null; gl?.getExtension('WEBGL_lose_context')?.loseContext(); } catch { /* none */ }
  return {
    os, browser, device: tablet ? 'tablet' : phone ? 'phone' : 'desktop', model: model && model !== 'K' ? model : uad?.mobile ? 'Android' : model,
    screen: `${screen.width}x${screen.height}@${Math.round((devicePixelRatio || 1) * 100) / 100}`,
    lang: navigator.language, gpu: gpu && gpu.slice(0, 120), memory_gb: navigator.deviceMemory ?? null, cores: navigator.hardwareConcurrency ?? null,
    installed: matchMedia('(display-mode: standalone), (display-mode: fullscreen)').matches || navigator.standalone === true,
  };
}
const quality = () => window.__game?.store?.getState?.().quality ?? window.__quality?.level ?? null;

// ---- send ------------------------------------------------------------------------------------------
let base = null;
function send(kind, row = {}) {
  if (!enabled || !navigator.onLine) return;
  try {
    base ??= { visitor_id: visitorId, session_id: sessionId, app_version: VERSION, ...device() };
    const body = JSON.stringify({ kind, ...base, quality: quality(), page: location.pathname + location.search, ...row });
    fetch(URL_, { method: 'POST', keepalive: body.length < 60000, mode: 'cors', credentials: 'omit',
      headers: { apikey: KEY, 'Content-Type': 'application/json', Prefer: 'return=minimal' }, body }).catch(() => {});
  } catch { /* never let statistics break the game */ }
}

// one visit per launch, once the game had a moment to load (never competes with the first frames)
function visit() {
  const go = () => send('visit', { referrer: document.referrer ? document.referrer.slice(0, 300) : null });
  const later = () => (window.requestIdleCallback ? requestIdleCallback(go, { timeout: 8000 }) : setTimeout(go, 1500));
  if (document.readyState === 'complete') setTimeout(later, 3000); else addEventListener('load', () => setTimeout(later, 3000), { once: true });
}

// ---- crashes ---------------------------------------------------------------------------------------
const seen = new Set(); let crashes = 0;
const NOISE = /ResizeObserver loop|^Script error\.?$|chrome-extension:|moz-extension:|safari-extension:|Non-Error promise rejection|AbortError|The play\(\) request was interrupted/i;
export function reportCrash(err, where = 'error', extra = {}) {
  try {
    const message = String(err?.message ?? err ?? 'unknown').slice(0, 1500), stack = err?.stack ? String(err.stack).slice(0, 3800) : null;
    if (NOISE.test(message) || (stack && NOISE.test(stack))) return;
    const key = message + '|' + where;
    if (seen.has(key) || crashes >= 5) return;
    seen.add(key); crashes++;
    send('crash', { message, stack, extra: { where, mode: window.__game?.state ?? null, online: navigator.onLine, ...extra } });
  } catch { /* ignore */ }
}
export function trackStory(id, extra = {}) { send('story', { message: String(id).slice(0, 100), extra }); }
let readySent = false;
export function trackReady() { if (readySent) return; readySent = true; send('ready', { extra: { ms: Math.round(performance.now()) } }); }
export function trackStart(id, extra = {}) { send('start', { message: String(id).slice(0, 100), extra }); }

// active play time: counts only while the page is visible; reported whenever it gets hidden/closed
let active = 0, since = document.visibilityState === 'visible' ? performance.now() : null, lastSent = 0;
function reportTime() {
  if (since != null) { active += performance.now() - since; since = null; }
  const sec = Math.round(active / 1000);
  if (sec >= 5 && sec - lastSent >= 5) { lastSent = sec; send('time', { extra: { sec } }); }
}

if (typeof window !== 'undefined') {
  addEventListener('error', e => reportCrash(e.error ?? e.message, 'error', { src: e.filename ? `${e.filename.split('/').pop()}:${e.lineno}:${e.colno}` : null }));
  addEventListener('unhandledrejection', e => reportCrash(e.reason, 'promise'));
  visit();
  addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden') reportTime(); else since = performance.now(); });
  addEventListener('pagehide', reportTime);
}
