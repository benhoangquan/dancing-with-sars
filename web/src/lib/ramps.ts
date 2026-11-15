// Project color ramps drawn in the browser by a custom color function for the COG protocol.
// ColorBrewer ramps use the protocol's own `#color:` fragment; ramps listed here are not in that set.
import type { Layer } from "@/types/chapter";

type Render = Layer["render"];
export type Rgba = [number, number, number, number];

/** Diverging ramp for a dark stage: dark neutral at zero, warm for negative, cool for positive, brighter with
 *  magnitude. Stops are equally spaced over the layer's domain. Keep in step with palettes.py (a test compares). */
export const SAR_DIVERGING_DARK = ["#ff7a59", "#b34a38", "#2c2c2e", "#3a6ea8", "#64b5ff"] as const;

const CUSTOM: Record<string, readonly string[]> = { SarDivergingDark: SAR_DIVERGING_DARK };

export const isCustomRamp = (render: Render) => render.type === "ramp" && render.scheme in CUSTOM;

const rgb = (hex: string): [number, number, number] => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16)) as [number, number, number];

/** Color for `value` on a ramp of equally spaced `stops` across `domain`. NaN is transparent. Clips at both ends. */
export function rampColor(stops: readonly string[], domain: readonly [number, number], value: number): Rgba {
  if (!Number.isFinite(value)) return [0, 0, 0, 0];
  const t = Math.min(1, Math.max(0, (value - domain[0]) / (domain[1] - domain[0])));
  const pos = t * (stops.length - 1);
  const i = Math.min(stops.length - 2, Math.floor(pos));
  const f = pos - i;
  const [a, b] = [rgb(stops[i]), rgb(stops[i + 1])];
  return [0, 1, 2].map((k) => Math.round(a[k] * (1 - f) + b[k] * f)).concat(255) as Rgba;
}

/** A per-pixel color function for the COG protocol's `setColorFunction`, or undefined for built-in ramps. */
export function customColorFunction(render: Render): ((pixel: ArrayLike<number>, color: Uint8ClampedArray) => void) | undefined {
  if (render.type !== "ramp" || !(render.scheme in CUSTOM)) return undefined;
  const stops = CUSTOM[render.scheme];
  return (pixel, color) => color.set(rampColor(stops, render.domain, pixel[0]));
}
