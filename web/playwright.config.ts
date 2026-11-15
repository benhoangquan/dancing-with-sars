import { defineConfig } from "@playwright/test";

// Smoke tests run against the static export in out/ (run `npm run build` first). SwiftShader gives
// headless Chromium a software WebGL context for the maps. The browser must not see DISPLAY or
// WAYLAND_DISPLAY: when they point at an X server it cannot reach, ANGLE's SwiftShader backend fails
// with "xcb_connect() failed" and WebGL is unavailable. CI machines have neither, so this changes nothing there.
const env = { ...process.env };
delete env.DISPLAY;
delete env.WAYLAND_DISPLAY;

export default defineConfig({
  testDir: "e2e",
  timeout: 90_000,
  expect: { timeout: 15_000 },
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://localhost:4173",
    viewport: { width: 1440, height: 900 },
    launchOptions: { env, args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] },
  },
  webServer: {
    command: "npx serve out -l 4173 --no-clipboard",
    url: "http://localhost:4173",
    reuseExistingServer: true,
    timeout: 60_000,
  },
});
