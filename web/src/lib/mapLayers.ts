// Map style and raster layer management for the radar maps. Pure helpers are unit-tested; the
// LayerManager touches a MapLibre map and runs in the browser only.
import type { Map as MlMap, RasterDEMSourceSpecification, StyleSpecification } from "maplibre-gl";
import type { BBox, Layer } from "@/types/chapter";
import { customColorFunction, isCustomRamp } from "./ramps";

export const HILLSHADE_LAYER = "hillshade";
export const TERRAIN_SOURCE = "terrain";
// MapLibre advises separate sources for 3D terrain and hillshade, so each gets its own copy of the DEM.
export const HILLSHADE_SOURCE = "hillshade-dem";
const FADE_MS = 600;
const rasterId = (id: string) => `lyr-${id}`;
const sourceId = (id: string) => `src-${id}`;

export const sourceIdFor = sourceId;
export const layerIdFor = rasterId;

/** Stacking order: imagery under radar under coherence under displacement under change masks. */
export function layerRank(kind: Layer["kind"]): number {
  switch (kind) {
    case "optical":
      return 0;
    case "sar-composite":
    case "sar-db":
      return 1;
    case "coherence":
      return 2;
    case "displacement":
    case "speed":
      return 3;
    case "change":
      return 4;
  }
}

/** The id of the existing layer a new layer of `rank` goes under, else `fallbackId`. */
export function insertBefore(existing: { id: string; rank: number }[], rank: number, fallbackId: string): string {
  const above = existing.filter((e) => e.rank > rank).sort((a, b) => a.rank - b.rank)[0];
  return above ? above.id : fallbackId;
}

type Render = Layer["render"];

/** The `#color:` fragment the COG protocol uses to color a single-band float layer; empty for RGBA and for project ramps. */
export function colorFragment(render: Render): string {
  if (render.type !== "ramp" || isCustomRamp(render)) return "";
  return `#color:${render.scheme},${render.domain[0]},${render.domain[1]},c`;
}

/** `cog://` source URL for a layer. `toAbsolute` turns an AssetPath into an absolute URL. */
export const cogSourceUrl = (layer: Layer, toAbsolute: (path: string) => string) =>
  `cog://${toAbsolute(layer.cog)}${colorFragment(layer.render)}`;

/** Corner order MapLibre's image source expects: top-left, top-right, bottom-right, bottom-left. */
export const imageCorners = ([w, s, e, n]: BBox): [[number, number], [number, number], [number, number], [number, number]] => [
  [w, n],
  [e, n],
  [e, s],
  [w, s],
];

const DEM: RasterDEMSourceSpecification = {
  type: "raster-dem",
  tiles: ["https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"],
  encoding: "terrarium",
  tileSize: 256,
  maxzoom: 15,
  attribution: "Terrain: Mapzen, AWS Open Data",
};

/** Black stage, terrain from free AWS tiles, a light hillshade over the imagery, and a black sky. */
export function baseStyle(): StyleSpecification {
  return {
    version: 8,
    sources: {
      [TERRAIN_SOURCE]: DEM,
      [HILLSHADE_SOURCE]: DEM,
    },
    layers: [
      { id: "stage", type: "background", paint: { "background-color": "#000000" } },
      {
        id: HILLSHADE_LAYER,
        type: "hillshade",
        source: HILLSHADE_SOURCE,
        paint: {
          "hillshade-exaggeration": 0.45,
          "hillshade-shadow-color": "rgba(0,0,0,0.85)",
          "hillshade-highlight-color": "rgba(255,255,255,0.14)",
          "hillshade-accent-color": "rgba(0,0,0,0.35)",
        },
      },
    ],
    sky: {
      "sky-color": "#0a0a0c",
      "horizon-color": "#000000",
      "fog-color": "#000000",
      "sky-horizon-blend": 0.5,
      "horizon-fog-blend": 0.8,
      "fog-ground-blend": 0.2,
    },
  };
}

/** Creates, shows and hides one map's raster layers for a chapter. Layers fade; hidden layers stop loading tiles. */
export class LayerManager {
  private byId: Map<string, Layer>;
  private created = new Set<string>();
  private fellBack = new Set<string>();
  private hideTimers = new Map<string, ReturnType<typeof setTimeout>>();
  private wanted: string[] = [];

  constructor(
    private map: MlMap,
    layers: Layer[],
    private toAbsolute: (path: string) => string,
    private toSite: (path: string) => string,
    /** The COG protocol's `setColorFunction`, which draws project ramps that `#color:` does not know. */
    private setColorFunction?: (url: string, fn: ((pixel: ArrayLike<number>, color: Uint8ClampedArray) => void) | undefined) => void,
  ) {
    this.byId = new Map(layers.map((l) => [l.id, l]));
    map.on("error", this.onError);
  }

  /** Show exactly these layers (ids in stacking input order); fade out every other created layer. */
  setVisible(ids: string[]) {
    this.wanted = ids;
    const want = new Set(ids);
    for (const id of ids) this.show(id);
    for (const id of this.created) if (!want.has(id)) this.hide(id);
  }

  dispose() {
    this.map.off("error", this.onError);
    for (const t of this.hideTimers.values()) clearTimeout(t);
    for (const id of this.created) this.remove(id);
    this.created.clear();
  }

  private ensure(id: string) {
    const layer = this.byId.get(id);
    if (!layer || this.created.has(id)) return;
    this.addSource(layer, false);
    this.addLayer(layer);
    this.created.add(id);
  }

  private addSource(layer: Layer, asImage: boolean) {
    const sid = sourceId(layer.id);
    if (asImage) {
      this.map.addSource(sid, { type: "image", url: this.toSite(layer.preview), coordinates: imageCorners(layer.bounds) });
    } else {
      const fn = customColorFunction(layer.render);
      if (fn) this.setColorFunction?.(this.toAbsolute(layer.cog), fn);
      this.map.addSource(sid, { type: "raster", url: cogSourceUrl(layer, this.toAbsolute), tileSize: 256 });
    }
  }

  private addLayer(layer: Layer) {
    const existing = [...this.created].map((cid) => ({ id: rasterId(cid), rank: layerRank(this.byId.get(cid)!.kind) }));
    this.map.addLayer(
      {
        id: rasterId(layer.id),
        type: "raster",
        source: sourceId(layer.id),
        layout: { visibility: "none" },
        paint: { "raster-opacity": 0, "raster-opacity-transition": { duration: FADE_MS, delay: 0 }, "raster-fade-duration": 0 },
      },
      insertBefore(existing, layerRank(layer.kind), HILLSHADE_LAYER),
    );
  }

  private show(id: string) {
    this.ensure(id);
    if (!this.created.has(id)) return;
    const timer = this.hideTimers.get(id);
    if (timer) clearTimeout(timer);
    this.hideTimers.delete(id);
    const lid = rasterId(id);
    this.map.setLayoutProperty(lid, "visibility", "visible");
    // Set the opacity on the next frame so the transition runs from 0.
    requestAnimationFrame(() => {
      if (this.map.getLayer(lid) && this.wanted.includes(id)) this.map.setPaintProperty(lid, "raster-opacity", 1);
    });
  }

  private hide(id: string) {
    const lid = rasterId(id);
    if (!this.map.getLayer(lid) || this.hideTimers.has(id)) return;
    this.map.setPaintProperty(lid, "raster-opacity", 0);
    this.hideTimers.set(
      id,
      setTimeout(() => {
        this.hideTimers.delete(id);
        if (this.map.getLayer(lid) && !this.wanted.includes(id)) this.map.setLayoutProperty(lid, "visibility", "none");
      }, FADE_MS + 50),
    );
  }

  private remove(id: string) {
    const lid = rasterId(id);
    if (this.map.getLayer(lid)) this.map.removeLayer(lid);
    if (this.map.getSource(sourceId(id))) this.map.removeSource(sourceId(id));
  }

  /** If a COG source fails, swap in the PNG preview of the same extent so the chapter still shows the layer. */
  private onError = (e: { sourceId?: string; error?: Error }) => {
    const sid = e.sourceId;
    if (!sid?.startsWith("src-")) return;
    const id = sid.slice(4);
    const layer = this.byId.get(id);
    if (!layer || this.fellBack.has(id) || !this.created.has(id)) return;
    this.fellBack.add(id);
    console.warn(`COG for layer ${id} failed (${e.error?.message}); using its PNG preview`);
    this.remove(id);
    this.addSource(layer, true);
    this.addLayer(layer);
    if (this.wanted.includes(id)) this.show(id);
  };
}
