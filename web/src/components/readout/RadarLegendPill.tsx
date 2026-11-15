"use client";

import { AnimatePresence, motion } from "motion/react";
import { useEffect } from "react";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useStory } from "@/lib/store";
import type { Chapter, Layer } from "@/types/chapter";

type Props = { chapter: Chapter; visibleLayerIds: string[] };

const EASE = [0.22, 1, 0.36, 1] as const;

function Swatch({ swatch }: { swatch: Chapter["legend"][number]["swatch"] }) {
  if (swatch.kind === "solid") {
    return <span aria-hidden className="size-3 shrink-0 rounded-full border border-white/20" style={{ background: swatch.color }} />;
  }
  return (
    <span
      aria-hidden
      className="h-2.5 w-9 shrink-0 rounded-full border border-white/20"
      style={{ background: `linear-gradient(to right, ${swatch.stops.join(", ")})` }}
    />
  );
}

/** The most cautious status among the visible layers, so the chip never overstates the data. */
function worstStatus(layers: Layer[]): Layer["status"] {
  if (layers.some((l) => l.status === "illustrative")) return "illustrative";
  if (layers.some((l) => l.status === "fallback")) return "fallback";
  return "real";
}

/** Collapsed: swatch chips and a provenance chip. Expanded: plain-English meanings and where each layer came from. */
export function RadarLegendPill({ chapter, visibleLayerIds }: Props) {
  const open = useStory((s) => s.legendOpen);
  const setOpen = useStory((s) => s.setLegendOpen);
  const visible = chapter.generated.layers.filter((l) => visibleLayerIds.includes(l.id));
  const entries = chapter.legend.filter((e) => e.layerIds.some((id) => visibleLayerIds.includes(id)));
  const sources = new Map(chapter.generated.sources.map((s) => [s.id, s]));
  const hasComposite = visible.some((l) => l.kind === "sar-composite");

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, setOpen]);

  return (
    <section aria-label="Radar legend" className="glass-data w-full overflow-hidden">
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            key="panel"
            id="legend-panel"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.4, ease: EASE }}
            className="overflow-hidden"
          >
            <div className="max-h-[max(10rem,calc(100svh-30rem))] space-y-4 overflow-y-auto p-4 pb-2 max-lg:max-h-[40svh]">
              {hasComposite && (
                <p className="tabular text-[12px] text-ink-dim">
                  Radar colors: <span className="font-semibold text-ink">red = HH</span>,{" "}
                  <span className="font-semibold text-ink">green = HV</span>,{" "}
                  <span className="font-semibold text-ink">blue = HH relative to HV</span>.
                </p>
              )}
              <ul className="space-y-3">
                {entries.map((e) => (
                  <li key={e.id} className="flex gap-3">
                    <span className="mt-1"><Swatch swatch={e.swatch} /></span>
                    <span>
                      <span className="block text-[13px] font-semibold">{e.label}</span>
                      <span className="block text-[12px] leading-snug text-ink-dim">{e.meaning}</span>
                    </span>
                  </li>
                ))}
              </ul>
              <p className="text-[12px] leading-snug text-ink-dim">{chapter.radar.explainer}</p>
              <div>
                <h3 className="text-[11px] font-medium uppercase tracking-[0.08em] text-ink-faint">Where these layers come from</h3>
                <ul className="mt-2 space-y-2">
                  {visible.map((l) => {
                    const src = l.sourceIds.map((id) => sources.get(id)).find(Boolean);
                    return (
                      <li key={l.id} className="text-[12px] leading-snug">
                        <span className="tabular font-semibold">{l.label}</span>
                        <span className="tabular block text-ink-dim">
                          {src ? `${src.mission} · ${src.product}${src.maturity === "n/a" ? "" : ` (${src.maturity})`}` : "Unknown source"} · {l.date}
                        </span>
                        <StatusBadge status={l.status} className="mt-1" />
                      </li>
                    );
                  })}
                </ul>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      <button
        type="button"
        aria-expanded={open}
        aria-controls="legend-panel"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors duration-[240ms] hover:bg-white/5 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-white/60"
      >
        <span className="flex min-w-0 flex-1 flex-wrap items-center gap-x-3 gap-y-1">
          {entries.slice(0, 3).map((e) => (
            <span key={e.id} className="flex items-center gap-1.5 text-[12px] text-ink-dim">
              <Swatch swatch={e.swatch} />
              {e.label}
            </span>
          ))}
          {entries.length === 0 && <span className="text-[12px] text-ink-dim">Legend</span>}
        </span>
        <StatusBadge status={worstStatus(visible)} />
        <span aria-hidden className={`text-ink-faint transition-transform duration-[240ms] ${open ? "rotate-180" : ""}`}>
          ˄
        </span>
      </button>
    </section>
  );
}
