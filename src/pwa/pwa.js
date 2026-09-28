// Installable offline app: service-worker registration, the «update available» toast, the
// install button on the title screen (Android/desktop Chrome) or an Add-to-Home-Screen hint
// (iOS Safari), and "download every story for offline play" (Settings).
import { QuranService, verseKeys } from '../game/systems/quran.js';

const $ = id => document.getElementById(id);
const supported = typeof navigator !== 'undefined' && 'serviceWorker' in navigator && (location.protocol === 'https:' || location.hostname === 'localhost' || location.hostname === '127.0.0.1');

// beforeinstallprompt can fire before the game UI exists: catch it from the first moment
let deferredInstall = null, onInstallable = null;
if (typeof window !== 'undefined') {
  addEventListener('beforeinstallprompt', e => { e.preventDefault(); deferredInstall = e; onInstallable?.(); });
  addEventListener('appinstalled', () => { deferredInstall = null; const b = $('btn-install'); if (b) b.hidden = true; });
}
const isIOS = () => /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.maxTouchPoints > 1 && /Macintosh/.test(navigator.userAgent));
const isSafari = () => /safari/i.test(navigator.userAgent) && !/crios|fxios|edgios|opios|chrome|android/i.test(navigator.userAgent);
export const isStandalone = () => matchMedia('(display-mode: standalone), (display-mode: fullscreen)').matches || navigator.standalone === true;

export const pwa = { registration: null, version: null, ready: false, supported };

// S(): the current language's strings · toast(text, ms)
export function initPWA({ S, toast, delay = 2500 }) {
  // ---- install ---------------------------------------------------------------------------
  const btn = $('btn-install');
  const showInstall = () => {
    if (!btn || isStandalone()) return;
    btn.textContent = S().install; btn.hidden = false;
  };
  if (btn) {
    btn.onclick = async () => {
      if (deferredInstall) {
        const e = deferredInstall; deferredInstall = null;
        e.prompt(); const { outcome } = await e.userChoice.catch(() => ({}));
        if (outcome === 'accepted') btn.hidden = true;
      } else if (isIOS()) toast(S().iosHint, 9000);
    };
    onInstallable = showInstall;
    if (deferredInstall) showInstall();
    else if (isIOS() && isSafari() && !isStandalone()) showInstall();        // iOS: a short hint instead of a prompt
  }
  pwa.relabel = () => { if (btn && !btn.hidden) btn.textContent = S().install; const u = $('update'); if (u && !u.hidden) u.textContent = S().updateReady; };

  // ---- service worker ----------------------------------------------------------------------
  if (!supported) return;
  const hadController = !!navigator.serviceWorker.controller;
  let reloading = false, asked = false;
  const offerUpdate = reg => {
    const u = $('update'); if (!u || !reg.waiting) return;
    u.textContent = S().updateReady; u.hidden = false;
    u.onclick = () => { asked = true; u.disabled = true; reg.waiting?.postMessage({ type: 'SKIP_WAITING' }); setTimeout(() => location.reload(), 4000); };
  };
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (asked && !reloading) { reloading = true; location.reload(); }   // only when the child tapped «update»
  });
  navigator.serviceWorker.addEventListener('message', e => {
    if (e.data?.type === 'SW_ACTIVE') {
      pwa.version = e.data.version; pwa.ready = true;
      if (!hadController && !asked) toast(S().offlineReady, 4000);        // first install: the whole game is now cached
    }
  });
  const register = async () => {
    try {
      const reg = await navigator.serviceWorker.register(new URL('sw.js', document.baseURI).href, { updateViaCache: 'none' });
      pwa.registration = reg;
      if (reg.waiting && navigator.serviceWorker.controller) offerUpdate(reg);
      reg.addEventListener('updatefound', () => {
        const w = reg.installing;
        w?.addEventListener('statechange', () => { if (w.state === 'installed' && navigator.serviceWorker.controller) offerUpdate(reg); });
      });
      if (navigator.serviceWorker.controller) pwa.ready = true;
      // look for a new version now and then (and when the app comes back to the foreground)
      setInterval(() => reg.update().catch(() => {}), 30 * 60e3);
      document.addEventListener('visibilitychange', () => { if (!document.hidden) reg.update().catch(() => {}); });
    } catch (e) { console.warn('service worker:', e); }
  };
  // after the world is up, so the ~16 MB precache never competes with the first load
  setTimeout(register, delay);
}

// ---- download every story for offline play -------------------------------------------------
// Fetches exactly what the stories use — each chapter's info, the verses (text, word timings,
// translation, audio link) for the chosen reciter, the Arabic tafsir, and the recitation mp3s —
// a few at a time (gentle on Quran.com). The service worker keeps every response. Local voice
// lines and illustrations are precached already; they are re-requested so any the precache
// missed are filled in too.
export async function downloadAllStories({ data, reciter, onProgress }) {
  if (!supported) throw new Error('no service worker');
  if (!navigator.onLine) throw new Error('offline');
  await navigator.serviceWorker.ready;                                   // responses are only kept once it controls the page
  if (!navigator.serviceWorker.controller) await new Promise(r => { navigator.serviceWorker.addEventListener('controllerchange', r, { once: true }); setTimeout(r, 8000); });
  const keys = new Set(), surahs = new Set();
  for (const e of data.encounters) for (const s of e.steps ?? []) {
    if (s.type !== 'verses') continue;
    for (const k of verseKeys(s.from, s.to ?? s.from)) { keys.add(k); surahs.add(+k.split(':')[0]); }
  }
  const jobs = [
    () => QuranService.getReciters(),
    ...[...surahs].map(n => () => QuranService.getSurah(n)),
    ...[...keys].map(k => () => QuranService.getTafsir(k)),
  ];
  const audio = [];
  for (const k of keys) jobs.push(async () => { const v = await QuranService.getVerse(k, reciter); if (v.audioUrl) audio.push(v.audioUrl); });
  const local = await fetch('./audio/manifest.json').then(r => r.json()).then(m => [...new Set(Object.values(m).filter(f => typeof f === 'string' && f.startsWith('audio/')))].map(f => './' + f)).catch(() => []);
  let done = 0, failed = 0, total = jobs.length + keys.size + local.length;
  const tick = () => onProgress?.(done, total, failed);
  const run = async (list, n) => {
    let i = 0;
    await Promise.all(Array.from({ length: n }, async () => {
      while (i < list.length) {
        const job = list[i++];
        try { await job(); } catch (e) { failed++; console.warn('offline download:', e.message || e); }
        done++; tick();
      }
    }));
  };
  tick();
  await run(jobs, 3);
  total = jobs.length + audio.length + local.length; tick();
  // opaque (no-cors) like the <audio> element: the service worker stores the whole file
  await run(audio.map(u => () => fetch(u, { mode: 'no-cors', credentials: 'omit' }).then(r => { if (r.type !== 'opaque' && !r.ok) throw new Error(`${r.status} ${u}`); return r.arrayBuffer(); })), 2);
  await run(local.map(u => () => fetch(u).then(r => { if (!r.ok) throw new Error(`${r.status} ${u}`); return r.arrayBuffer(); })), 4);
  return { done, total, failed, verses: keys.size, audio: audio.length };
}
