import { defineConfig, devices } from "@playwright/test";

// Fase 3 — replay determinístico (sem modelo). Mesma config local e CI.
export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? "blob" : "html",
  use: {
    baseURL: process.env.TARGET_URL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
});
