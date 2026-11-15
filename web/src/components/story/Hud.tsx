"use client";

import { ModeSegmentedControl } from "@/components/controls/ModeSegmentedControl";
import { BackscatterSparkline } from "@/components/readout/BackscatterSparkline";
import { RadarLegendPill } from "@/components/readout/RadarLegendPill";
import type { Beat } from "@/lib/beats";
import { useStory } from "@/lib/store";
import type { Chapter, StageMode } from "@/types/chapter";

type Props = { chapter: Chapter; beatIdx: number; beat: Beat; mode: StageMode; visibleLayerIds: string[] };

/** Fixed overlay: wordmark, mode control and call to action on top; readout and legend at the side. */
export function Hud({ chapter, beatIdx, beat, mode, visibleLayerIds }: Props) {
  const pinMode = useStory((s) => s.pinMode);
  const setDrawerOpen = useStory((s) => s.setDrawerOpen);
  const lastBeat = beatIdx === chapter.beats.length - 1;
  const live = !chapter.generated.flyover.video;

  return (
    <div data-story-root className="pointer-events-none fixed inset-0 z-30">
      <header className="flex items-center justify-between gap-2 px-3 py-3 lg:px-6 lg:py-4">
        <a href="#top" className="glass pointer-events-auto rounded-full! px-4 py-2 text-[13px] font-semibold display max-md:hidden">
          Dancing with the SARs
        </a>
        <div className="pointer-events-auto max-md:mx-auto">
          <ModeSegmentedControl value={mode} onChange={pinMode} liveFlyover={live} />
        </div>
        <button
          type="button"
          onClick={() => setDrawerOpen(true)}
          className={`pointer-events-auto rounded-full bg-white px-4 py-2 text-[13px] font-semibold text-black transition-transform duration-[240ms] ease-[cubic-bezier(0.22,1,0.36,1)] hover:scale-[1.04] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white max-md:hidden ${lastBeat ? "cta-pulse" : ""}`}
        >
          Take action · {chapter.aoi.placeName}
        </button>
        <button
          type="button"
          onClick={() => setDrawerOpen(true)}
          className={`pointer-events-auto absolute right-3 top-[3.75rem] rounded-full bg-white px-4 py-2 text-[13px] font-semibold text-black md:hidden ${lastBeat ? "cta-pulse" : ""}`}
        >
          Take action
        </button>
      </header>
      <aside
        aria-label="Radar readout"
        className="pointer-events-auto absolute bottom-5 right-5 flex w-80 flex-col gap-3 max-lg:inset-x-3 max-lg:bottom-auto max-lg:right-auto max-lg:top-[6.75rem] max-lg:w-auto max-lg:max-w-[22rem]"
      >
        {beat.readout && <BackscatterSparkline key={`${chapter.slug}-${beat.id}`} chapter={chapter} readout={beat.readout} />}
        <RadarLegendPill chapter={chapter} visibleLayerIds={visibleLayerIds} />
      </aside>
    </div>
  );
}
