// Pure scene logic: the three-state machine, the URL hash route, acts within a chapter, and the overlay
// matrix that keeps UI pieces from colliding. No DOM, so it is unit-tested.

export type Scene = "HERO_GLOBE" | "HOTSPOT_GLOBE" | "PLACE_CHAPTER";
export type Act = 1 | 2 | 3;
export type Modal = "discovery" | "action" | null;

/** `#place=rondonia` -> "rondonia"; anything else -> null. Unknown slugs are null too. */
export function parsePlace(hash: string, slugs: readonly string[]): string | null {
  const m = /(?:^#|&)place=([a-z0-9-]{2,40})(?:&|$)/.exec(hash);
  return m && slugs.includes(m[1]) ? m[1] : null;
}

export const placeHash = (slug: string | null) => (slug ? `#place=${slug}` : "");

/** The scene a fresh page load starts in. */
export const initialScene = (place: string | null): Scene => (place ? "PLACE_CHAPTER" : "HERO_GLOBE");

/** Act of a beat: the first beat is Act I (flyover), the last is Act III (action), the rest Act II (radar). */
export function actOf(beatIdx: number, beats: number): Act {
  if (beatIdx <= 0) return 1;
  if (beatIdx >= beats - 1) return 3;
  return 2;
}

/** Progress through the hero (0 to 1) -> where the headline and globe are. Settles at 1. */
export function heroPose(p: number) {
  const t = Math.min(1, Math.max(0, p));
  const e = 1 - (1 - t) ** 3; // ease-out
  // The globe starts low on the page under the headline (top padding as a share of the height) and rises to centre.
  return { headlineY: -28 * e, headlineOpacity: 1 - e, zoom: 1.15 + 0.85 * e, pitch: 0, padTop: 0.5 * (1 - e), settled: t >= 0.999 };
}

export interface OverlayInput {
  scene: Scene;
  act: Act;
  dragging: boolean;
  popover: string | null;
  modal: Modal;
}

export interface OverlayState {
  /** Beat card opacity: dimmed while the user works the swipe or reads a landmark popover. */
  cardOpacity: number;
  legend: boolean;
  landmarks: boolean;
  backToGlobe: "hidden" | "disabled" | "enabled";
  scrollLocked: boolean;
  audioGain: number;
}

/** The mutual-exclusion matrix of the layout, as one function. */
export function overlays(s: OverlayInput): OverlayState {
  const inPlace = s.scene === "PLACE_CHAPTER";
  return {
    cardOpacity: s.dragging || s.popover ? 0.25 : 1,
    legend: inPlace && s.act === 2 && !s.modal,
    landmarks: inPlace && s.act === 2,
    backToGlobe: s.scene === "HERO_GLOBE" ? "hidden" : inPlace ? "enabled" : "disabled",
    scrollLocked: s.scene === "HOTSPOT_GLOBE" || s.modal !== null,
    audioGain: s.modal ? 0.5 : 1,
  };
}

/** A popover closes once the page has scrolled more than this many pixels since it opened. */
export const POPOVER_SCROLL_CLOSE_PX = 40;
export const shouldClosePopover = (scrollAtOpen: number, scrollNow: number) =>
  Math.abs(scrollNow - scrollAtOpen) > POPOVER_SCROLL_CLOSE_PX;
