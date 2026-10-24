import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    // The SPA calls relative /api paths; in development Vite forwards them to FastAPI.
    proxy: { "/api": "http://localhost:8000" }
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"]
  }
});
