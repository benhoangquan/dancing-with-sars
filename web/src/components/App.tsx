"use client";

import dynamic from "next/dynamic";
import { useReducedMotion } from "motion/react";
import { useCallback, useEffect, useState } from "react";
import { DiscoveryModal } from "@/components/globe/DiscoveryModal";
import { HeroBlurHeader } from "@/components/globe/HeroBlurHeader";
import { TopNavBar } from "@/components/nav/TopNavBar";
import { PlaceChapter } from "@/components/place/PlaceChapter";
import { useSoundscape } from "@/lib/audio";
import { actOf, overlays, parsePlace, placeHash } from "@/lib/scenes";
import { useStory } from "@/lib/store";
import { WATCHED } from "@/lib/watched";
import type { Chapter } from "@/types/chapter";

const GlobeStage = dynamic(() => import("@/components/globe/GlobeStage"), { ssr: false });

/** The whole experience: hero globe, hotspot globe and one place at a time, kept in step with `#place=`. */
export function App({ chapters }: { chapters: Chapter[] }) {
  const reduced = useReducedMotion() ?? false;
  const scene = useStory((s) => s.scene);
  const place = useStory((s) => s.place);
  const beatIdx = useStory((s) => s.beatIdx);
  const modal = useStory((s) => s.modal);
  const [highlight, setHighlight] = useState<string | null>(null);
  const chapter = chapters.find((c) => c.slug === place) ?? null;
  const act = chapter ? actOf(beatIdx, chapter.beats.length) : 1;
  const o = overlays({ scene, act, dragging: false, popover: null, modal });
  const slugs = chapters.map((c) => c.slug);

  // Hash route: a link to #place=demak opens Demak; back and forward move between globe and place.
  useEffect(() => {
    const sync = () => {
      const want = parsePlace(window.location.hash, slugs);
      const s = useStory.getState();
      if (want && want !== s.place) s.enterPlace(want, null);
      if (!want && s.scene === "PLACE_CHAPTER") s.leavePlace();
    };
    sync();
    window.addEventListener("hashchange", sync);
    return () => window.removeEventListener("hashchange", sync);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => {
    const want = placeHash(place);
    if (window.location.hash !== want) history.pushState(null, "", want || window.location.pathname + window.location.search);
  }, [place]);

  // Light canvas on the globe, black stage in a place; page scroll locked on the hotspot globe and under modals.
  useEffect(() => {
    const html = document.documentElement;
    html.dataset.scene = scene;
    html.style.overflow = o.scrollLocked ? "hidden" : "";
  }, [scene, o.scrollLocked]);

  // Grey pins open the discovery sheet at their note.
  useEffect(() => {
    const onWatched = (e: Event) => {
      setHighlight((e as CustomEvent<string>).detail);
      useStory.getState().setModal("discovery");
    };
    window.addEventListener("sar:watched", onWatched);
    return () => window.removeEventListener("sar:watched", onWatched);
  }, []);

  useSoundscape(chapter, o.audioGain);

  const toGlobe = useCallback(() => {
    useStory.getState().leavePlace();
    window.scrollTo(0, 0);
  }, []);

  return (
    <>
      {scene !== "PLACE_CHAPTER" && <GlobeStage chapters={chapters} watched={WATCHED} reduced={reduced} />}
      {scene === "HERO_GLOBE" && <HeroBlurHeader places={chapters.length} />}
      {scene === "HOTSPOT_GLOBE" && (
        <div data-story-root className="pointer-events-none fixed inset-x-0 bottom-8 z-20 text-center">
          <p className="text-[15px] font-medium text-light-ink-dim">Drag to turn the Earth. Pick a red pin to open its story.</p>
        </div>
      )}
      {chapter && scene === "PLACE_CHAPTER" && <PlaceChapter key={chapter.slug} chapter={chapter} onExit={toGlobe} />}
      <TopNavBar act={act} onGlobe={toGlobe} />
      <DiscoveryModal chapters={chapters} watched={WATCHED} highlight={highlight} />
    </>
  );
}
