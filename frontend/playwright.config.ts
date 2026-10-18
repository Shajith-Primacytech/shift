import { defineConfig } from "@playwright/test";
const frontendPort = process.env.SHIFT_E2E_FRONTEND_PORT || "3000";
const apiPort = process.env.SHIFT_E2E_API_PORT || "8000";
const baseURL = `http://127.0.0.1:${frontendPort}`;
export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  use: {
    baseURL,
    viewport: { width: 1440, height: 1000 },
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: "cd ../backend && uv run --no-sync python -m tests.e2e_server",
      env: {
        SHIFT_E2E_LIVE: "0",
        SHIFT_E2E_API_PORT: apiPort,
        SHIFT_CORS_ORIGINS: JSON.stringify([baseURL]),
      },
      url: `http://127.0.0.1:${apiPort}/api/v1/health`,
      reuseExistingServer: false,
    },
    {
      command: `npm run start -- --port ${frontendPort}`,
      url: baseURL,
      reuseExistingServer: false,
    },
  ],
});
