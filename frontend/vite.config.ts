import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import { defineConfig } from 'vite';

// Served under the /legalEdge subpath in production (nginx strips the prefix,
// Vite's `base` makes every built asset URL absolute under /legalEdge/). Because
// `apiBase` (src/lib/api.ts) is derived from import.meta.env.BASE_URL, this base
// also ties the API prefix to /legalEdge/api/... with no code change. The Gemini
// key never reaches the browser; this SPA is a read-only monitoring dashboard.
export default defineConfig(() => {
  return {
    base: '/legalEdge/',
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    server: {
      // HMR is disabled in AI Studio via DISABLE_HMR env var.
      hmr: process.env.DISABLE_HMR !== 'true',
    },
  };
});
