"use client";

import { BackscatterSparkline } from "@/components/readout/BackscatterSparkline";
import { RichText } from "@/components/ui/RichText";
import { overlays } from "@/lib/scenes";
import { useStory } from "@/lib/store";
import { chapterTokens } from "@/lib/tokens";
import type { Chapter } from "@/types/chapter";

type Props = { chapter: Chapter; beatIdx: number };

/**
 * An Act II beat: a dark frosted card at the bottom left with the narrative, each figure paired with its everyday
 * comparison, and the radar series in the measured beat. It fades to a quarter while the reader drags the swipe
 * or reads a landmark popover, so the map stays in view.
 */
export function BeatGlassCard({ chapter, beatIdx }: Props) {
  const beat = chapter.beats[beatIdx];
  const active = useStory((s) => s.beatIdx === beatIdx);
  const dragging = useStory((s) => s.dragging);
  const popover = useStory((s) => s.popover);
  const { cardOpacity } = overlays({ scene: "PLACE_CHAPTER", act: 2, dragging: active && dragging, popover: active ? popover : null, modal: null });
  return (
    <section data-section="beat" data-chapter={0} data-beat={beatIdx} aria-labelledby={`beat-${beat.id}`} className="relative min-h-[130svh]">
      <div className="sticky top-0 flex h-svh items-end px-6 pb-8 max-sm:px-3 max-sm:pb-4">
        <article
          className="beat-card glass-dark pointer-events-auto w-full max-w-[400px] p-6 transition-opacity duration-[240ms] max-sm:max-w-none max-sm:p-5"
          style={{ opacity: cardOpacity }}
          data-beat-card={beat.id}
        >
          <p className="tabular flex items-center justify-between text-[12px] font-semibold uppercase tracking-[0.08em]" style={{ color: chapter.accent }}>
            <span>{beat.eyebrow ?? chapter.kicker}</span>
            <span className="text-ink-faint">
              {beatIdx} / {chapter.beats.length - 2}
            </span>
          </p>
          <h2 id={`beat-${beat.id}`} className="display mt-2 text-[26px] font-semibold leading-[1.12] max-sm:text-[21px]">
            {beat.headline}
          </h2>
          <p className="mt-2 text-[16px] leading-[1.47] text-ink/85 max-sm:text-[15px]">
            <RichText text={beat.body} ctx={chapterTokens(chapter)} />
          </p>
          {beat.readout && (
            <div className="mt-4">
              <BackscatterSparkline key={`${chapter.slug}-${beat.id}`} chapter={chapter} readout={beat.readout} />
            </div>
          )}
        </article>
      </div>
    </section>
  );
}
