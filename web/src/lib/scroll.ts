// The scroll engine: each animation frame it finds the beat under the viewport center line, updates the
// story store, and advances the flyover clock. Runs in the browser only.
import { type SectionBox, locate } from "./beats";
import { FlyoverClock } from "./clock";
import { clock, useStory } from "./store";
import type { Chapter } from "@/types/chapter";

/** Start tracking `[data-section]` elements inside `root`. Returns a stop function. */
export function startStoryScroll(root: HTMLElement, chapters: Chapter[], prefersReducedMotion: () => boolean): () => void {
  const sections = [...root.querySelectorAll<HTMLElement>("[data-section]")].map((el) => ({
    el,
    kind: el.dataset.section as SectionBox["kind"],
    chapter: Number(el.dataset.chapter),
    beat: Number(el.dataset.beat),
  }));
  const flyoverClock = new FlyoverClock();
  let prev = performance.now();
  let raf = 0;

  const frame = (now: number) => {
    raf = requestAnimationFrame(frame);
    const dt = Math.min(0.1, (now - prev) / 1000);
    prev = now;
    const boxes: SectionBox[] = sections.map((s) => {
      const r = s.el.getBoundingClientRect();
      return { kind: s.kind, chapter: s.chapter, beat: s.beat, top: r.top, bottom: r.bottom };
    });
    const at = locate(boxes, window.innerHeight / 2);
    const beat = chapters[at.chapterIdx].beats[at.beatIdx];
    useStory.getState().setActive(at.chapterIdx, at.beatIdx, beat.stage.swipe);
    flyoverClock.reduced = prefersReducedMotion();
    const t = flyoverClock.update(now, dt, `${at.chapterIdx}:${at.beatIdx}`, beat, at.p);
    const s = clock.getState();
    if (s.t !== t || s.p !== at.p) clock.setState({ t, p: at.p });
  };
  raf = requestAnimationFrame(frame);
  const replay = () => flyoverClock.restart();
  window.addEventListener("sar:replay", replay);
  return () => {
    cancelAnimationFrame(raf);
    window.removeEventListener("sar:replay", replay);
  };
}
