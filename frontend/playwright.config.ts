import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  timeout: 45_000,
  expect: { timeout: 10_000 },
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL,
    locale: "pt-BR",
    timezoneId: "America/Manaus",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "desktop-firefox",
      use: { ...devices["Desktop Firefox"] },
    },
    {
      name: "mobile-firefox",
      use: { ...devices["iPhone 13"], browserName: "firefox" },
    },
  ],
  webServer: {
    command: "npm run dev -- --hostname 0.0.0.0",
    url: baseURL,
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
