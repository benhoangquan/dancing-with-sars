"use client";

import { useEffect, useMemo, useState } from "react";
import { assetUrl } from "@/lib/asset";
import { areaHa, extentMetres, svgPath, toLocalMetres } from "@/lib/cityScale";
import { formatNumber } from "@/lib/format";
import type { Chapter } from "@/types/chapter";

const CITIES = [
  { id: "montreal", label: "Montréal" },
  { id: "new-york", label: "New York" },
  { id: "toronto", label: "Toronto" },
  { id: "london", label: "London" },
  { id: "jakarta", label: "Jakarta" },
] as const;
type CityId = (typeof CITIES)[number]["id"];
type CityDoc = { id: string; label: string; geometry: Parameters<typeof toLocalMetres>[0] };

const SIZE = 320;

/** The chapter's footprint drawn over a reference city at the same scale (1:1 in ground metres). */
export function CityScaleCompare({ chapter }: { chapter: Chapter }) {
  const [city, setCity] = useState<CityId>("montreal");
  const [doc, setDoc] = useState<CityDoc | null>(null);
  const footprint = chapter.generated.footprint;

  useEffect(() => {
    let live = true;
    fetch(assetUrl(`cities/${city}.json`))
      .then((r) => r.json())
      .then((d: CityDoc) => live && setDoc(d))
      .catch(() => live && setDoc(null));
    return () => {
      live = false;
    };
  }, [city]);

  const drawn = useMemo(() => {
    if (!footprint || !doc) return null;
    const fp = toLocalMetres(footprint.geometry as CityDoc["geometry"]);
    const town = toLocalMetres(doc.geometry);
    const half = extentMetres(fp, town) * 1.05;
    return { fp: svgPath(fp, half, SIZE), town: svgPath(town, half, SIZE), cityHa: areaHa(town), half };
  }, [footprint, doc]);

  if (!footprint) return null;
  const share = drawn ? (100 * footprint.areaHa) / drawn.cityHa : null;
  const barMetres = drawn ? niceBar(drawn.half) : 0;
  return (
    <section aria-labelledby="scale-title" className="rounded-2xl bg-light-surface p-5">
      <h3 id="scale-title" className="text-[18px] font-semibold">
        Your city scale
      </h3>
      <p className="mt-1 text-[14px] leading-snug text-light-ink-dim">
        {footprint.label}, <span className="tabular font-semibold text-light-ink">{formatNumber(footprint.areaHa, 0)} ha</span>, drawn over a city at the same scale.
        {footprint.kind === "equal-area" && " The square has the same area; its shape is not the real one."}
      </p>
      <div role="radiogroup" aria-label="Reference city" className="mt-3 flex flex-wrap gap-2">
        {CITIES.map((c) => (
          <button
            key={c.id}
            type="button"
            role="radio"
            aria-checked={city === c.id}
            onClick={() => setCity(c.id)}
            className={`rounded-full px-3 py-1 text-[13px] font-semibold transition-colors duration-[240ms] ${city === c.id ? "bg-apple-blue text-white" : "bg-white text-light-ink"}`}
          >
            {c.label}
          </button>
        ))}
      </div>
      <figure className="mt-4">
        <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className="mx-auto block w-full max-w-[320px]" role="img" aria-label={`${footprint.label} drawn at the same scale as ${doc?.label ?? "the city"}`} data-city={city}>
          {drawn && (
            <>
              <path d={drawn.town} fill="#D2D2D7" stroke="#86868B" strokeWidth={1} fillRule="evenodd" />
              <path d={drawn.fp} fill="#FF3B30" fillOpacity={0.85} stroke="#FFFFFF" strokeWidth={1.5} fillRule="evenodd" data-footprint />
              <g transform={`translate(12 ${SIZE - 14})`}>
                <rect width={(barMetres / (2 * drawn.half)) * SIZE} height={3} rx={1.5} fill="#1D1D1F" />
                <text y={-6} fontSize={11} fill="#6E6E73" className="tabular">
                  {barMetres >= 1000 ? `${formatNumber(barMetres / 1000, 0)} km` : `${formatNumber(barMetres, 0)} m`}
                </text>
              </g>
            </>
          )}
        </svg>
        <figcaption className="mt-2 text-center text-[13px] text-light-ink-dim">
          {share !== null && doc ? (
            <>
              About <span className="tabular font-semibold text-light-ink">{formatNumber(share, share < 10 ? 1 : 0)}%</span> of {doc.label}’s area. City outline © OpenStreetMap contributors (ODbL).
            </>
          ) : (
            "Loading the city outline…"
          )}
        </figcaption>
      </figure>
    </section>
  );
}

/** A round scale-bar length near a fifth of the drawing. */
function niceBar(halfMetres: number): number {
  const target = (2 * halfMetres) / 5;
  const pow = 10 ** Math.floor(Math.log10(target));
  return [1, 2, 5, 10].map((k) => k * pow).reduce((best, v) => (Math.abs(v - target) < Math.abs(best - target) ? v : best));
}
