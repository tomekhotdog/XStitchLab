import { defineConfig } from 'vite';

const backendPort = process.env.BACKEND_PORT || 8000;

export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: `http://127.0.0.1:${backendPort}`,
        changeOrigin: true,
      },
    },
  },
});
