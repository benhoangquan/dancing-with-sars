import { RichText } from "@/components/ui/RichText";
import type { Chapter } from "@/types/chapter";

type Props = { chapter: Chapter; chapterIdx: number; beatIdx: number };

/**
 * One scroll beat. The section is tall so scrolling through it scrubs the flyover; the frosted card stays
 * pinned in the middle of the screen (the bottom on narrow screens) while it does.
 */
export function NarrativeBeat({ chapter, chapterIdx, beatIdx }: Props) {
  const beat = chapter.beats[beatIdx];
  return (
    <section data-section="beat" data-chapter={chapterIdx} data-beat={beatIdx} aria-labelledby={`beat-${chapter.slug}-${beat.id}`} className="relative min-h-[150svh]">
      <div className="sticky top-0 flex h-svh items-center px-4 max-lg:items-end max-lg:pb-5 lg:px-16">
        <article className="glass pointer-events-auto w-full max-w-[420px] p-7 max-lg:max-w-none max-lg:p-5">
          <p className="tabular flex items-center justify-between text-[12px] font-medium uppercase tracking-[0.08em]" style={{ color: chapter.accent }}>
            <span>{beat.eyebrow ?? chapter.kicker}</span>
            <span className="text-ink-faint">
              {beatIdx + 1} / {chapter.beats.length}
            </span>
          </p>
          <h2 id={`beat-${chapter.slug}-${beat.id}`} className="display mt-3 text-[28px] font-semibold leading-[1.1] max-lg:text-[22px]">
            {beat.headline}
          </h2>
          <p className="mt-3 text-[17px] leading-[1.47] text-ink/85 max-lg:text-[15px]">
            <RichText text={beat.body} stats={chapter.generated.stats} />
          </p>
        </article>
      </div>
    </section>
  );
}
