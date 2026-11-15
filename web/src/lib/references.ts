// Everyday references that pair with a figure in the story ("374 ha · about 1.1 × Central Park"). Each value
// is sourced; the comparison is computed here so no equivalence is typed by hand.
import type { ScaleReference } from "@/types/chapter";
import { formatNumber } from "./format";

export interface Reference {
  id: ScaleReference;
  /** Size in the figure's own unit (hectares, or none for formulas). */
  value?: number;
  name: string;
  source: { name: string; url: string };
}

export const REFERENCES: Record<ScaleReference, Reference> = {
  "football-pitch": {
    id: "football-pitch",
    value: 0.714,
    name: "football pitch",
    source: { name: "IFAB Laws of the Game, Law 1 (international pitches 100–110 × 64–75 m; 105 × 68 m used here)", url: "https://www.theifab.com/laws/latest/the-field-of-play/" },
  },
  "central-park": {
    id: "central-park",
    value: 341,
    name: "Central Park",
    source: { name: "Central Park Conservancy: 843 acres (341 ha)", url: "https://www.centralparknyc.org/about" },
  },
  manhattan: {
    id: "manhattan",
    value: 5869,
    name: "Manhattan",
    source: { name: "US Census Bureau, New York County land area (22.66 sq mi)", url: "https://www.census.gov/quickfacts/newyorkcountynewyork" },
  },
  "echo-power": {
    id: "echo-power",
    name: "radar echo strength",
    source: { name: "Decibels to power ratio: 10^(−dB/10)", url: "https://en.wikipedia.org/wiki/Decibel" },
  },
  "per-decade": {
    id: "per-decade",
    name: "per decade",
    source: { name: "Rate × 10 years", url: "https://en.wikipedia.org/wiki/Land_subsidence" },
  },
};

const times = (x: number) => `${formatNumber(x, x < 10 ? 1 : 0)} ×`;

/** The everyday comparison for `value` (in `unit`), for example "about 1.1 × Central Park". */
export function anchorText(ref: ScaleReference, value: number, unit: string): string {
  const r = REFERENCES[ref];
  switch (ref) {
    case "echo-power": {
      const ratio = 10 ** (-Math.abs(value) / 10);
      if (ratio <= 0.5) return `the echo fell to about 1/${Math.round(1 / ratio)} of its strength`;
      return `an echo about ${Math.round((1 - ratio) * 100)}% weaker`;
    }
    case "per-decade": {
      const cm = value * 10;
      return cm >= 100 ? `${formatNumber(cm / 100, 1)} m per decade` : `${formatNumber(cm, 0)} cm per decade`;
    }
    case "football-pitch":
      return `about ${formatNumber(Math.round(toHa(value, unit) / r.value!), 0)} football pitches`;
    default: {
      const n = toHa(value, unit) / r.value!;
      return n < 0.95 ? `about ${Math.round(n * 100)}% of ${r.name}` : `about ${times(n)} ${r.name}`;
    }
  }
}

const toHa = (value: number, unit: string) => (unit === "km2" ? value * 100 : value);
