// Pure logic that turns scroll position and beat data into stage state. No DOM, so it is unit-tested.
import type { Camera, Chapter, StageMode, Waypoint } from "@/types/chapter";
import { cameraAt } from "./camera";

export type Beat = Chapter["beats"][number];
export type FlyoverWindow = Beat["stage"]["flyover"];

export const clamp01 = (x: number) => Math.min(1, Math.max(0, x));

/** Flyover time for a scrub beat at scroll progress `p` (0 to 1). */
export const scrubTime = (f: FlyoverWindow, p: number) => f.from + (f.to - f.from) * clamp01(p);

/** Flyover time for a play-hold beat `elapsedSec` after it became active: plays at 1x, then holds at `to`. */
export const playHoldTime = (f: FlyoverWindow, elapsedSec: number) =>
  Math.min(f.to, f.from + Math.max(0, elapsedSec));

export interface SectionBox {
  kind: "hero" | "header" | "beat" | "outro";
  chapter: number;
  beat: number;
  top: number;
  bottom: number;
}
export interface Located {
  chapterIdx: number;
  beatIdx: number;
  /** Progress through the active beat, 0 to 1. */
  p: number;
}

/**
 * Which beat is under the viewport center line `y`, and how far through it.
 * Boxes are in document order. The hero and chapter headers count as progress 0 of the next beat,
 * the outro and anything below it as progress 1 of the last beat.
 */
export function locate(boxes: readonly SectionBox[], y: number): Located {
  if (!boxes.length) return { chapterIdx: 0, beatIdx: 0, p: 0 };
  const first = boxes[0];
  const last = boxes[boxes.length - 1];
  if (y < first.top) return { chapterIdx: first.chapter, beatIdx: first.beat, p: 0 };
  if (y >= last.bottom) return { chapterIdx: last.chapter, beatIdx: last.beat, p: 1 };
  const box = boxes.find((b) => y >= b.top && y < b.bottom) ?? last;
  const height = box.bottom - box.top;
  const p = box.kind === "beat" && height > 0 ? clamp01((y - box.top) / height) : box.kind === "outro" ? 1 : 0;
  return { chapterIdx: box.chapter, beatIdx: box.beat, p };
}

export interface PaneLayers {
  /** Layer ids shown on map A, bottom to top. */
  a: string[];
  /** Layer ids shown on map B, bottom to top. Empty when B is hidden. */
  b: string[];
}

/**
 * Which layers each map shows for a beat in a mode. Overlays (for example the HV drop) are the result of
 * comparing the two scenes, so they sit on the right-hand (after) map only; the left side stays a clean "before".
 */
export function paneLayers(beat: Beat, mode: StageMode): PaneLayers {
  const s = beat.stage;
  const overlays = s.overlays ?? [];
  const flyLayer = s.flyoverLayer ?? s.left;
  if (mode === "flyover") return { a: [flyLayer], b: [] };
  if (mode === "radar") return { a: [s.left], b: [s.right, ...overlays] };
  return { a: [flyLayer], b: [s.right, ...overlays] };
}

/** Camera for radar mode: the beat's own camera, else where the flyover is at the end of the beat's window. */
export const radarCamera = (beat: Beat, waypoints: readonly Waypoint[]): Camera =>
  beat.stage.camera ?? cameraAt(waypoints, beat.stage.flyover.to);

/** Layer ids that any beat in the chapter can show, for provenance and preloading. */
export const chapterLayerIds = (chapter: Chapter) => new Set(chapter.generated.layers.map((l) => l.id));
