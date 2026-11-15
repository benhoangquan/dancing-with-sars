// Time-series helpers for the readout sparkline: interpolation, scales, paths, formatting. Pure, so tested.
import type { Chapter, Unit } from "@/types/chapter";
import { formatNumber, unitSuffix } from "./format";

export type Point = { t: string; v: number };
export type Series = Chapter["generated"]["series"][number];
/** What the scale and path helpers need from a series. */
export type SeriesLike = { points: readonly Point[]; reference?: { points: readonly Point[] } };

/** Midnight UTC of an ISO date, in milliseconds. */
export const dateMs = (iso: string) => Date.parse(`${iso}T00:00:00Z`);

const DAY = 86_400_000;

/** Linear interpolation of the series at time `ms`, clamped to its first and last points. */
export function valueAt(points: readonly Point[], ms: number): number {
  const first = points[0];
  const last = points[points.length - 1];
  if (ms <= dateMs(first.t)) return first.v;
  if (ms >= dateMs(last.t)) return last.v;
  for (let i = 0; i < points.length - 1; i++) {
    const a = dateMs(points[i].t);
    const b = dateMs(points[i + 1].t);
    if (ms >= a && ms <= b) return points[i].v + ((points[i + 1].v - points[i].v) * (ms - a)) / (b - a);
  }
  return last.v;
}

/** Index of the point whose date is nearest `ms`. */
export function nearestIndex(points: readonly Point[], ms: number): number {
  let best = 0;
  let gap = Infinity;
  points.forEach((p, i) => {
    const d = Math.abs(dateMs(p.t) - ms);
    if (d < gap) {
      gap = d;
      best = i;
    }
  });
  return best;
}

export interface Frame {
  width: number;
  height: number;
  padLeft: number;
  padRight: number;
  padTop: number;
  padBottom: number;
}

export interface Scales {
  x: (ms: number) => number;
  y: (v: number) => number;
  /** Inverse of x: the time at a horizontal position. */
  xInverse: (px: number) => number;
  t0: number;
  t1: number;
  v0: number;
  v1: number;
}

/** Scales over the series and its reference together, so both share one axis. The y range is padded 12%. */
export function buildScales(series: SeriesLike, f: Frame): Scales {
  const all = [...series.points, ...(series.reference?.points ?? [])];
  const t0 = Math.min(...all.map((p) => dateMs(p.t)));
  const t1 = Math.max(...all.map((p) => dateMs(p.t)));
  let lo = Math.min(...all.map((p) => p.v));
  let hi = Math.max(...all.map((p) => p.v));
  if (hi - lo < 1e-9) {
    lo -= 1;
    hi += 1;
  }
  const pad = (hi - lo) * 0.12;
  const v0 = lo - pad;
  const v1 = hi + pad;
  const w = f.width - f.padLeft - f.padRight;
  const h = f.height - f.padTop - f.padBottom;
  const x = (ms: number) => f.padLeft + (t1 === t0 ? 0 : ((ms - t0) / (t1 - t0)) * w);
  return {
    x,
    y: (v: number) => f.padTop + (1 - (v - v0) / (v1 - v0)) * h,
    xInverse: (px) => t0 + ((px - f.padLeft) / w) * (t1 - t0),
    t0,
    t1,
    v0,
    v1,
  };
}

const num = (n: number) => (Math.round(n * 100) / 100).toString();

/** SVG path for a polyline through the points. */
export const linePath = (points: readonly Point[], s: Scales) =>
  points.map((p, i) => `${i ? "L" : "M"}${num(s.x(dateMs(p.t)))} ${num(s.y(p.v))}`).join("");

/** Closed path from the line down to the bottom of the plot, for the area wash. */
export function areaPath(points: readonly Point[], s: Scales, bottom: number) {
  const first = points[0];
  const last = points[points.length - 1];
  return `${linePath(points, s)}L${num(s.x(dateMs(last.t)))} ${num(bottom)}L${num(s.x(dateMs(first.t)))} ${num(bottom)}Z`;
}

/** Decimals shown for a series value of a unit. */
export const seriesDecimals = (unit: Unit) => (unit === "ha" || unit === "count" ? 0 : 1);

export const formatValue = (v: number, unit: Unit) => `${formatNumber(v, seriesDecimals(unit))}${unitSuffix(unit)}`;

/** Signed change, for example "+2.1 dB" or "−5.5 dB". */
export function formatDelta(delta: number, unit: Unit): string {
  const d = seriesDecimals(unit);
  const rounded = Number(delta.toFixed(d));
  const sign = rounded > 0 ? "+" : "";
  return `${sign}${formatNumber(rounded, d)}${unitSuffix(unit)}`;
}

/** "Jun 17" (UTC), the short form used on the sparkline. */
export const formatShortDate = (iso: string) =>
  new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", timeZone: "UTC" }).format(dateMs(iso));

/** ISO date `ms` falls on, UTC. */
export const isoFromMs = (ms: number) => new Date(ms).toISOString().slice(0, 10);

/** Cursor time for a scroll-driven sparkline: sweeps the series' date range as beat progress goes 0 to 1. */
export const cursorMs = (s: Scales, p: number) => s.t0 + (s.t1 - s.t0) * Math.min(1, Math.max(0, p));

export const daysBetween = (aIso: string, bIso: string) => Math.round((dateMs(bIso) - dateMs(aIso)) / DAY);
