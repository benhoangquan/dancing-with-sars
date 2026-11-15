"use client";

import { Fragment, useEffect, useRef } from "react";
import { ActionDrawer } from "@/components/action/ActionDrawer";
import { Stage } from "@/components/stage/Stage";
import { effectiveMode, paneLayers } from "@/lib/beats";
import { startStoryScroll } from "@/lib/scroll";
import { useStory } from "@/lib/store";
import type { Chapter } from "@/types/chapter";
import { ChapterHeader } from "./ChapterHeader";
import { Hero } from "./Hero";
import { Hud } from "./Hud";
import { NarrativeBeat } from "./NarrativeBeat";
import { Outro } from "./Outro";

/** The whole experience: a fixed stage, a fixed HUD, and a column of scrolling sections over them. */
export function StoryViewport({ chapters }: { chapters: Chapter[] }) {
  const root = useRef<HTMLDivElement>(null);
  const chapterIdx = useStory((s) => s.chapterIdx);
  const beatIdx = useStory((s) => s.beatIdx);
  const pinned = useStory((s) => s.pinnedMode);
  const drawerOpen = useStory((s) => s.drawerOpen);
  const setDrawerOpen = useStory((s) => s.setDrawerOpen);

  useEffect(() => {
    if (!root.current) return;
    return startStoryScroll(root.current, chapters, () => window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }, [chapters]);

  const chapter = chapters[chapterIdx];
  const beat = chapter.beats[beatIdx];
  const mode = effectiveMode(beat, pinned);
  const panes = paneLayers(beat, mode);
  const visibleLayerIds = [...new Set([...panes.a, ...panes.b])];

  return (
    <>
      <Stage chapters={chapters} />
      <Hud chapter={chapter} beatIdx={beatIdx} beat={beat} mode={mode} visibleLayerIds={visibleLayerIds} />
      <main id="top" ref={root} data-story-root className="pointer-events-none relative z-20">
        <Hero chapters={chapters.length} />
        {chapters.map((c, ci) => (
          <Fragment key={c.slug}>
            <ChapterHeader chapter={c} chapterIdx={ci} total={chapters.length} />
            {c.beats.map((b, bi) => (
              <NarrativeBeat key={b.id} chapter={c} chapterIdx={ci} beatIdx={bi} />
            ))}
          </Fragment>
        ))}
        <Outro chapters={chapters} />
      </main>
      <ActionDrawer chapter={chapter} open={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </>
  );
}
