import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// base './' so the built game runs from any sub-path (e.g. Apache at /old/3d-quranic/dist/)
// Vendor code is split into long-lived chunks (three · react/r3f) that download in parallel
// and stay cached across game updates; post-processing and the Piper voice are lazy chunks.
export default defineConfig({
  base: './',
  plugins: [react()],
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
