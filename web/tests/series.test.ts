import { describe, expect, it } from "vitest";
import { CARD_SURFACE, CHART_COLOR, REFERENCE_GRAY } from "@/lib/chartColors";
import {
  type Point,
  areaPath,
  buildScales,
  cursorMs,
  dateMs,
  formatDelta,
  formatShortDate,
  formatValue,
  isoFromMs,
  linePath,
  nearestIndex,
  valueAt,
} from "@/lib/series";

const pts: Point[] = [
  { t: "2026-06-17", v: -13 },
  { t: "2026-06-29", v: -15 },
  { t: "2026-07-11", v: -19 },
];
const frame = { width: 200, height: 80, padLeft: 4, padRight: 10, padTop: 8, padBottom: 6 };

describe("valueAt and nearestIndex", () => {
  it("interpolates linearly between points and clamps outside", () => {
    expect(valueAt(pts, dateMs("2026-06-17"))).toBe(-13);
    expect(valueAt(pts, dateMs("2026-06-23"))).toBeCloseTo(-14, 6);
    expect(valueAt(pts, dateMs("2026-07-11"))).toBe(-19);
    expect(valueAt(pts, dateMs("2025-01-01"))).toBe(-13);
    expect(valueAt(pts, dateMs("2030-01-01"))).toBe(-19);
  });
  it("snaps to the nearest point", () => {
    expect(nearestIndex(pts, dateMs("2026-06-18"))).toBe(0);
    expect(nearestIndex(pts, dateMs("2026-06-27"))).toBe(1);
    expect(nearestIndex(pts, dateMs("2026-12-01"))).toBe(2);
  });
});

describe("scales and paths", () => {
  const series = { points: pts, reference: { label: "ref", points: [{ t: "2026-06-17", v: -12 }, { t: "2026-07-11", v: -12 }] } };
  const s = buildScales(series, frame);
  it("maps the date range onto the plot width and inverts exactly", () => {
    expect(s.x(dateMs("2026-06-17"))).toBeCloseTo(frame.padLeft, 6);
    expect(s.x(dateMs("2026-07-11"))).toBeCloseTo(frame.width - frame.padRight, 6);
    expect(s.xInverse(s.x(dateMs("2026-06-29")))).toBeCloseTo(dateMs("2026-06-29"), 3);
  });
  it("puts higher values higher on screen and keeps both series inside the plot", () => {
    expect(s.y(-12)).toBeLessThan(s.y(-19));
    for (const v of [-19, -13, -12]) {
      expect(s.y(v)).toBeGreaterThanOrEqual(frame.padTop);
      expect(s.y(v)).toBeLessThanOrEqual(frame.height - frame.padBottom);
    }
  });
  it("pads a flat series instead of dividing by zero", () => {
    const flat = buildScales({ points: [{ t: "2026-06-17", v: 5 }, { t: "2026-06-29", v: 5 }] }, frame);
    expect(Number.isFinite(flat.y(5))).toBe(true);
  });
  it("writes one move and a line to each later point, and closes the area", () => {
    const d = linePath(pts, s);
    expect(d.startsWith("M")).toBe(true);
    expect(d.match(/L/g)).toHaveLength(2);
    const area = areaPath(pts, s, 74);
    expect(area.endsWith("Z")).toBe(true);
    expect(area).toContain(" 74");
  });
  it("sweeps the cursor across the date range with progress", () => {
    expect(cursorMs(s, 0)).toBe(s.t0);
    expect(cursorMs(s, 1)).toBe(s.t1);
    expect(cursorMs(s, 5)).toBe(s.t1);
    expect(isoFromMs(cursorMs(s, 0.5))).toBe("2026-06-29");
  });
});

describe("formatting", () => {
  it("formats values with unit-appropriate decimals and a true minus", () => {
    expect(formatValue(-13.24, "dB")).toBe("−13.2 dB");
    expect(formatValue(7648.4, "ha")).toBe("7,648 ha");
    expect(formatValue(-8.9, "cm")).toBe("−8.9 cm");
  });
  it("signs deltas, and shows no sign on zero", () => {
    expect(formatDelta(2.14, "dB")).toBe("+2.1 dB");
    expect(formatDelta(-5.5, "dB")).toBe("−5.5 dB");
    expect(formatDelta(0.01, "dB")).toBe("0.0 dB");
  });
  it("formats short dates in UTC", () => {
    expect(formatShortDate("2026-06-17")).toBe("Jun 17");
    expect(formatShortDate("2026-10-03")).toBe("Oct 3");
  });
});

// Re-checks the dataviz skill's dark-mode thresholds for the chart tokens, so editing a hex cannot
// silently break them. (The skill's validate_palette.js is the authority; this guards regressions.)
describe("chart color tokens", () => {
  const lin = (c: number) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
  const rgb = (hex: string) => [1, 3, 5].map((i) => lin(parseInt(hex.slice(i, i + 2), 16) / 255));
  const luminance = (hex: string) => {
    const [r, g, b] = rgb(hex);
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  };
  const contrast = (a: string, b: string) => {
    const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
    return (hi + 0.05) / (lo + 0.05);
  };
  const oklchL = (hex: string) => {
    const [R, G, B] = rgb(hex);
    const l = Math.cbrt(0.4122214708 * R + 0.5363325363 * G + 0.0514459929 * B);
    const m = Math.cbrt(0.2119034982 * R + 0.6806995451 * G + 0.1073969566 * B);
    const s = Math.cbrt(0.0883024619 * R + 0.2817188376 * G + 0.6299787005 * B);
    return 0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s;
  };
  for (const [theme, color] of Object.entries(CHART_COLOR)) {
    it(`${theme} line is inside the dark lightness band and has 3:1 contrast on the card`, () => {
      expect(oklchL(color)).toBeGreaterThanOrEqual(0.48);
      expect(oklchL(color)).toBeLessThanOrEqual(0.67);
      expect(contrast(color, CARD_SURFACE)).toBeGreaterThanOrEqual(3);
    });
  }
  it("the reference gray has 3:1 contrast on the card and is darker than every chart line", () => {
    expect(contrast(REFERENCE_GRAY, CARD_SURFACE)).toBeGreaterThanOrEqual(3);
    for (const color of Object.values(CHART_COLOR)) expect(oklchL(REFERENCE_GRAY)).toBeLessThan(oklchL(color));
  });
});
