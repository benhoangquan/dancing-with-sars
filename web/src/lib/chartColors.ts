// Chart colors. The vivid chapter accents (manifest `accent`) are for UI chrome. Data marks use these
// steps of the same hues, lowered to OKLCH lightness 0.66 so they sit in the dark-mode band, and a
// neutral gray for the reference series. All were checked with the dataviz skill's validate_palette.js
// against the card surface (#1c1c1e): lightness band, chroma floor, adjacent-pair CVD separation,
// normal-vision floor and contrast. The gray's own chroma is zero by design (de-emphasis, not a hue).
import type { Chapter } from "@/types/chapter";

export const CARD_SURFACE = "#1c1c1e";
export const REFERENCE_GRAY = "#6e6e73";

export const CHART_COLOR: Record<Chapter["theme"], string> = {
  forest: "#00b040",
  fire: "#cc7e03",
  ground: "#27a0cb",
  water: "#27a0cb",
  ice: "#27a0cb",
};
