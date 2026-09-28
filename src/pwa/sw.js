/* Quran Journey — service worker (hand-written, no Workbox: npm could not install it here).
 * Built by tools/vite-pwa.js, which prepends
 *   self.__PRECACHE = [{ url, rev, size, core }]   (paths relative to this file)
 *   self.__VERSION  = '<hash of that list>'
 *
 * · precache: the app shell, JS/CSS chunks, story data, UI svgs, all models (+ Draco decoder),
 *   illustrations and the recorded voice lines. Files already cached with the same revision are
 *   kept across versions (an update only downloads what changed). Core files must all arrive;
 *   an audio/illustration that fails is fetched again at runtime.
 * · runtime: Quran.com API JSON → stale-while-revalidate; recitation mp3s → cache-first with
 *   Range support (a story played once works offline); Google Fonts → cached.
 * · never cached here: the Piper voice (~63 MB, the library keeps it in its own storage) and
 *   its onnxruntime / CDN files.
 * · updates: a new version installs in the background and WAITS; the page shows «تحديث جديد
 *   متاح» and sends SKIP_WAITING when the child taps it, then reloads. A running session is
 *   never switched under its feet.
 */
const PRECACHE = self.__PRECACHE || [];
const VERSION = self.__VERSION || 'dev';
const SHELL = 'qj-shell';                 // one cache; keys carry the revision: <url>?__rev=<rev>
const API = 'qj-quran-api', AUDIO = 'qj-quran-audio', FONTS = 'qj-fonts';
const scope = new URL(self.registration.scope);
const abs = u => new URL(u, scope).href;
const keyFor = e => abs(e.url) + (e.url.includes('?') ? '&' : '?') + '__rev=' + e.rev;
const byUrl = new Map(PRECACHE.map(e => [abs(e.url), e]));
byUrl.set(scope.href, byUrl.get(abs('index.html')));                 // "./" is the shell too
const AUDIO_HOSTS = /(^|\.)(verses\.quran\.com|audio\.qurancdn\.com|everyayah\.com|quranicaudio\.com|download\.quranicaudio\.com|mirrors\.quranicaudio\.com|cdn\.islamic\.network)$/;

async function precache() {
  const cache = await caches.open(SHELL), have = new Set((await cache.keys()).map(r => r.url));
  const todo = PRECACHE.filter(e => !have.has(keyFor(e)));
  let i = 0, failed = [];
  const worker = async () => {
    while (i < todo.length) {
      const e = todo[i++];
      try {
        const r = await fetch(abs(e.url), { cache: 'no-cache', credentials: 'same-origin' });
        if (!r.ok) throw new Error(r.status);
        await cache.put(keyFor(e), r);
      } catch (err) { failed.push(e); }
    }
  };
  await Promise.all(Array.from({ length: 6 }, worker));
  const core = failed.filter(e => e.core);
  if (core.length) throw new Error('precache failed: ' + core.map(e => e.url).join(', '));
}

self.addEventListener('install', e => { e.waitUntil(precache()); });
self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    const cache = await caches.open(SHELL), keep = new Set(PRECACHE.map(keyFor));
    for (const r of await cache.keys()) if (!keep.has(r.url)) await cache.delete(r);   // files of old versions
    await self.clients.claim();
    for (const c of await self.clients.matchAll({ type: 'window' })) c.postMessage({ type: 'SW_ACTIVE', version: VERSION });
  })());
});
self.addEventListener('message', e => {
  if (e.data?.type === 'SKIP_WAITING') self.skipWaiting();
  if (e.data?.type === 'VERSION') e.source?.postMessage({ type: 'VERSION', version: VERSION, files: PRECACHE.length });
});

// ---- Range requests (media elements ask for byte ranges; Safari insists on 206) -------------
async function ranged(req, res) {
  const range = req.headers.get('range');
  if (!range || !res || res.status !== 200 || res.type === 'opaque') return res;
  const m = /bytes=(\d*)-(\d*)/.exec(range); if (!m) return res;
  const buf = await res.arrayBuffer(), size = buf.byteLength;
  let start = m[1] === '' ? size - +m[2] : +m[1], end = m[1] === '' ? size - 1 : m[2] === '' ? size - 1 : +m[2];
  start = Math.max(0, start); end = Math.min(size - 1, end);
  if (start > end || start >= size) return new Response(null, { status: 416, headers: { 'Content-Range': `bytes */${size}` } });
  const h = new Headers(res.headers);
  h.set('Content-Range', `bytes ${start}-${end}/${size}`); h.set('Content-Length', String(end - start + 1));
  return new Response(buf.slice(start, end + 1), { status: 206, statusText: 'Partial Content', headers: h });
}

async function fromShell(req, entry) {
  const cache = await caches.open(SHELL);
  let res = await cache.match(keyFor(entry));
  if (!res) {                                                  // not cached yet (or evicted): network, then keep it
    try {
      res = await fetch(abs(entry.url), { credentials: 'same-origin' });
      if (res.ok) cache.put(keyFor(entry), res.clone());
    } catch (e) { return Response.error(); }
  }
  if (req.method === 'HEAD') return new Response(null, { status: res.status, headers: res.headers });
  return ranged(req, res);
}

async function staleWhileRevalidate(req, name) {
  const cache = await caches.open(name), hit = await cache.match(req);
  const net = fetch(req).then(r => { if (r.ok || r.type === 'opaque') cache.put(req, r.clone()); return r; }).catch(() => null);
  if (hit) { net.catch(() => {}); return hit; }
  return (await net) || Response.error();
}

// Recitation audio: cache-first by URL (no Range in the key). A miss is fetched whole — with
// CORS when the CDN allows it (so ranges can be served from the copy), else as an opaque copy.
async function audio(req) {
  const cache = await caches.open(AUDIO), url = req.url;
  let res = await cache.match(url);
  if (!res) {
    try {
      res = await fetch(url, { mode: 'cors', credentials: 'omit' });
      if (!res.ok) return res;
    } catch (e) {
      try { res = await fetch(url, { mode: 'no-cors', credentials: 'omit' }); } catch (e2) { return Response.error(); }
    }
    await cache.put(url, res.clone());
  }
  return ranged(req, res);
}

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET' && req.method !== 'HEAD') return;
  const url = new URL(req.url);
  if (url.origin === scope.origin) {
    const clean = url.origin + url.pathname;
    if (req.mode === 'navigate' && clean.startsWith(scope.href)) {
      const shell = byUrl.get(abs('index.html'));
      if (shell && (clean === scope.href || /\/(index\.html)?$/.test(clean))) { e.respondWith(fromShell(req, shell)); return; }
    }
    const entry = byUrl.get(clean);
    if (entry) e.respondWith(fromShell(req, entry));
    return;                                                    // anything else same-origin: the network as usual
  }
  if (req.method !== 'GET') return;
  if (url.hostname === 'api.quran.com') { e.respondWith(staleWhileRevalidate(req, API)); return; }
  if (AUDIO_HOSTS.test(url.hostname)) { e.respondWith(audio(req)); return; }
  if (url.hostname === 'fonts.googleapis.com' || url.hostname === 'fonts.gstatic.com') { e.respondWith(staleWhileRevalidate(req, FONTS)); return; }
});
