import { describe, expect, it } from "vitest";
import { colorFragment } from "@/lib/mapLayers";
import { SAR_DIVERGING_DARK, SAR_SPEED_DARK, customColorFunction, isCustomRamp, rampColor } from "@/lib/ramps";
import type { Layer } from "@/types/chapter";

const render = (scheme: string): Layer["render"] => ({ type: "ramp", scheme, domain: [-15, 15], unit: "cm" });

describe("custom dark diverging ramp", () => {
  const stops = SAR_DIVERGING_DARK;
  it("hits the end stops at the ends of the domain and clips beyond", () => {
    expect(rampColor(stops, [-15, 15], -15)).toEqual([255, 122, 89, 255]);
    expect(rampColor(stops, [-15, 15], 15)).toEqual([100, 181, 255, 255]);
    expect(rampColor(stops, [-15, 15], -99)).toEqual([255, 122, 89, 255]);
    expect(rampColor(stops, [-15, 15], 99)).toEqual([100, 181, 255, 255]);
  });
  it("is a dark neutral at zero, not white", () => {
    const [r, g, b, a] = rampColor(stops, [-15, 15], 0);
    expect([r, g, b, a]).toEqual([44, 44, 46, 255]);
  });
  it("gets brighter with magnitude on both sides", () => {
    const lum = (v: number) => rampColor(stops, [-15, 15], v).slice(0, 3).reduce((x, y) => x + y, 0);
    expect(lum(-15)).toBeGreaterThan(lum(-7.5));
    expect(lum(-7.5)).toBeGreaterThan(lum(0));
    expect(lum(15)).toBeGreaterThan(lum(7.5));
    expect(lum(7.5)).toBeGreaterThan(lum(0));
  });
  it("makes NaN transparent", () => {
    expect(rampColor(stops, [-15, 15], Number.NaN)).toEqual([0, 0, 0, 0]);
  });
  it("writes into the protocol's color array and is only used for project ramps", () => {
    const fn = customColorFunction(render("SarDivergingDark"));
    const color = new Uint8ClampedArray(4);
    fn?.([15], color);
    expect([...color]).toEqual([100, 181, 255, 255]);
    expect(customColorFunction(render("BrewerRdBu11"))).toBeUndefined();
    expect(customColorFunction({ type: "rgba" })).toBeUndefined();
  });
  it("has no #color fragment, while built-in ramps still do", () => {
    expect(isCustomRamp(render("SarDivergingDark"))).toBe(true);
    expect(colorFragment(render("SarDivergingDark"))).toBe("");
    expect(colorFragment(render("BrewerRdBu11"))).toBe("#color:BrewerRdBu11,-15,15,c");
  });
});

describe("custom dark speed ramp", () => {
  const domain: [number, number] = [0, 40];
  it("is near-black for still ground and brightest for the fastest ice, and brightens steadily", () => {
    const lum = (v: number) => rampColor(SAR_SPEED_DARK, domain, v).slice(0, 3).reduce((a, b) => a + b, 0);
    expect(rampColor(SAR_SPEED_DARK, domain, 0)).toEqual([11, 29, 51, 255]);
    expect(rampColor(SAR_SPEED_DARK, domain, 40)).toEqual([244, 254, 255, 255]);
    for (const [a, b] of [[0, 10], [10, 20], [20, 30], [30, 40]]) expect(lum(b)).toBeGreaterThan(lum(a));
    expect(rampColor(SAR_SPEED_DARK, domain, 400)).toEqual([244, 254, 255, 255]);
  });
  it("is registered as a project ramp", () => {
    const render: Layer["render"] = { type: "ramp", scheme: "SarSpeedDark", domain, unit: "m/day" };
    expect(isCustomRamp(render)).toBe(true);
    expect(colorFragment(render)).toBe("");
    expect(customColorFunction(render)).toBeDefined();
  });
});
