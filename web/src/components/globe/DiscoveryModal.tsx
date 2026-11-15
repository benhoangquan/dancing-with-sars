"use client";

import { Sheet } from "@/components/ui/Sheet";
import { useStory } from "@/lib/store";
import type { WatchedPlace } from "@/lib/watched";
import type { Chapter } from "@/types/chapter";

type Props = { chapters: Chapter[]; watched: WatchedPlace[]; highlight: string | null };

/** What a chapter's numbers rest on, in one line. */
export function dataLine(c: Chapter): string {
  const real = c.generated.layers.some((l) => l.status === "real" && l.sourceIds.includes("nisar-gcov"));
  const measured = c.generated.series.some((s) => s.status === "real");
  if (real && measured) return "Measured with NISAR";
  if (real) return "NISAR imagery, numbers from published studies";
  return "Illustrative data";
}

/** "Take Action" on the hotspot globe: every place, its stakes and who to support, plus where NISAR looked. */
export function DiscoveryModal({ chapters, watched, highlight }: Props) {
  const modal = useStory((s) => s.modal);
  const setModal = useStory((s) => s.setModal);
  const enterPlace = useStory((s) => s.enterPlace);
  const open = modal === "discovery";
  return (
    <Sheet open={open} onClose={() => setModal(null)} labelledBy="discovery-title">
      <div className="px-8 pb-8 pt-10 text-light-ink max-sm:px-5">
        <p className="text-[12px] font-semibold uppercase tracking-[0.1em] text-light-ink-dim">Take action</p>
        <h2 id="discovery-title" className="display mt-2 text-[32px] font-semibold leading-[1.1]">
          Three places, three ways to help
        </h2>
        <ul className="mt-6 flex flex-col gap-3">
          {chapters.map((c) => {
            const org = c.action.organizations[0];
            return (
              <li key={c.slug} className="rounded-2xl bg-light-surface p-5">
                <p className="text-[12px] font-semibold uppercase tracking-[0.08em]" style={{ color: c.accent === "#64D2FF" ? "#0071E3" : undefined }}>
                  {c.kicker}
                </p>
                <h3 className="display mt-1 text-[21px] font-semibold leading-[1.2]">{c.title}</h3>
                <p className="mt-2 text-[15px] leading-[1.47] text-light-ink-dim">{c.dek}</p>
                <p className="mt-2 text-[12px] font-medium text-light-ink-dim">{dataLine(c)}</p>
                <div className="mt-4 flex flex-wrap gap-2">
                  <button
                    type="button"
                    data-autofocus={c === chapters[0] ? true : undefined}
                    onClick={() => enterPlace(c.slug, null)}
                    className="rounded-full bg-apple-blue px-4 py-2 text-[14px] font-semibold text-white transition-colors duration-[240ms] hover:bg-apple-blue-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-apple-blue"
                  >
                    Open the story
                  </button>
                  <a
                    href={org.cta.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="rounded-full bg-light-ink px-4 py-2 text-[14px] font-semibold text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-apple-blue"
                  >
                    {org.cta.label}
                  </a>
                </div>
              </li>
            );
          })}
        </ul>
        <h3 className="display mt-8 text-[19px] font-semibold">Checked, no chapter yet</h3>
        <p className="mt-1 text-[14px] text-light-ink-dim">NISAR data was fetched and analyzed for these places too. None gave a change we could defend, so they stay on the globe in grey.</p>
        <ul className="mt-3 flex flex-col gap-2">
          {watched.map((w) => (
            <li key={w.id} id={`watched-${w.id}`} className={`rounded-xl px-4 py-3 text-[14px] ${highlight === w.id ? "bg-apple-blue/10 ring-1 ring-apple-blue/40" : "bg-light-surface"}`}>
              <span className="font-semibold">
                {w.name} · {w.iso3}
              </span>
              <span className="text-light-ink-dim"> — {w.note}</span>
            </li>
          ))}
        </ul>
        <p className="mt-8 border-t border-black/10 pt-4 text-[12px] leading-[1.5] text-light-ink-dim">
          Radar: NISAR L2 GCOV, provisional release (NASA-ISRO, ASF DAAC). Optical: HLS (NASA). Terrain: Copernicus DEM GLO-30. Globe: NASA Blue Marble.
          Each chapter lists its own sources and methods.
        </p>
      </div>
    </Sheet>
  );
}
