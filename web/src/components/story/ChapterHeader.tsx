import { formatCoordinate } from "@/lib/format";
import type { Chapter } from "@/types/chapter";

type Props = { chapter: Chapter; chapterIdx: number; total: number };

/** Full-screen chapter opener. The stage behind it shows the start of the chapter's flyover. */
export function ChapterHeader({ chapter, chapterIdx, total }: Props) {
  const [w, s, e, n] = chapter.aoi.bbox;
  return (
    <section data-section="header" data-chapter={chapterIdx} data-beat={0} aria-labelledby={`chapter-${chapter.slug}`} className="flex min-h-svh items-end px-4 pb-24 lg:px-16">
      <div className="max-w-3xl">
        <p className="tabular text-[13px] font-medium uppercase tracking-[0.1em]" style={{ color: chapter.accent }}>
          Chapter {chapterIdx + 1} of {total} · {chapter.kicker}
        </p>
        <h2 id={`chapter-${chapter.slug}`} className="display mt-4 text-[clamp(2.5rem,7vw,5.5rem)] font-semibold leading-[1.02] text-balance">
          {chapter.title}
        </h2>
        <p className="mt-5 max-w-2xl text-[19px] leading-snug text-ink-dim text-pretty">{chapter.dek}</p>
        <p className="tabular mt-6 text-[13px] text-ink-faint">{formatCoordinate((w + e) / 2, (s + n) / 2)}</p>
      </div>
    </section>
  );
}
