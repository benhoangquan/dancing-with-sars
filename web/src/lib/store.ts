// Story state. Low-frequency values live in a zustand store; the per-frame flyover time lives in a
// separate vanilla store so subscribers can read it without re-rendering React.
import { create } from "zustand";
import { createStore } from "zustand/vanilla";
import type { StageMode } from "@/types/chapter";

export interface StoryState {
  chapterIdx: number;
  beatIdx: number;
  /** Mode chosen with the segmented control; null follows the beat. Cleared on chapter change. */
  pinnedMode: StageMode | null;
  /** Position of the radar swipe divider, 0 to 1. Reset to the beat's value when the beat changes. */
  swipe: number;
  drawerOpen: boolean;
  legendOpen: boolean;
  setActive: (chapterIdx: number, beatIdx: number, beatSwipe: number) => void;
  pinMode: (mode: StageMode | null) => void;
  setSwipe: (swipe: number) => void;
  setDrawerOpen: (open: boolean) => void;
  setLegendOpen: (open: boolean) => void;
}

export const useStory = create<StoryState>((set, get) => ({
  chapterIdx: 0,
  beatIdx: 0,
  pinnedMode: null,
  swipe: 0.5,
  drawerOpen: false,
  legendOpen: false,
  setActive: (chapterIdx, beatIdx, beatSwipe) => {
    const s = get();
    if (s.chapterIdx === chapterIdx && s.beatIdx === beatIdx) return;
    set({
      chapterIdx,
      beatIdx,
      swipe: beatSwipe,
      pinnedMode: s.chapterIdx === chapterIdx ? s.pinnedMode : null,
    });
  },
  pinMode: (pinnedMode) => set({ pinnedMode }),
  setSwipe: (swipe) => set({ swipe: Math.min(1, Math.max(0, swipe)) }),
  setDrawerOpen: (drawerOpen) => set({ drawerOpen }),
  setLegendOpen: (legendOpen) => set({ legendOpen }),
}));

/** Flyover time `t` in seconds and active-beat progress `p`, updated every animation frame. */
export const clock = createStore<{ t: number; p: number }>(() => ({ t: 0, p: 0 }));
