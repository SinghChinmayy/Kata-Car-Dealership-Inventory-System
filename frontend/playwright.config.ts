import { randomBytes } from "node:crypto";
import { defineConfig, devices } from "@playwright/test";
import { E2E_ADMIN, E2E_DATABASE_URL } from "./e2e/env";

// Explicit settings so the run never depends on (or touches) the developer's .env database.
const apiEnv = {
  DATABASE_URL: E2E_DATABASE_URL,
  JWT_SECRET: randomBytes(32).toString("hex"),
  INITIAL_ADMIN_EMAIL: E2E_ADMIN.email,
  INITIAL_ADMIN_PASSWORD: E2E_ADMIN.password,
  ALLOWED_CORS_ORIGINS: "http://localhost:5173"
};

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://localhost:5173",
    trace: "retain-on-failure"
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  // Never reuse a running server: an API already on :8000 would be pointed at the dev database.
  webServer: [
    {
      command: "./e2e/start-api.sh",
      url: "http://127.0.0.1:8000/health",
      env: apiEnv,
      reuseExistingServer: false,
      timeout: 120_000
    },
    {
      command: "npm run dev -- --port 5173 --strictPort",
      url: "http://localhost:5173",
      reuseExistingServer: false,
      timeout: 60_000
    }
  ]
});
