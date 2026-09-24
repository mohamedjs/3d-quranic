import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// base './' so the built game runs from any sub-path (e.g. Apache at /old/3d-quranic/dist/)
export default defineConfig({
  base: './',
  plugins: [react()],
  build: { target: 'es2022', chunkSizeWarningLimit: 1500 },
});
