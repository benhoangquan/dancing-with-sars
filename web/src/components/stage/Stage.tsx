"use client";

import dynamic from "next/dynamic";
import { useReducedMotion } from "motion/react";
import { useEffect, useRef } from "react";
import { SwipeDivider } from "@/components/map/SwipeDivider";
import { SyncedFlyoverPlayer } from "@/components/map/SyncedFlyoverPlayer";
import { effectiveMode } from "@/lib/beats";
import { useStory } from "@/lib/store";
import type { Chapter } from "@/types/chapter";

// MapLibre, deck.gl and the COG reader load in a separate chunk, in the browser only.
const RadarCompareMap = dynamic(() => import("@/components/map/RadarCompareMap"), { ssr: false });

/** The fixed full-bleed stage behind the story. Shows the active beat of the active chapter. */
export function Stage({ chapters }: { chapters: Chapter[] }) {
  const chapterIdx = useStory((s) => s.chapterIdx);
  const beatIdx = useStory((s) => s.beatIdx);
  const pinned = useStory((s) => s.pinnedMode);
  const reduced = useReducedMotion() ?? false;
  const root = useRef<HTMLDivElement>(null);

  const chapter = chapters[chapterIdx];
  const beat = chapter.beats[beatIdx];
  const mode = effectiveMode(beat, pinned);
  const video = chapter.generated.flyover.video;
  const videoActive = Boolean(video) && mode !== "radar";

  // The swipe position is a CSS variable, so the divider and the clip move without re-rendering React.
  useEffect(() => {
    const set = (swipe: number) => root.current?.style.setProperty("--swipe", String(swipe));
    set(useStory.getState().swipe);
    return useStory.subscribe((s) => set(s.swipe));
  }, []);

  return (
    <div
      ref={root}
      data-story-root
      data-mode={mode}
      data-video={videoActive}
      role="group"
      aria-label={`Map view, ${mode === "radar" ? "radar compare" : mode}`}
      className="stage-root fixed inset-0 z-0 bg-black"
    >
      <RadarCompareMap chapter={chapter} beat={beat} mode={mode} reduced={reduced} videoActive={videoActive} />
      {video && videoActive && (
        <div className="pane pane-video">
          <SyncedFlyoverPlayer video={video} label={`Terrain flyover of ${chapter.aoi.placeName}`} />
        </div>
      )}
      {mode === "radar" && <SwipeDivider />}
    </div>
  );
}
