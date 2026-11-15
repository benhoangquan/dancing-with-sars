// deck.gl layers for a beat's annotations: pulsing pins, outlined areas and labels. They draw on a
// separate canvas above the map, so each point is lifted to the terrain height from MapLibre.
import { PathLayer, ScatterplotLayer, TextLayer } from "@deck.gl/layers";
import type { Layer as DeckLayer } from "@deck.gl/core";
import type { Annotation } from "@/types/chapter";

export type Elevation = (lon: number, lat: number) => number;
type Rgb = [number, number, number];

const FONT = '-apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, "Segoe UI", Roboto, sans-serif';

export function hexToRgb(hex: string): Rgb {
  return [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16)) as Rgb;
}

/** Points along a closed ring with extra vertices on each edge, so the outline follows the terrain. */
export function densifyRing(ring: number[][], perEdge = 12): [number, number][] {
  const out: [number, number][] = [];
  for (let i = 0; i < ring.length - 1; i++) {
    const [x0, y0] = ring[i];
    const [x1, y1] = ring[i + 1];
    for (let k = 0; k < perEdge; k++) out.push([x0 + ((x1 - x0) * k) / perEdge, y0 + ((y1 - y0) * k) / perEdge]);
  }
  out.push([ring[ring.length - 1][0], ring[ring.length - 1][1]]);
  return out;
}

/** Mean of a ring's distinct corners. */
export const ringCentroid = (ring: number[][]): [number, number] => {
  const pts = ring.slice(0, -1);
  return [pts.reduce((a, p) => a + p[0], 0) / pts.length, pts.reduce((a, p) => a + p[1], 0) / pts.length];
};

/** Where an area's label goes: centered over the outline's northern edge, so it clears pin labels inside the area. */
export const ringLabelAnchor = (ring: number[][]): [number, number] => {
  const lons = ring.map((p) => p[0]);
  const lats = ring.map((p) => p[1]);
  return [(Math.min(...lons) + Math.max(...lons)) / 2, Math.max(...lats)];
};

/** Layers for the annotations at animation `phase` (0 to 1, loops) in the chapter accent color. */
export function annotationLayers(annotations: readonly Annotation[], accent: string, phase: number, elevation: Elevation): DeckLayer[] {
  const rgb = hexToRgb(accent);
  const pins: { position: [number, number, number]; label: string }[] = [];
  const areas: { path: [number, number, number][]; label: string; at: [number, number, number] }[] = [];
  for (const a of annotations) {
    if (a.geometry.type === "Point") {
      const [lon, lat] = a.geometry.coordinates;
      pins.push({ position: [lon, lat, elevation(lon, lat)], label: a.label });
    } else {
      const ring = a.geometry.coordinates[0];
      const [clon, clat] = ringLabelAnchor(ring);
      areas.push({
        path: densifyRing(ring).map(([lon, lat]) => [lon, lat, elevation(lon, lat)]),
        label: a.label,
        at: [clon, clat, elevation(clon, clat)],
      });
    }
  }
  const labels = [...pins.map((p) => ({ position: p.position, text: p.label, dy: -26 })), ...areas.map((a) => ({ position: a.at, text: a.label, dy: -16 }))];
  return [
    new PathLayer({
      id: "annotation-areas",
      data: areas,
      getPath: (d) => d.path,
      getColor: [...rgb, 235],
      getWidth: 2,
      widthUnits: "pixels",
      capRounded: true,
      jointRounded: true,
    }),
    new ScatterplotLayer({
      id: "annotation-pulse",
      data: pins,
      getPosition: (d) => d.position,
      getRadius: 9 + 20 * phase,
      radiusUnits: "pixels",
      stroked: true,
      filled: false,
      getLineColor: [...rgb, Math.round(200 * (1 - phase))],
      getLineWidth: 2,
      lineWidthUnits: "pixels",
      updateTriggers: { getRadius: phase, getLineColor: phase },
    }),
    new ScatterplotLayer({
      id: "annotation-pins",
      data: pins,
      getPosition: (d) => d.position,
      getRadius: 5,
      radiusUnits: "pixels",
      getFillColor: rgb,
      stroked: true,
      getLineColor: [28, 28, 30, 255],
      getLineWidth: 2,
      lineWidthUnits: "pixels",
    }),
    new TextLayer({
      id: "annotation-labels",
      data: labels,
      getPosition: (d) => d.position,
      getText: (d) => d.text,
      getPixelOffset: (d) => [0, d.dy],
      getSize: 13,
      getColor: [245, 245, 247, 255],
      fontFamily: FONT,
      fontWeight: 600,
      background: true,
      getBackgroundColor: [28, 28, 30, 225],
      backgroundPadding: [8, 4, 8, 4],
      getBorderColor: [255, 255, 255, 40],
      getBorderWidth: 1,
      characterSet: "auto",
    }),
  ];
}
