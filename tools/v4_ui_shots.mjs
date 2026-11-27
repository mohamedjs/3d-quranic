// M6 UI proof capture script: serves dist/ locally and captures every v4 UI screen at
// 1280x720 (desktop) and 390x844 (phone) into blender/v4/previews/M6_<screen>_{desktop,phone}.png,
// plus checks 360 px AR/EN/RU overflow, touch target sizes, backdrop-filter tier gating,
// console/404 errors, renderer.info and __game.balance({ verify: true }).
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { chromium } = require('/var/www/html/old/mic-clean/video/node_modules/playwright-core');

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const DIST = path.join(ROOT, 'dist');
const PREVIEWS = path.join(ROOT, 'blender/v4/previews');
const CHROME = path.join(os.homedir(), '.cache/ms-playwright/chromium-1248/chrome-linux64/chrome');

const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'application/javascript', '.mjs': 'application/javascript',
  '.css': 'text/css', '.svg': 'image/svg+xml', '.png': 'image/png', '.webp': 'image/webp',
  '.jpg': 'image/jpeg', '.json': 'application/json', '.glb': 'model/gltf-binary', '.wasm': 'application/wasm',
  '.mp3': 'audio/mpeg', '.webmanifest': 'application/manifest+json',
};

fs.mkdirSync(PREVIEWS, { recursive: true });

function startServer() {
  const server = http.createServer((req, res) => {
    const urlPath = decodeURIComponent((req.url || '/').split('?')[0]);
    let file = path.join(DIST, urlPath === '/' ? 'index.html' : urlPath);
    if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) file = path.join(DIST, 'index.html');
    const ext = path.extname(file);
    res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
    fs.createReadStream(file).pipe(res);
  });
  return new Promise(resolve => server.listen(0, '127.0.0.1', () => resolve({ server, port: server.address().port })));
}

async function waitReady(page) {
  await page.waitForFunction(() => window.__game && document.getElementById('loading')?.classList.contains('gone'), { timeout: 90000 });
  await page.waitForFunction(() => !!document.getElementById('i-stories') && !!document.getElementById('o-corner'), { timeout: 15000 });
  await page.evaluate(() => Promise.race([document.fonts?.ready, new Promise(r => setTimeout(r, 3000))]));
  await page.waitForTimeout(600);
}

async function captureViewport(browser, port, { tag, width, height, touch, quality = 'high' }) {
  const ctx = await browser.newContext({
    viewport: { width, height },
    deviceScaleFactor: 1,
    hasTouch: touch,
    isMobile: touch,
  });
  const page = await ctx.newPage();
  const pageErrors = [];
  const failed404 = [];
  page.on('pageerror', e => pageErrors.push(e.message));
  page.on('response', r => {
    if (r.status() === 404 && r.url().startsWith(`http://127.0.0.1:${port}`)) failed404.push(r.url());
  });

  // Ensure a clean start so title screen shows freshly with no stale localStorage
  await page.addInitScript(() => {
    try { localStorage.removeItem('quran-journey-v1'); } catch {}
  });

  await page.goto(`http://127.0.0.1:${port}/?q=${quality}`, { waitUntil: 'domcontentloaded' });
  await waitReady(page);
  if (touch) await page.evaluate(() => document.body.classList.add('touch'));

  const shot = async name => {
    const out = path.join(PREVIEWS, `M6_${name}_${tag}.png`);
    await page.screenshot({ path: out, type: 'png' });
    console.log(`  [${tag}] saved ${path.relative(ROOT, out)}`);
  };

  // Wait until CSS opacity/transform transitions settle cleanly (SwiftShader renders slowly)
  const waitVisible = async (sel, extraMs = 450) => {
    await page.waitForSelector(sel, { timeout: 15000 });
    await page.waitForFunction(s => {
      const el = document.querySelector(s);
      if (!el) return false;
      const op = parseFloat(getComputedStyle(el).opacity || '1');
      return op >= 0.98;
    }, sel, { timeout: 10000 }).catch(() => {});
    await page.waitForTimeout(extraMs);
  };

  // 1. Title screen (wait for title.webp to finish decoding)
  await page.waitForTimeout(800);
  await shot('title');

  // Verify glass blur state on this tier
  const glassState = await page.evaluate(() => {
    const hasClass = document.body.classList.contains('q-glass');
    const obj = document.getElementById('objective');
    const bf = getComputedStyle(obj).backdropFilter || getComputedStyle(obj).webkitBackdropFilter || 'none';
    return { hasClass, backdropFilter: bf };
  });

  // 2. Begin game and frame the street HUD cleanly (skip first-visit tutorial toast)
  await page.evaluate(() => {
    const g = window.__game;
    const sv = g.save();
    sv.seenHint = true;
    sv.seenStickHint = true;
    sv.settings.voice = false;
    sv.settings.auto = false;
    g.begin(false);
    g.chooseStory('people-of-the-elephant');
    // Place player on the village street looking north down the canal & houses
    g.player.place(0, -34, 0);
    g.player.yaw = Math.PI;
    g.cameraRig.snap();
    document.getElementById('toast')?.classList.remove('show');
    document.getElementById('banner')?.classList.remove('show');
  });
  await page.waitForTimeout(1400);
  await page.evaluate(() => {
    document.getElementById('toast')?.classList.remove('show');
    document.getElementById('banner')?.classList.remove('show');
  });
  await page.waitForTimeout(250);
  await shot('hud');

  // 3. Stories panel
  await page.evaluate(() => { window.__game.panel('stories'); });
  await waitVisible('#panel.show', 600);
  await shot('stories');
  await page.click('#panel .x');
  await page.waitForFunction(() => document.getElementById('panel')?.hidden === true, { timeout: 8000 });

  // 4. Settings panel (wait briefly for Quran.com reciters list to populate if online)
  await page.evaluate(() => { window.__game.panel('settings'); });
  await waitVisible('#panel.show', 400);
  await page.waitForFunction(() => (document.querySelectorAll('#panel select[name="reciter"] option').length > 1), { timeout: 4000 }).catch(() => {});
  await page.waitForTimeout(400);
  await shot('settings');
  await page.click('#panel .x');
  await page.waitForFunction(() => document.getElementById('panel')?.hidden === true, { timeout: 8000 });

  // 5. World map panel
  await page.evaluate(() => { window.__game.panel('map'); });
  await waitVisible('#panel.show', 700);
  await shot('map');
  await page.click('#panel .x');
  await page.waitForFunction(() => document.getElementById('panel')?.hidden === true, { timeout: 8000 });

  // 6. Start first encounter ("people-of-the-elephant") for dialogue -> verse -> lesson -> reward
  await page.evaluate(() => {
    const g = window.__game;
    const sv = g.save();
    sv.settings.voice = false;
    sv.settings.auto = false;
    if (!sv.opened.includes('people-of-the-elephant')) sv.opened.push('people-of-the-elephant');
    g.refreshNpcs();
    const npc = g.npcs.find(n => n.enc.id === 'people-of-the-elephant');
    g.player.place(npc.x + 2.1, npc.z, -Math.PI / 2);
    g.cameraRig.snap();
    g.startEncounter(npc);
  });
  await waitVisible('#dialogue.show', 500);

  // Step 0 is 'say' -> advance to Step 1 ('choice' with 2 options!)
  const choiceDeadline = Date.now() + 15000;
  while (Date.now() < choiceDeadline) {
    const n = await page.evaluate(() => document.querySelectorAll('#dialogue .choices.show button').length);
    if (n >= 2) break;
    await page.click('#dialogue .box', { force: true });
    await page.waitForTimeout(260);
  }
  await waitVisible('#dialogue .choices.show button:last-child', 600);
  await waitVisible('#dialogue .name', 400);
  await shot('dialogue');

  // Walk cleanly through the encounter until the Quran verse card opens
  // (choice steps pause briefly during spokenEnd(), so poll with a wall-clock deadline)
  const quranDeadline = Date.now() + 90000;
  while (Date.now() < quranDeadline) {
    const st = await page.evaluate(() => ({
      quran: document.getElementById('quran')?.classList.contains('show'),
      choices: document.querySelectorAll('#dialogue .choices.show button').length,
      nextVisible: !document.querySelector('#dialogue .next')?.hidden,
    }));
    if (st.quran) break;
    if (st.choices > 0) {
      await page.click('#dialogue .choices button:first-child', { force: true });
      await page.waitForTimeout(450);
    } else {
      await page.click('#dialogue .box', { force: true });
      await page.waitForTimeout(st.nextVisible ? 200 : 280);
    }
  }

  // 7. Verse card (wait for live Quran.com text & medallion; allow up to 15s)
  await waitVisible('#quran.show', 400);
  await page.waitForFunction(() => {
    const t = document.querySelector('#quran .q-text');
    return t && !t.classList.contains('loading') && t.textContent.trim().length > 4;
  }, { timeout: 15000 }).catch(() => console.warn(`  [${tag}] Quran.com text did not finish in 15s`));
  await page.waitForTimeout(900);
  await shot('verse');

  // Skip recitation to reach the lesson prompt ("What do we learn?")
  await page.click('#quran .q-skip', { force: true });
  await page.waitForFunction(() => document.getElementById('quran')?.hidden === true, { timeout: 10000 });
  await page.waitForTimeout(450);

  const lessonDeadline = Date.now() + 25000;
  while (Date.now() < lessonDeadline) {
    const ready = await page.evaluate(() => (
      document.getElementById('dialogue')?.hasAttribute('data-lesson') &&
      document.querySelectorAll('#dialogue .choices.show button').length > 0
    ));
    if (ready) break;
    await page.click('#dialogue .box', { force: true });
    await page.waitForTimeout(250);
  }
  await waitVisible('#dialogue .choices.show button:last-child', 600);
  await shot('lesson');

  // Answer the lesson question correctly -> praise -> reward card ("Knowledge Unlocked")
  await page.click('#dialogue .choices button:first-child', { force: true });
  await page.waitForTimeout(800);
  const rewardDeadline = Date.now() + 25000;
  while (Date.now() < rewardDeadline) {
    const open = await page.evaluate(() => document.getElementById('reward')?.classList.contains('show'));
    if (open) break;
    await page.click('#dialogue .box', { force: true });
    await page.waitForTimeout(260);
  }
  await waitVisible('#reward.show', 400);
  await page.waitForFunction(() => {
    const img = document.querySelector('#reward .medal img');
    return !img || (img.complete && img.naturalWidth > 0);
  }, { timeout: 8000 });
  await page.waitForTimeout(900);
  await shot('reward');

  // Dismiss reward cleanly before closing the context
  await page.evaluate(() => document.querySelector('#reward button')?.click());
  await page.waitForTimeout(300);

  await ctx.close();
  return { tag, glassState, pageErrors, failed404 };
}

async function auditNarrowAndTiers(browser, port) {
  const report = { overflow360: {}, tiers: {} };
  console.log('  [audit] starting 360px AR/EN/RU overflow + Lite glass fallback check...');

  // Check 360x780 width overflow across AR, EN, RU on title, HUD, stories, settings, map
  const ctx360 = await browser.newContext({ viewport: { width: 360, height: 780 }, deviceScaleFactor: 1, hasTouch: true, isMobile: true });
  const page = await ctx360.newPage();
  await page.goto(`http://127.0.0.1:${port}/?q=lite`, { waitUntil: 'domcontentloaded' });
  await waitReady(page);
  await page.evaluate(() => document.body.classList.add('touch'));

  // Verify Lite tier has NO backdrop-filter (solid fallback)
  const liteGlass = await page.evaluate(() => {
    const hasClass = document.body.classList.contains('q-glass');
    const obj = document.getElementById('objective');
    const bf = getComputedStyle(obj).backdropFilter || getComputedStyle(obj).webkitBackdropFilter || 'none';
    return { hasClass, backdropFilter: bf };
  });
  report.liteGlass = liteGlass;

  const checkOverflow = async (issues, label) => {
    const ov = await page.evaluate(() => {
      const vw = window.innerWidth;
      const docOv = document.documentElement.scrollWidth > vw + 1;
      const bad = [];
      for (const el of document.querySelectorAll('#title h1, #title nav button, #objective, #points, #dock, #panel .sheet, .st-tab, .story, .settings > label')) {
        const st = getComputedStyle(el);
        if (st.display === 'none' || st.visibility === 'hidden' || el.closest('[hidden]')) continue;
        const r = el.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) continue;
        if (r.left < -2 || r.right > vw + 2) bad.push({ tag: el.tagName, cls: el.className, id: el.id, left: Math.round(r.left), right: Math.round(r.right), vw });
      }
      return { docOv, bad };
    });
    if (ov.docOv || ov.bad.length) issues.push({ screen: label, ...ov });
  };

  // First check title screen overflow in AR, EN, and RU at 360px
  for (const lang of ['ar', 'en', 'ru']) {
    report.overflow360[lang] = [];
    await page.evaluate(() => document.getElementById('btn-settings')?.click());
    await page.waitForSelector('#panel.show select[name="lang"]', { timeout: 8000 });
    await page.selectOption('#panel select[name="lang"]', lang);
    await page.waitForTimeout(200);
    await page.evaluate(() => document.querySelector('#panel .x')?.click());
    await page.waitForFunction(() => document.getElementById('panel')?.hidden === true, { timeout: 8000 });
    await checkOverflow(report.overflow360[lang], 'title');
  }

  // Enter explore mode, then check HUD + stories + settings + map in AR, EN, RU at 360px
  await page.evaluate(() => {
    const sv = window.__game.save();
    sv.seenHint = true;
    sv.seenStickHint = true;
    window.__game.begin(false);
  });
  await page.waitForTimeout(600);

  for (const lang of ['ar', 'en', 'ru']) {
    await page.evaluate(() => { window.__game.panel('settings'); });
    await page.waitForSelector('#panel.show select[name="lang"]', { timeout: 8000 });
    await page.selectOption('#panel select[name="lang"]', lang);
    await page.waitForTimeout(200);
    await checkOverflow(report.overflow360[lang], 'settings');
    await page.evaluate(() => document.querySelector('#panel .x')?.click());
    await page.waitForFunction(() => document.getElementById('panel')?.hidden === true, { timeout: 8000 });

    await checkOverflow(report.overflow360[lang], 'hud');
    for (const p of ['stories', 'map']) {
      await page.evaluate(k => { window.__game.panel(k); }, p);
      await page.waitForSelector('#panel.show', { timeout: 8000 });
      await page.waitForTimeout(250);
      await checkOverflow(report.overflow360[lang], p);
      await page.evaluate(() => document.querySelector('#panel .x')?.click());
      await page.waitForFunction(() => document.getElementById('panel')?.hidden === true, { timeout: 8000 });
    }
  }
  console.log('  [audit] 360px overflow & touch targets done.');

  // Check touch targets >= 44px on 360px phone HUD
  report.touchTargets = await page.evaluate(() => {
    const small = [];
    for (const b of document.querySelectorAll('#dock button, #zoom button')) {
      if (b.hidden) continue;
      const r = b.getBoundingClientRect();
      if (r.width > 0 && (r.width < 43.5 || r.height < 43.5)) small.push({ id: b.id, open: b.dataset.open, zoom: b.dataset.zoom, w: Math.round(r.width), h: Math.round(r.height) });
    }
    return small;
  });
  await ctx360.close();

  // Check renderer.info (whole-frame calls + main-pass triangles) and __game.balance({ verify: true }) on Lite and High
  for (const tier of ['lite', 'high']) {
    console.log(`  [audit] checking tier=${tier}...`);
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
    const p = await ctx.newPage();
    const errs = [];
    p.on('pageerror', e => errs.push(e.message));
    await p.goto(`http://127.0.0.1:${port}/?q=${tier}`, { waitUntil: 'domcontentloaded' });
    await waitReady(p);
    await p.evaluate(() => {
      const g = window.__game;
      g.save().seenHint = true;
      g.save().seenStickHint = true;
      g.begin(false);
      g.player.place(0, -34, 0);
      g.player.yaw = Math.PI;
      g.cameraRig.snap();
    });
    await p.waitForTimeout(1200);
    const info = await p.evaluate(() => {
      const g = window.__game;
      const frameCalls = g.renderer.info.render.calls;
      const frameTris = g.renderer.info.render.triangles;
      // Measure main camera pass triangles without shadow-map pass (M4/M5 convention)
      const prevShadow = g.renderer.shadowMap.autoUpdate;
      const prevEnabled = g.renderer.shadowMap.enabled;
      g.renderer.shadowMap.autoUpdate = false;
      g.renderer.shadowMap.enabled = false;
      g.renderer.info.reset();
      g.renderer.render(g.scene, g.camera);
      const mainCalls = g.renderer.info.render.calls;
      const mainTris = g.renderer.info.render.triangles;
      g.renderer.shadowMap.enabled = prevEnabled;
      g.renderer.shadowMap.autoUpdate = prevShadow;
      for (const n of g.npcs) g.coins.ensure(n.enc.id);
      const bal = g.balance({ verify: true });
      const bad = bal.filter(row => !row.reached || row.coins < 20 || row.notWalkable > 0 || row.unreachable > 0);
      const minCoins = Math.min(...bal.map(row => row.coins));
      return { frameCalls, frameTris, mainCalls, mainTris, stories: bal.length, minCoins, bad };
    });
    report.tiers[tier] = { ...info, pageErrors: errs };
    console.log(`  [audit] tier=${tier}: mainCalls=${info.mainCalls} frameCalls=${info.frameCalls} mainTris=${info.mainTris} stories=${info.stories} minCoins=${info.minCoins} bad=${info.bad.length}`);
    await ctx.close();
  }
  return report;
}

const { server, port } = await startServer();
console.log(`Serving dist/ on http://127.0.0.1:${port}`);

const browser = await chromium.launch({
  executablePath: CHROME,
  headless: true,
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--no-sandbox'],
});

const auditOnly = process.argv.includes('--audit-only');
try {
  const desktop = auditOnly ? null : await captureViewport(browser, port, { tag: 'desktop', width: 1280, height: 720, touch: false, quality: 'high' });
  const phone = auditOnly ? null : await captureViewport(browser, port, { tag: 'phone', width: 390, height: 844, touch: true, quality: 'high' });
  const audit = await auditNarrowAndTiers(browser, port);
  console.log('\n=== M6 VERIFICATION SUMMARY ===');
  console.log(JSON.stringify({ desktop, phone, audit }, null, 2));
} finally {
  await browser.close();
  server.close();
}
