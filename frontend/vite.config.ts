import { loadEnv } from "vite";
import { configDefaults, defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig(({ command, mode }) => {
  // Only the dev server: tests stub these themselves, and Vercel builds set VITE_DEMO_*.
  if (command === "serve" && mode === "development") showSeededDemoLogins(mode);
  return {
    plugins: [react()],
    server: {
      // The SPA calls relative /api paths; in development Vite forwards them to FastAPI.
      proxy: { "/api": "http://localhost:8000" }
    },
    test: {
      environment: "jsdom",
      setupFiles: ["./src/test/setup.ts"],
      // Playwright owns e2e/; its specs would otherwise match Vitest's *.spec.ts pattern.
      exclude: [...configDefaults.exclude, "e2e/**"]
    }
  };
});

/**
 * List the logins `make seed-demo` creates on the local sign-in page, as the deployed one
 * lists the published ones: copy DEMO_* from the root .env to VITE_DEMO_* unless set.
 * Vite reads VITE_* from process.env after this config runs.
 */
function showSeededDemoLogins(mode: string) {
  for (const [key, value] of Object.entries(loadEnv(mode, "..", "DEMO_"))) {
    process.env[`VITE_${key}`] ??= value;
  }
}
