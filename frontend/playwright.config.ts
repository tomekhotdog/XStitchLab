import { defineConfig, devices } from '@playwright/test';
import { DESIGNS_DIR } from './e2e/paths';

/**
 * One smoke test against real servers on their own ports (backend 8001, Vite 5174) so a running
 * dev session on 8000/5173 is never touched. The backend serves a throwaway copy of one design
 * (see e2e/global-setup.ts), so saving in the test never writes to `designs/`.
 */
export default defineConfig({
  testDir: 'e2e',
  globalSetup: './e2e/global-setup.ts',
  timeout: 120_000,
  expect: { timeout: 20_000 },
  retries: 0,
  workers: 1,
  use: { baseURL: 'http://localhost:5174' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: 'uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8001',
      cwd: '..',
      url: 'http://127.0.0.1:8001/api/health',
      env: { XSTITCH_DESIGNS_DIR: DESIGNS_DIR },
      timeout: 180_000,
      reuseExistingServer: false,
    },
    {
      command: 'npm run dev -- --port 5174 --strictPort',
      env: { BACKEND_PORT: '8001' },
      url: 'http://localhost:5174',
      timeout: 180_000,
      reuseExistingServer: false,
    },
  ],
});
