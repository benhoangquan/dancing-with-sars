import { formatStat } from "@/lib/format";
import type { Chapter } from "@/types/chapter";

/** Key for the infrastructure overlay, with the counts measured against a real footprint. */
export function ImpactKey({ chapter }: { chapter: Chapter }) {
  const impact = chapter.generated.impact;
  if (!impact) return null;
  const c = impact.counts;
  const stats = chapter.generated.stats;
  const items: [string, string][] = [];
  if (c.territories) items.push(["#FFD60A", "Indigenous territory"]);
  if (c.road_segments) items.push(["#FFFFFF", "Roads"]);
  if (c.road_km_near !== undefined) items.push(["#FF9F0A", "Roads near new clearings"]);
  if (c.buildings) items.push(["#FFFFFF", "Buildings"]);
  if (c.buildings_near !== undefined) items.push(["#FF453A", "Buildings near the burn"]);
  const figures = Object.entries(stats).filter(([k]) => k.startsWith("impact_"));
  return (
    <div className="glass-dark mt-2 px-4 py-2.5 text-[12px] text-ink-dim">
      <ul className="flex flex-wrap gap-x-3 gap-y-1">
        {items.map(([color, label]) => (
          <li key={label} className="flex items-center gap-1.5">
            <span aria-hidden className="inline-block h-[3px] w-3 rounded-full" style={{ background: color }} />
            {label}
          </li>
        ))}
      </ul>
      {figures.map(([k, s]) => (
        <p key={k} className="mt-1">
          <span className="tabular font-semibold text-ink">{formatStat(s)}</span> {s.label.toLowerCase().replace(/^road within/, "of road within")}
        </p>
      ))}
      <p className="mt-1 text-[11px] text-ink-faint">Overture Maps and OpenStreetMap, ODbL</p>
    </div>
  );
}
