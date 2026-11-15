import { describe, expect, it } from "vitest";
import { cubicBezier, springEase } from "@/lib/ease";

describe("cubicBezier", () => {
  it("is the identity for the linear curve", () => {
    const linear = cubicBezier(0, 0, 1, 1);
    for (const x of [0, 0.1, 0.5, 0.9, 1]) expect(linear(x)).toBeCloseTo(x, 5);
  });
  it("matches known CSS values for ease-in-out", () => {
    const easeInOut = cubicBezier(0.42, 0, 0.58, 1);
    expect(easeInOut(0.5)).toBeCloseTo(0.5, 4);
    expect(easeInOut(0.25)).toBeLessThan(0.25);
    expect(easeInOut(0.75)).toBeGreaterThan(0.75);
  });
  it("spring curve starts at 0, ends at 1, rises monotonically and front-loads the motion", () => {
    expect(springEase(0)).toBe(0);
    expect(springEase(1)).toBe(1);
    let prev = 0;
    for (let i = 1; i <= 100; i++) {
      const y = springEase(i / 100);
      expect(y).toBeGreaterThanOrEqual(prev - 1e-9);
      prev = y;
    }
    expect(springEase(0.3)).toBeGreaterThan(0.6);
  });
  it("clamps outside 0 to 1", () => {
    expect(springEase(-1)).toBe(0);
    expect(springEase(2)).toBe(1);
  });
});
