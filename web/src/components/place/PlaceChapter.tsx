"use client";

import dynamic from "next/dynamic";
import { useReducedMotion } from "motion/react";
import { useEffect, useRef } from "react";
import { ActionModal } from "@/components/action/ActionModal";
import { SwipeDivider } from "@/components/map/SwipeDivider";
import { SyncedFlyoverPlayer } from "@/components/map/SyncedFlyoverPlayer";
import { RadarLegendPill } from "@/components/readout/RadarLegendPill";
import { RichText } from "@/components/ui/RichText";
import { paneLayers } from "@/lib/beats";
import { actOf, overlays } from "@/lib/scenes";
import { startStoryScroll } from "@/lib/scroll";
import { useStory } from "@/lib/store";
import { chapterTokens } from "@/lib/tokens";
import type { Chapter } from "@/types/chapter";
import { BeatGlassCard } from "./BeatGlassCard";
import { ImpactKey } from "./ImpactKey";

const RadarCompareMap = dynamic(() => import("@/components/map/RadarCompareMap"), { ssr: false });

/**
 * Scene 3, one place in three acts. Act I is the 20-second flyover (video, else the live map flying the same
 * path) with a lower-third caption. Act II is the radar stage: swipe, beat cards, landmarks and legend. Act III
 * is the resolution card with Take Action. Scrolling past the end returns to the globe.
 */
export function PlaceChapter({ chapter, onExit }: { chapter: Chapter; onExit: () => void }) {
  const root = useRef<HTMLElement>(null);
  const stage = useRef<HTMLDivElement>(null);
  const exit = useRef<HTMLElement>(null);
  const reduced = useReducedMotion() ?? false;
  const beatIdx = useStory((s) => s.beatIdx);
  const modal = useStory((s) => s.modal);
  const setModal = useStory((s) => s.setModal);
  const n = chapter.beats.length;
  const act = actOf(beatIdx, n);
  const beat = chapter.beats[beatIdx];
  const mode = act === 1 ? "flyover" : "radar";
  const video = chapter.generated.flyover.video;
  const videoActive = Boolean(video) && act === 1;
  const o = overlays({ scene: "PLACE_CHAPTER", act, dragging: false, popover: null, modal });
  const last = chapter.beats[n - 1];
  const panes = paneLayers(beat, mode);

  useEffect(() => {
    window.scrollTo(0, 0);
    if (!root.current) return;
    return startStoryScroll(root.current, [chapter], () => window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }, [chapter]);

  // The swipe position is a CSS variable, so the divider and the clip move without re-rendering React.
  useEffect(() => {
    const set = (swipe: number) => stage.current?.style.setProperty("--swipe", String(swipe));
    set(useStory.getState().swipe);
    return useStory.subscribe((s) => set(s.swipe));
  }, []);

  // Past the end of Act III: back to the globe.
  useEffect(() => {
    let done = false;
    const onScroll = () => {
      const el = exit.current;
      if (done || !el) return;
      if (el.getBoundingClientRect().bottom <= window.innerHeight + 2) {
        done = true;
        onExit();
      }
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [onExit]);

  return (
    <>
      <div ref={stage} data-story-root data-mode={mode} data-video={videoActive} data-act={act} className="stage-root fixed inset-0 z-0 bg-black" role="group" aria-label={`Map of ${chapter.aoi.placeName}`}>
        <RadarCompareMap chapter={chapter} beat={beat} mode={mode} reduced={reduced} videoActive={videoActive} showLandmarks={o.landmarks} />
        {video && videoActive && (
          <div className="pane pane-video">
            <SyncedFlyoverPlayer video={video} label={`Terrain flyover of ${chapter.aoi.placeName}`} />
          </div>
        )}
        {mode === "radar" && <SwipeDivider />}
      </div>

      {o.legend && (
        <div data-story-root className="pointer-events-auto fixed left-1/2 top-[5.25rem] z-20 w-[min(26rem,calc(100vw-1.5rem))] -translate-x-1/2">
          <RadarLegendPill chapter={chapter} visibleLayerIds={[...new Set([...panes.a, ...panes.b])]} />
          <ImpactKey chapter={chapter} />
        </div>
      )}

      <main ref={root} data-story-root className="pointer-events-none relative z-20 text-ink">
        <section data-section="beat" data-chapter={0} data-beat={0} aria-labelledby="act1-title" className="relative min-h-[170svh]">
          <div className="sticky top-0 flex h-svh flex-col justify-end px-8 pb-12 max-sm:px-4 max-sm:pb-6">
            <div className="lower-third max-w-[640px]">
              <p className="text-[13px] font-semibold uppercase tracking-[0.1em]" style={{ color: chapter.accent }}>
                {chapter.kicker}
              </p>
              <h1 id="act1-title" className="display mt-2 text-[clamp(34px,5vw,56px)] font-semibold leading-[1.05]">
                {chapter.title}
              </h1>
              <p className="mt-3 max-w-[52ch] text-[17px] leading-[1.47] text-ink/85">{chapter.dek}</p>
              <div className="mt-5 flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => window.dispatchEvent(new Event("sar:replay"))}
                  className="glass-dark pointer-events-auto rounded-full! px-4 py-2 text-[13px] font-semibold"
                >
                  Replay 20s
                </button>
                <span className="text-[13px] text-ink-faint">Scroll to read the radar</span>
              </div>
            </div>
          </div>
        </section>

        {chapter.beats.slice(1, n - 1).map((b, i) => (
          <BeatGlassCard key={b.id} chapter={chapter} beatIdx={i + 1} />
        ))}

        <section data-section="beat" data-chapter={0} data-beat={n - 1} aria-labelledby="act3-title" className="relative min-h-[130svh]">
          <div className="sticky top-0 flex h-svh items-center justify-center px-6">
            <article className="glass-dark pointer-events-auto w-full max-w-[520px] p-8 text-center max-sm:p-6">
              <p className="text-[12px] font-semibold uppercase tracking-[0.1em]" style={{ color: chapter.accent }}>
                {last.eyebrow ?? "What helps"}
              </p>
              <h2 id="act3-title" className="display mt-2 text-[30px] font-semibold leading-[1.1]">
                {last.headline}
              </h2>
              <p className="mt-3 text-[17px] leading-[1.47] text-ink/85">
                <RichText text={last.body} ctx={chapterTokens(chapter)} />
              </p>
              <button
                type="button"
                onClick={() => setModal("action")}
                className={`mt-6 rounded-full bg-apple-blue px-6 py-3 text-[17px] font-semibold text-white transition-colors duration-[240ms] hover:bg-apple-blue-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white ${act === 3 ? "cta-pulse" : ""}`}
              >
                Take Action
              </button>
            </article>
          </div>
        </section>
        <section ref={exit} className="flex h-[70svh] items-end justify-center pb-10">
          <p className="text-[13px] font-medium text-ink-faint">Keep scrolling to return to the globe</p>
        </section>
      </main>

      <ActionModal chapter={chapter} open={modal === "action"} onClose={() => setModal(null)} />
    </>
  );
}
