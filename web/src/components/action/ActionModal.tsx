"use client";

import { useState } from "react";
import { CityScaleCompare } from "@/components/action/CityScaleCompare";
import { RichText } from "@/components/ui/RichText";
import { Sheet } from "@/components/ui/Sheet";
import { formatNumber, formatStat } from "@/lib/format";
import { chapterTokens } from "@/lib/tokens";
import type { Chapter } from "@/types/chapter";

type Props = { chapter: Chapter; open: boolean; onClose: () => void };
type Tab = "support" | "local";

/** Where the figures in this sheet come from, in one honest line. */
export function provenanceLine(chapter: Chapter): string {
  const { metrics } = chapter.action;
  const measured = chapter.generated.series.some((s) => s.status === "real");
  const cited = metrics.some((m) => !("statKey" in m));
  const fallback = chapter.generated.sources.some((s) => s.mission === "BC Wildfire Service");
  const provisional = chapter.generated.sources.some((s) => s.mission === "NISAR" && s.maturity !== "validated");
  const parts: string[] = [];
  if (measured) parts.push(`Radar figures measured from NISAR data by this project${provisional ? " (provisional release: calibrated, not final)" : ""}.`);
  if (fallback) parts.push("The fire's area is BC Wildfire Service's mapped perimeter, not a NISAR measurement.");
  if (cited) parts.push("Other figures come from the published sources linked under each one.");
  return parts.join(" ");
}

/** End-of-chapter action sheet: support organizations (tab 1) and what to do where you live (tab 2). */
export function ActionModal({ chapter, open, onClose }: Props) {
  const [tab, setTab] = useState<Tab>("support");
  const { action, generated } = chapter;
  const tabs: [Tab, string][] = [
    ["support", "Support"],
    ["local", "Act Where You Live"],
  ];
  return (
    <Sheet open={open} onClose={onClose} labelledBy="action-title">
      <div className="px-8 pb-8 pt-10 text-light-ink max-sm:px-5">
        <p className="text-[12px] font-semibold uppercase tracking-[0.1em] text-light-ink-dim">{chapter.aoi.placeName}</p>
        <h2 id="action-title" className="display mt-2 text-[30px] font-semibold leading-[1.1]">
          {action.headline}
        </h2>
        <div role="tablist" aria-label="Ways to act" className="mt-5 inline-flex rounded-full bg-light-surface p-1">
          {tabs.map(([id, label]) => (
            <button
              key={id}
              type="button"
              role="tab"
              id={`tab-${id}`}
              aria-selected={tab === id}
              aria-controls={`panel-${id}`}
              data-autofocus={id === "support" ? true : undefined}
              onClick={() => setTab(id)}
              className={`rounded-full px-4 py-1.5 text-[14px] font-semibold transition-colors duration-[240ms] ${tab === id ? "bg-white text-light-ink shadow-sm" : "text-light-ink-dim"}`}
            >
              {label}
            </button>
          ))}
        </div>

        {tab === "support" ? (
          <div id="panel-support" role="tabpanel" aria-labelledby="tab-support" className="mt-5 space-y-6">
            <p className="text-[16px] leading-[1.47] text-light-ink-dim">
              <RichText text={action.body} ctx={chapterTokens(chapter)} anchors={false} />
            </p>
            <ul className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
              {action.metrics.map((m) => (
                <li key={m.label} className="rounded-2xl bg-light-surface p-4">
                  <p className="tabular display text-[24px] font-semibold leading-none">
                    {"statKey" in m ? formatStat(generated.stats[m.statKey]) : `${formatNumber(m.value, Number.isInteger(m.value) ? 0 : 1)} ${m.unit}`}
                  </p>
                  <p className="mt-2 text-[13px] leading-snug text-light-ink-dim">{m.label}</p>
                  <a href={m.source.url} target="_blank" rel="noopener noreferrer" className="mt-2 block text-[11px] leading-snug text-light-ink-dim underline underline-offset-2">
                    {m.source.name}, accessed {m.source.accessed}
                  </a>
                </li>
              ))}
            </ul>
            <p className="text-[12px] leading-snug text-light-ink-dim">{provenanceLine(chapter)}</p>
            <section aria-label="Organizations you can support" className="space-y-3">
              {action.organizations.map((o) => (
                <article key={o.name} className="rounded-2xl border border-black/10 p-5">
                  <h3 className="text-[18px] font-semibold">
                    <a href={o.url} target="_blank" rel="noopener noreferrer" className="hover:underline">
                      {o.name}
                    </a>
                  </h3>
                  <p className="mt-1 text-[14px] leading-snug text-light-ink-dim">{o.focus}</p>
                  <p className="mt-1 text-[12px] text-light-ink-dim">{o.region}</p>
                  <a
                    href={o.cta.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-4 inline-flex items-center rounded-full bg-apple-blue px-5 py-2.5 text-[15px] font-semibold text-white transition-colors duration-[240ms] hover:bg-apple-blue-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-apple-blue"
                  >
                    {o.cta.label}
                    <span aria-hidden className="ml-1.5">↗</span>
                  </a>
                  <p className="mt-3 text-[11px] text-light-ink-dim">
                    Link checked {o.verified.on}: {o.verified.how}.
                  </p>
                </article>
              ))}
            </section>
          </div>
        ) : (
          <div id="panel-local" role="tabpanel" aria-labelledby="tab-local" className="mt-5 space-y-5">
            <CityScaleCompare chapter={chapter} />
            {action.local && (
              <section aria-labelledby="local-title">
                <h3 id="local-title" className="text-[18px] font-semibold">
                  {action.local.headline}
                </h3>
                <p className="mt-1 text-[15px] leading-[1.47] text-light-ink-dim">{action.local.body}</p>
                <ol className="mt-3 list-decimal space-y-2 pl-5 text-[15px] leading-[1.45]">
                  {action.local.steps.map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ol>
              </section>
            )}
          </div>
        )}
      </div>
    </Sheet>
  );
}
