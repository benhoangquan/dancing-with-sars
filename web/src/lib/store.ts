// Story state. Low-frequency values live in a zustand store; the per-frame flyover time lives in a
// separate vanilla store so subscribers can read it without re-rendering React.
import { create } from "zustand";
import { createStore } from "zustand/vanilla";
import type { Modal, Scene } from "./scenes";

/** Globe camera saved when a place opens, restored when the reader returns to the globe. */
export interface GlobeView {
  center: [number, number];
  zoom: number;
  bearing: number;
  pitch: number;
}

export interface StoryState {
  scene: Scene;
  /** Slug of the open place chapter, or null on the globe. */
  place: string | null;
  savedGlobeView: GlobeView | null;
  /** Place the reader just left, so the globe can zoom out from it. */
  leftPlace: string | null;
  /** Always 0 inside a place: the scroll engine tracks one chapter at a time. */
  chapterIdx: number;
  beatIdx: number;
  /** Position of the radar swipe divider, 0 to 1. Reset to the beat's value when the beat changes. */
  swipe: number;
  dragging: boolean;
  popover: string | null;
  modal: Modal;
  soundOn: boolean;
  legendOpen: boolean;
  setScene: (scene: Scene) => void;
  enterPlace: (slug: string, view: GlobeView | null) => void;
  leavePlace: () => void;
  setActive: (chapterIdx: number, beatIdx: number, beatSwipe: number) => void;
  setSwipe: (swipe: number) => void;
  setDragging: (dragging: boolean) => void;
  setPopover: (id: string | null) => void;
  setModal: (modal: Modal) => void;
  setSoundOn: (on: boolean) => void;
  setLegendOpen: (open: boolean) => void;
}

export const useStory = create<StoryState>((set, get) => ({
  scene: "HERO_GLOBE",
  place: null,
  savedGlobeView: null,
  leftPlace: null,
  chapterIdx: 0,
  beatIdx: 0,
  swipe: 0.5,
  dragging: false,
  popover: null,
  modal: null,
  soundOn: false,
  legendOpen: false,
  setScene: (scene) => set({ scene }),
  enterPlace: (place, view) =>
    set({ scene: "PLACE_CHAPTER", place, savedGlobeView: view ?? get().savedGlobeView, beatIdx: 0, chapterIdx: 0, popover: null, modal: null }),
  leavePlace: () => set((s) => ({ scene: "HOTSPOT_GLOBE", leftPlace: s.place, place: null, popover: null, modal: null, dragging: false })),
  setActive: (chapterIdx, beatIdx, beatSwipe) => {
    const s = get();
    if (s.chapterIdx === chapterIdx && s.beatIdx === beatIdx) return;
    set({ chapterIdx, beatIdx, swipe: beatSwipe, popover: null });
  },
  setSwipe: (swipe) => set({ swipe: Math.min(1, Math.max(0, swipe)) }),
  setDragging: (dragging) => set({ dragging }),
  setPopover: (popover) => set({ popover }),
  setModal: (modal) => set({ modal, popover: null }),
  setSoundOn: (soundOn) => set({ soundOn }),
  setLegendOpen: (legendOpen) => set({ legendOpen }),
}));

/** Flyover time `t` in seconds and active-beat progress `p`, updated every animation frame. */
export const clock = createStore<{ t: number; p: number }>(() => ({ t: 0, p: 0 }));

/** Scroll progress through the hero, 0 to 1, updated on scroll. */
export const heroClock = createStore<{ p: number }>(() => ({ p: 0 }));
