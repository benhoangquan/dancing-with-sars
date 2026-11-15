import { expect, test, type Page } from "@playwright/test";

const SCREENS = "e2e/__screens__";

/** Scroll so the viewport center line sits `fraction` of the way down the given beat. */
async function scrollToBeat(page: Page, chapter: number, beat: number, fraction = 0.3) {
  await page.evaluate(
    ([c, b, f]) => {
      const el = document.querySelector<HTMLElement>(`[data-section="beat"][data-chapter="${c}"][data-beat="${b}"]`);
      if (!el) throw new Error(`no beat ${c}:${b}`);
      const r = el.getBoundingClientRect();
      window.scrollTo({ top: window.scrollY + r.top - window.innerHeight / 2 + r.height * f, behavior: "instant" });
    },
    [chapter, beat, fraction] as const,
  );
}

const mode = (page: Page, name: string) => page.getByRole("radio", { name });

test("loads with no console errors and shows the three chapters", async ({ page }) => {
  const problems: string[] = [];
  page.on("console", (m) => m.type() === "error" && problems.push(m.text()));
  page.on("pageerror", (e) => problems.push(String(e)));
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: "Dancing with the SARs" })).toBeVisible();
  await expect(page.locator('[data-section="header"] h2')).toHaveCount(3);
  await expect(page.locator(".maplibregl-canvas").first()).toBeVisible();
  await page.waitForLoadState("networkidle");
  expect(problems).toEqual([]);
});

test("the segmented control follows the beat, and a click pins a mode", async ({ page }) => {
  await page.goto("/");
  await scrollToBeat(page, 0, 0);
  await expect(mode(page, "Flyover")).toBeChecked();
  await scrollToBeat(page, 0, 2); // "The fishbone spreads" is a radar beat
  await expect(mode(page, "Radar Compare")).toBeChecked();
  await expect(page.locator(".stage-root")).toHaveAttribute("data-mode", "radar");
  await mode(page, "Split").click();
  await expect(mode(page, "Split")).toBeChecked();
  await expect(page.locator(".stage-root")).toHaveAttribute("data-mode", "split");
  await scrollToBeat(page, 0, 1); // pin survives a beat change inside the chapter
  await expect(mode(page, "Split")).toBeChecked();
  await scrollToBeat(page, 1, 0); // and clears when the chapter changes
  await expect(mode(page, "Flyover")).toBeChecked();
});

test("the swipe divider moves with the keyboard", async ({ page }) => {
  await page.goto("/");
  await scrollToBeat(page, 0, 2);
  const slider = page.getByRole("slider", { name: "Before and after divider" });
  await expect(slider).toHaveAttribute("aria-valuenow", "50");
  await slider.focus();
  await page.keyboard.press("ArrowLeft");
  await expect(slider).toHaveAttribute("aria-valuenow", "45");
  await page.keyboard.press("Home");
  await expect(slider).toHaveAttribute("aria-valuenow", "0");
  await page.keyboard.press("End");
  await expect(slider).toHaveAttribute("aria-valuenow", "100");
});

test("a COG tile request is served as a partial (206) response", async ({ page }) => {
  const partial = page.waitForResponse((r) => r.url().endsWith(".tif") && r.status() === 206);
  await page.goto("/");
  await scrollToBeat(page, 0, 2);
  expect((await partial).headers()["content-range"]).toMatch(/^bytes \d+-\d+\/\d+$/);
});

test("the action drawer opens with https links and closes on Escape", async ({ page }) => {
  await page.goto("/");
  const trigger = page.getByRole("button", { name: /Take action · Rondônia/ });
  await trigger.click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  const links = dialog.locator('a[target="_blank"]');
  expect(await links.count()).toBeGreaterThanOrEqual(4);
  for (const href of await links.evaluateAll((els) => els.map((e) => e.getAttribute("href")))) expect(href).toMatch(/^https:\/\//);
  for (const rel of await links.evaluateAll((els) => els.map((e) => e.getAttribute("rel")))) expect(rel).toContain("noopener");
  await expect(dialog.getByText("Illustrative data").first()).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(trigger).toBeFocused();
});

test("the expanded legend never covers the call-to-action button", async ({ page }) => {
  for (const viewport of [{ width: 1440, height: 900 }, { width: 1280, height: 720 }]) {
    await page.setViewportSize(viewport);
    await page.goto("/");
    await scrollToBeat(page, 1, 2);
    await page.getByRole("button", { name: /Yellow-green/ }).click();
    await expect(page.locator("#legend-panel")).toBeVisible();
    await page.waitForTimeout(800); // let the panel finish growing
    const cta = await page.getByRole("button", { name: /Take action/ }).boundingBox();
    const column = await page.getByRole("complementary", { name: "Radar readout" }).boundingBox();
    expect(column!.y).toBeGreaterThanOrEqual(cta!.y + cta!.height);
  }
});

test("a COG that fails to load falls back to its PNG preview", async ({ page }) => {
  await page.route("**/data/rondonia/sar_before.tif", (route) => route.abort());
  const warnings: string[] = [];
  page.on("console", (m) => m.type() === "warning" && warnings.push(m.text()));
  await page.goto("/?debug");
  await scrollToBeat(page, 0, 2);
  await expect.poll(() => warnings.some((w) => w.includes("sar_before") && w.includes("PNG preview"))).toBe(true);
  const kind = () => page.evaluate(() => (window as unknown as { __sar: { a: { getSource(id: string): { type: string } | undefined } } }).__sar.a.getSource("src-sar_before")?.type);
  await expect.poll(kind).toBe("image");
});

test("screenshots for review", async ({ page }) => {
  await page.goto("/");
  await page.waitForLoadState("networkidle");
  const shots: [string, number, number, number][] = [
    ["01-hero", -1, 0, 0],
    ["02-rondonia-flyover", 0, 0, 0.6],
    ["03-rondonia-radar", 0, 2, 0.5],
    ["04-rondonia-split", 0, 3, 0.5],
    ["05-okanagan-smoke", 1, 1, 0.5],
    ["06-okanagan-scar", 1, 2, 0.5],
    ["07-sanjoaquin-bowl", 2, 2, 0.5],
  ];
  for (const [name, c, b, f] of shots) {
    if (c < 0) await page.evaluate(() => window.scrollTo(0, 0));
    else await scrollToBeat(page, c, b, f);
    await page.waitForTimeout(3500); // let the spring settle and tiles load
    await page.screenshot({ path: `${SCREENS}/${name}.png` });
  }

  // Open states: the expanded legend and the action drawer.
  await scrollToBeat(page, 1, 2, 0.5);
  await page.getByRole("button", { name: /Yellow-green/ }).click();
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `${SCREENS}/08-legend-open.png` });
  await page.getByRole("button", { name: /Yellow-green/ }).click();
  await page.getByRole("button", { name: /Take action · Okanagan/ }).click();
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `${SCREENS}/09-drawer.png` });
  await page.keyboard.press("Escape");

  // A phone-sized viewport.
  await page.setViewportSize({ width: 390, height: 844 });
  for (const [name, c, b] of [["10-mobile-radar", 0, 2], ["11-mobile-bowl", 2, 2]] as const) {
    await scrollToBeat(page, c, b, 0.5);
    await page.waitForTimeout(3500);
    await page.screenshot({ path: `${SCREENS}/${name}.png` });
  }
});
