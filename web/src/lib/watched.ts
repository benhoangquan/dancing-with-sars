// Catalog places that were fetched and analyzed but gave no change we can defend. They sit on the hotspot globe
// as inactive pins, so the reader sees where NISAR looked and why there is no chapter yet. The reasons are in
// docs/decisions.md ("milestone 3, the other catalog locations").
export interface WatchedPlace {
  id: string;
  name: string;
  iso3: string;
  pin: [number, number];
  note: string;
}

export const WATCHED: WatchedPlace[] = [
  {
    id: "madre-de-dios",
    name: "Madre de Dios",
    iso3: "PER",
    pin: [-70.25, -12.85],
    note: "Checked with NISAR, 2026: the change patches were no larger than radar speckle, so there is no mining or clearing signal to report yet.",
  },
  {
    id: "sundarbans",
    name: "Sundarbans",
    iso3: "BGD",
    pin: [89.03, 22.0],
    note: "Checked with NISAR, 2026: the only drop came from the edge of one radar pass. The mangroves showed no measurable change between June and September.",
  },
  {
    id: "alaska",
    name: "Yukon–Kuskokwim Delta",
    iso3: "USA",
    pin: [-164.0, 61.2],
    note: "Checked with NISAR, 2026: scattered three-hectare specks, no thaw slump, burn or drained lake to point at yet.",
  },
  {
    id: "greenland",
    name: "Sermeq Kujalleq",
    iso3: "GRL",
    pin: [-49.75, 69.2],
    note: "Checked with NISAR, 2026: the glacier is too fast for the offset search window, and pairs did not agree, so speeds are not published yet.",
  },
  {
    id: "san-joaquin",
    name: "San Joaquin Valley",
    iso3: "USA",
    pin: [-119.5, 36.15],
    note: "Checked with NISAR, 2026: interferograms over four months were not yet reliable enough to publish subsidence.",
  },
];
