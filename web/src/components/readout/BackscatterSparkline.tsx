"use client";

import { useEffect, useId, useMemo, useState } from "react";
import { CARD_SURFACE, CHART_COLOR, REFERENCE_GRAY } from "@/lib/chartColors";
import { formatStat } from "@/lib/format";
import {
  type Frame,
  areaPath,
  buildScales,
  cursorMs,
  dateMs,
  formatDelta,
  formatShortDate,
  formatValue,
  linePath,
  nearestIndex,
  valueAt,
} from "@/lib/series";
import { clock } from "@/lib/store";
import type { Beat } from "@/lib/beats";
import type { Chapter } from "@/types/chapter";
import { StatusBadge } from "@/components/ui/StatusBadge";

const FRAME: Frame = { width: 288, height: 84, padLeft: 6, padRight: 10, padTop: 10, padBottom: 8 };
const LINE_WIDTH = 2; // mark spec: lines are 2px
const DOT_R = 4; // markers are at least 8px across
const RING = 2; // 2px surface ring around markers

type Props = { chapter: Chapter; readout: NonNullable<Beat["readout"]> };

/** Beat progress, throttled to animation frames so the card re-renders only when the cursor moves. */
function useBeatProgress(): number {
  const [p, setP] = useState(() => clock.getState().p);
  useEffect(() => {
    let raf = 0;
    let last = -1;
    const unsubscribe = clock.subscribe((s) => {
      if (Math.abs(s.p - last) < 0.004) return;
      last = s.p;
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => setP(s.p));
    });
    return () => {
      unsubscribe();
      cancelAnimationFrame(raf);
    };
  }, []);
  return p;
}

export function BackscatterSparkline({ chapter, readout }: Props) {
  const series = chapter.generated.series.find((s) => s.id === readout.seriesId);
  const p = useBeatProgress();
  const [hover, setHover] = useState<number | null>(null);
  const [table, setTable] = useState(false);
  const titleId = useId();
  const scales = useMemo(() => (series ? buildScales(series, FRAME) : null), [series]);
  if (!series || !scales) return null;

  const color = CHART_COLOR[chapter.theme];
  const pts = series.points;
  const ref = series.reference;
  const fixed = readout.cursor ? dateMs(readout.cursor) : null;
  const ms = hover !== null ? dateMs(pts[hover].t) : (fixed ?? cursorMs(scales, p));
  const value = valueAt(pts, ms);
  const delta = value - pts[0].v;
  const refValue = ref ? valueAt(ref.points, ms) : null;
  const cx = scales.x(ms);
  const bottom = FRAME.height - FRAME.padBottom;
  const stat = readout.statKey ? chapter.generated.stats[readout.statKey] : undefined;
  const win = readout.window;
  const nearestToCursor = hover ?? nearestIndex(pts, ms);

  const onPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - rect.left) / rect.width) * FRAME.width;
    setHover(nearestIndex(pts, scales.xInverse(px)));
  };
  const onKeyDown = (e: React.KeyboardEvent) => {
    const step = e.key === "ArrowRight" || e.key === "ArrowUp" ? 1 : e.key === "ArrowLeft" || e.key === "ArrowDown" ? -1 : 0;
    if (e.key === "Home") setHover(0);
    else if (e.key === "End") setHover(pts.length - 1);
    else if (step) setHover(Math.min(pts.length - 1, Math.max(0, (hover ?? nearestToCursor) + step)));
    else return;
    e.preventDefault();
  };

  const tipLeft = Math.min(Math.max((cx / FRAME.width) * 100, 22), 78);
  const summary = `${series.label}: ${formatValue(pts[0].v, series.unit)} on ${formatShortDate(pts[0].t)} to ${formatValue(
    pts[pts.length - 1].v,
    series.unit,
  )} on ${formatShortDate(pts[pts.length - 1].t)}`;

  return (
    <figure aria-labelledby={titleId} className="glass-data w-full p-4 text-ink">
      <div className="flex items-start justify-between gap-3">
        <figcaption id={titleId} className="text-[11px] font-medium uppercase tracking-[0.08em] text-ink-faint">
          {series.label}
        </figcaption>
        <button
          type="button"
          onClick={() => setTable((t) => !t)}
          aria-pressed={table}
          className="shrink-0 rounded-full px-2 py-0.5 text-[11px] text-ink-dim transition-colors duration-[240ms] hover:bg-white/10 focus-visible:outline-2 focus-visible:outline-white/60"
        >
          {table ? "Chart" : "Table"}
        </button>
      </div>

      <div className="mt-1 flex items-baseline gap-2.5">
        <span className="tabular text-[28px] font-semibold leading-none display">{formatValue(value, series.unit)}</span>
        <span className="tabular text-[12px] text-ink-dim">
          {formatDelta(delta, series.unit)} since {formatShortDate(pts[0].t)}
        </span>
      </div>

      {table ? (
        <table className="tabular mt-3 w-full text-left text-[12px]">
          <caption className="sr-only">{summary}</caption>
          <thead className="text-ink-faint">
            <tr>
              <th className="py-1 font-normal">Date</th>
              <th className="py-1 text-right font-normal">{series.label.length > 22 ? "Value" : series.label}</th>
              {ref && <th className="py-1 text-right font-normal">{ref.label}</th>}
            </tr>
          </thead>
          <tbody>
            {pts.map((pt) => (
              <tr key={pt.t} className="border-t border-hairline">
                <td className="py-1 text-ink-dim">{formatShortDate(pt.t)}</td>
                <td className="py-1 text-right">{formatValue(pt.v, series.unit)}</td>
                {ref && <td className="py-1 text-right text-ink-dim">{formatValue(valueAt(ref.points, dateMs(pt.t)), series.unit)}</td>}
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div
          role="slider"
          tabIndex={0}
          aria-label={`${series.label}. ${summary}. Use arrow keys to inspect each date.`}
          aria-orientation="horizontal"
          aria-valuemin={0}
          aria-valuemax={pts.length - 1}
          aria-valuenow={nearestToCursor}
          aria-valuetext={`${formatShortDate(pts[nearestToCursor].t)}: ${formatValue(pts[nearestToCursor].v, series.unit)}`}
          onPointerMove={onPointerMove}
          onPointerLeave={() => setHover(null)}
          onKeyDown={onKeyDown}
          onBlur={() => setHover(null)}
          className="relative mt-3 cursor-crosshair rounded-lg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white/60"
        >
          <svg viewBox={`0 0 ${FRAME.width} ${FRAME.height}`} className="block h-auto w-full" aria-hidden>
            {win && (
              <rect
                x={scales.x(dateMs(win[0]))}
                y={FRAME.padTop}
                width={Math.max(0, scales.x(dateMs(win[1])) - scales.x(dateMs(win[0])))}
                height={bottom - FRAME.padTop}
                fill="rgb(255 255 255 / 0.06)"
              />
            )}
            <line x1={FRAME.padLeft} x2={FRAME.width - FRAME.padRight} y1={bottom} y2={bottom} stroke="rgb(255 255 255 / 0.12)" strokeWidth={1} />
            <path d={areaPath(pts, scales, bottom)} fill={color} fillOpacity={0.1} />
            {ref && (
              <path d={linePath(ref.points, scales)} fill="none" stroke={REFERENCE_GRAY} strokeWidth={LINE_WIDTH} strokeLinecap="round" strokeLinejoin="round" />
            )}
            <path d={linePath(pts, scales)} fill="none" stroke={color} strokeWidth={LINE_WIDTH} strokeLinecap="round" strokeLinejoin="round" />
            <line x1={cx} x2={cx} y1={FRAME.padTop} y2={bottom} stroke="rgb(255 255 255 / 0.3)" strokeWidth={1} />
            {refValue !== null && (
              <circle cx={cx} cy={scales.y(refValue)} r={DOT_R} fill={REFERENCE_GRAY} stroke={CARD_SURFACE} strokeWidth={RING} />
            )}
            <circle cx={cx} cy={scales.y(value)} r={DOT_R} fill={color} stroke={CARD_SURFACE} strokeWidth={RING} />
          </svg>
          {hover !== null && (
            <div
              role="status"
              className="tabular pointer-events-none absolute -top-2 z-10 -translate-x-1/2 -translate-y-full rounded-xl border border-hairline bg-[#2c2c2e] px-3 py-2 text-[12px] shadow-lg"
              style={{ left: `${tipLeft}%` }}
            >
              <div className="text-ink-faint">{formatShortDate(pts[hover].t)}</div>
              <TipRow color={color} value={formatValue(pts[hover].v, series.unit)} name={series.label} />
              {ref && (
                <TipRow color={REFERENCE_GRAY} value={formatValue(valueAt(ref.points, dateMs(pts[hover].t)), series.unit)} name={ref.label} />
              )}
            </div>
          )}
        </div>
      )}

      <div className="tabular mt-1 flex justify-between text-[11px] text-ink-faint">
        <span>{formatShortDate(pts[0].t)}</span>
        <span>{formatShortDate(pts[pts.length - 1].t)}</span>
      </div>

      {ref && (
        <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[12px] text-ink-dim max-lg:hidden">
          <LegendKey color={color} name={series.label} />
          <LegendKey color={REFERENCE_GRAY} name={ref.label} />
        </ul>
      )}
      {stat && (
        <div className="mt-3 flex items-baseline justify-between gap-3 border-t border-hairline pt-3 max-lg:hidden">
          <span className="text-[12px] text-ink-dim">{stat.label}</span>
          <span className="tabular text-[15px] font-semibold">{formatStat(stat)}</span>
        </div>
      )}
      {series.status !== "real" && <StatusBadge status={series.status} className="mt-3 max-lg:hidden" />}
    </figure>
  );
}

/** Tooltip row: a short stroke in the series color, the value first and strong, the name second. */
function TipRow({ color, value, name }: { color: string; value: string; name: string }) {
  return (
    <div className="mt-1 flex items-center gap-2">
      <span aria-hidden className="inline-block h-0.5 w-3 rounded-full" style={{ background: color }} />
      <span className="font-semibold text-ink">{value}</span>
      <span className="text-ink-dim">{name}</span>
    </div>
  );
}

function LegendKey({ color, name }: { color: string; name: string }) {
  return (
    <li className="flex items-center gap-1.5">
      <span aria-hidden className="inline-block h-0.5 w-4 rounded-full" style={{ background: color }} />
      {name}
    </li>
  );
}
