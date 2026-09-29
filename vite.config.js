import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import pwa from './tools/vite-pwa.js';
import { execSync } from 'node:child_process';
import pkg from './package.json' with { type: 'json' };

// build id for the statistics rows: Railway / GitHub Actions give the commit in env vars, locally ask git
const sha = (process.env.RAILWAY_GIT_COMMIT_SHA || process.env.GITHUB_SHA || '').slice(0, 7) || (() => { try { return execSync('git rev-parse --short HEAD', { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim(); } catch { return 'nogit'; } })();

// base './' so the built game runs from any sub-path (e.g. Apache at /old/3d-quranic/dist/)
// Vendor code is split into long-lived chunks (three · react/r3f) that download in parallel
// and stay cached across game updates; post-processing and the Piper voice are lazy chunks.
// tools/vite-pwa.js emits the service worker (offline play) with this build's precache list.
export default defineConfig({
  base: './',
  plugins: [react(), pwa()],
  define: { __APP_VERSION__: JSON.stringify(`${pkg.version}+${sha}`) },   // tagged on every statistics row
  build: {
    target: 'es2022', chunkSizeWarningLimit: 900,
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            { name: 'three', test: /node_modules[\\/]three[\\/]/, priority: 20 },
            { name: 'react', test: /node_modules[\\/](react|react-dom|scheduler|@react-three[\\/]fiber|@react-three[\\/]drei|zustand|its-fine|suspend-react|react-use-measure|use-sync-external-store)[\\/]/, priority: 10 },
          ],
        },
      },
    },
  },
});
