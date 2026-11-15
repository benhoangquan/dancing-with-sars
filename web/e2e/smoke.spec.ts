import { readFileSync, readdirSync } from "node:fs";
import { expect, test, type Page } from "@playwright/test";

const SCREENS = "e2e/__screens__";
const slugs = readdirSync("public/chapters")
  .filter((f) => f.endsWith(".json"))
  .map((f) => f.replace(".json", ""));
const manifest = (slug: string) => JSON.parse(readFileSync(`public/chapters/${slug}.json`, "utf8"));

/** Scroll so the viewport centre line sits `fraction` of the way down beat `beat` of the open place. */
async function scrollToBeat(page: Page, beat: number, fraction = 0.3) {
  await page.evaluate(
    ([b, f]) => {
      const el = document.querySelector<HTMLElement>(`[data-section="beat"][data-beat="${b}"]`);
      if (!el) throw new Error(`no beat ${b}`);
      const r = el.getBoundingClientRect();
      window.scrollTo({ top: window.scrollY + r.top - window.innerHeight / 2 + r.height * f, behavior: "instant" });
    },
    [beat, fraction] as const,
  );
}

const scene = (page: Page) => page.evaluate(() => document.documentElement.dataset.scene);

async function toHotspot(page: Page) {
  await page.goto("/?debug");
  for (let i = 0; i < 14; i++) await page.mouse.wheel(0, 400);
  await expect.poll(() => scene(page)).toBe("HOTSPOT_GLOBE");
}

test("the hero renders the globe with no console errors, then settles into the hotspot globe", async ({ page }) => {
  const problems: string[] = [];
  page.on("console", (m) => m.type() === "error" && problems.push(m.text()));
  page.on("pageerror", (e) => problems.push(String(e)));
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: "Dancing with the SARs" })).toBeVisible();
  await expect(page.locator(".globe-root .maplibregl-canvas")).toBeVisible();
  await expect(page.getByRole("button", { name: "Back to the globe" })).toHaveCount(0);
  await page.waitForLoadState("networkidle");
  expect(problems).toEqual([]);
  await toHotspot(page);
  expect(await page.evaluate(() => getComputedStyle(document.documentElement).overflow)).toBe("hidden");
  await expect(page.getByRole("button", { name: "Back to the globe" })).toBeDisabled();
  for (const slug of slugs) await expect(page.getByRole("button", { name: new RegExp(`^Open ${manifest(slug).aoi.placeName.split(",")[0]}`) })).toHaveCount(1);
});

test("a pin opens its place, the act I flyover hands over at the opening camera, and the globe button returns", async ({ page }) => {
  await toHotspot(page);
  await page.getByRole("button", { name: /^Open Rondônia/ }).click();
  await expect(page).toHaveURL(/#place=rondonia/);
  await expect.poll(() => scene(page)).toBe("PLACE_CHAPTER");
  await expect(page.getByRole("button", { name: "Replay 20s" })).toBeVisible();
  await expect(page.locator(".stage-root")).toHaveAttribute("data-act", "1");
  await scrollToBeat(page, 1);
  await expect(page.locator(".stage-root")).toHaveAttribute("data-act", "2");
  const opening = manifest("rondonia").openingCamera;
  await expect
    .poll(
      () =>
        page.evaluate(() => {
          const a = (window as unknown as { __sar?: { a: { getCenter: () => { lng: number; lat: number }; getZoom: () => number; getPitch: () => number } } }).__sar?.a;
          if (!a) return null;
          const c = a.getCenter();
          return [c.lng, c.lat, a.getZoom(), a.getPitch()];
        }),
      { timeout: 10_000 },
    )
    .toEqual([expect.closeTo(opening.center[0], 4), expect.closeTo(opening.center[1], 4), expect.closeTo(opening.zoom, 3), expect.closeTo(opening.pitch, 2)]);
  await page.getByRole("button", { name: "Back to the globe" }).click();
  await expect.poll(() => scene(page)).toBe("HOTSPOT_GLOBE");
  await expect(page).not.toHaveURL(/#place=/);
});

test("the swipe divider moves with the keyboard and dims the beat card while dragged", async ({ page }) => {
  await page.goto("/?debug#place=okanagan");
  await scrollToBeat(page, 2);
  const slider = page.getByRole("slider", { name: "Before and after divider" });
  await expect(slider).toHaveAttribute("aria-valuenow", "50");
  await slider.focus();
  await page.keyboard.press("ArrowLeft");
  await expect(slider).toHaveAttribute("aria-valuenow", "45");
  const card = page.locator('[data-beat-card="scar"]');
  const box = (await slider.boundingBox())!;
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(box.x + 200, box.y + box.height / 2);
  await expect(card).toHaveCSS("opacity", "0.25");
  await page.mouse.up();
  await expect(card).toHaveCSS("opacity", "1");
});

test("a landmark popover opens and closes after the page scrolls more than 40 px", async ({ page }) => {
  await page.goto("/?debug#place=rondonia");
  await scrollToBeat(page, 1, 0.2);
  const pin = page.getByRole("button", { name: "Largest new clearing: ground view" });
  await expect(pin).toBeVisible();
  await pin.click();
  await expect(page.getByRole("dialog", { name: "Largest new clearing" })).toBeVisible();
  await expect(page.getByText("HV after")).toBeVisible();
  await page.mouse.wheel(0, 60);
  await expect(page.getByRole("dialog", { name: "Largest new clearing" })).toHaveCount(0);
});

test("Take Action opens the sheet with https links, the city tab redraws per city, and Escape closes it", async ({ page }) => {
  await page.goto("/?debug#place=okanagan");
  await scrollToBeat(page, 4, 0.4);
  await page.getByRole("button", { name: "Take Action" }).click();
  const sheet = page.getByRole("dialog");
  await expect(sheet).toBeVisible();
  for (const href of await sheet.locator("a").evaluateAll((as) => as.map((a) => (a as HTMLAnchorElement).href))) expect(href).toMatch(/^https:\/\//);
  await page.getByRole("tab", { name: "Act Where You Live" }).click();
  const figure = page.locator("svg[data-city]");
  await expect(figure.locator("[data-footprint]")).toHaveCount(1);
  const first = await figure.locator("path").first().getAttribute("d");
  await page.getByRole("radio", { name: "Jakarta" }).click();
  await expect(figure).toHaveAttribute("data-city", "jakarta");
  await expect.poll(() => figure.locator("path").first().getAttribute("d")).not.toBe(first);
  await page.keyboard.press("Escape");
  await expect(sheet).toHaveCount(0);
});

test("the discovery sheet lists every place and the places checked without a chapter", async ({ page }) => {
  await toHotspot(page);
  await page.getByRole("button", { name: "Take Action" }).click();
  const sheet = page.getByRole("dialog");
  await expect(sheet.getByRole("button", { name: "Open the story" })).toHaveCount(slugs.length);
  await expect(sheet.getByText("Checked, no chapter yet")).toBeVisible();
  await sheet.getByRole("button", { name: "Open the story" }).first().click();
  await expect.poll(() => scene(page)).toBe("PLACE_CHAPTER");
});

test("sound stays off until the reader turns it on", async ({ page }) => {
  await page.goto("/?debug#place=demak");
  const toggle = page.getByRole("switch", { name: /Sound/ });
  await expect(toggle).toHaveAttribute("aria-checked", "false");
  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-checked", "true");
});

test("a COG tile request is served as a partial (206) response", async ({ page }) => {
  const ranged = page.waitForResponse((r) => r.url().endsWith(".tif") && r.status() === 206);
  await page.goto("/?debug#place=demak");
  expect((await ranged).status()).toBe(206);
});

test("screenshots for review", async ({ page }) => {
  test.setTimeout(480_000);
  await page.goto("/");
  await page.waitForTimeout(2500);
  await page.screenshot({ path: `${SCREENS}/01-hero.png` });
  await toHotspot(page);
  await page.waitForTimeout(2500);
  await page.screenshot({ path: `${SCREENS}/02-hotspot.png` });
  for (const slug of slugs) {
    await page.goto(`/?debug#place=${slug}`);
    await page.waitForTimeout(3500);
    await page.screenshot({ path: `${SCREENS}/${slug}-act1.png` });
    for (const beat of [1, 2, 3, 4]) {
      await scrollToBeat(page, beat, 0.4);
      await page.waitForTimeout(3000);
      await page.screenshot({ path: `${SCREENS}/${slug}-beat${beat}.png` });
    }
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/?debug#place=demak");
  await scrollToBeat(page, 2, 0.4);
  await page.waitForTimeout(3000);
  await page.screenshot({ path: `${SCREENS}/mobile-demak.png` });
});
