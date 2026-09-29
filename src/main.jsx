import { createRoot } from 'react-dom/client';
import './game/ui/style.css';
import './game/ui/clay.css';
import './pwa/pwa.js';          // listens for beforeinstallprompt from the first moment
import { resolveQuality } from './game/systems/quality.js';

// The quality level is settled here, on the loading screen, BEFORE anything of the world is
// built: GPU guess + device age (pre-2021 → Low/Lite) + a saved choice / remembered Lite
// (systems/store.js). The game module (and with it the store) is only loaded afterwards, so
// the world is built once, at the right level.
const msg = document.querySelector('#loading p'), building = msg?.textContent;
if (msg) msg.textContent = 'نجهّز العالم لجهازك… · Preparing the world for your device…';
resolveQuality()
  .catch(e => console.warn('[quality]', e))
  .then(() => import('./game/components/Game.jsx'))
  .then(({ Game }) => {
    if (msg && building) msg.textContent = building;
    createRoot(document.getElementById('root')).render(<Game />);
  })
  .catch(e => { if (msg) { msg.textContent = 'Something went wrong while loading — تعذّر تحميل اللعبة:\n' + (e?.message || e); msg.style.whiteSpace = 'pre-line'; } });
