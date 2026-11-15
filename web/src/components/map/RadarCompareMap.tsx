"use client";

import "maplibre-gl/dist/maplibre-gl.css";
import type { MapboxOverlay } from "@deck.gl/mapbox";
import type { IControl, Map as MlMap } from "maplibre-gl";
import { useEffect, useRef, useState } from "react";
import { annotationLayers } from "@/lib/annotations";
import { absoluteAssetUrl, assetUrl } from "@/lib/asset";
import { type Beat, paneLayers, radarCamera } from "@/lib/beats";
import { cameraAt } from "@/lib/camera";
import { springEase } from "@/lib/ease";
import { LayerManager, TERRAIN_SOURCE, baseStyle } from "@/lib/mapLayers";
import { clock } from "@/lib/store";
import { useMediaQuery } from "@/lib/useMediaQuery";
import type { Camera, Chapter, StageMode } from "@/types/chapter";

type Props = {
  chapter: Chapter;
  beat: Beat;
  mode: StageMode;
  reduced: boolean;
  /** A pre-rendered flyover video covers pane A (and the live map there is hidden). */
  videoActive: boolean;
};

interface Runtime {
  setColorFunction: ConstructorParameters<typeof LayerManager>[4];
  a: MlMap;
  b: MlMap;
  overlayA: MapboxOverlay;
  overlayB: MapboxOverlay;
  mgrA?: LayerManager;
  mgrB?: LayerManager;
}

let protocolRegistered = false;
// Inline, because MapLibre's stylesheet sets `.maplibregl-map { position: relative }` and would beat a class.
const FILL = { position: "absolute", inset: 0 } as const;
const CAMERA_MS = 1600;

const cameraOf = (m: MlMap): Camera => ({
  center: m.getCenter().toArray() as [number, number],
  zoom: m.getZoom(),
  pitch: m.getPitch(),
  bearing: m.getBearing(),
});

/** Plain-English tag for a pane: the label of the layer it shows. */
function PaneTag({ side, text }: { side: "left" | "right"; text?: string }) {
  if (!text) return null;
  return (
    <span
      className={`glass-data pointer-events-none absolute top-[4.5rem] z-10 rounded-full! px-3 py-1 text-[12px] font-medium text-ink-dim max-lg:hidden ${
        side === "left" ? "left-5" : "right-5"
      }`}
    >
      {text}
    </span>
  );
}

/**
 * Two MapLibre maps that live for the whole page. Map A shows the left layers; map B shows the right layers
 * (clipped by the swipe divider in radar mode, beside A in split mode). Cameras are driven by the flyover
 * clock in flyover and split modes, and by the beat's own camera in radar mode.
 */
export default function RadarCompareMap({ chapter, beat, mode, reduced, videoActive }: Props) {
  const elA = useRef<HTMLDivElement>(null);
  const elB = useRef<HTMLDivElement>(null);
  const rt = useRef<Runtime | null>(null);
  const modeRef = useRef(mode);
  useEffect(() => {
    modeRef.current = mode;
  }, [mode]);
  const [ready, setReady] = useState(false);
  const finePointer = useMediaQuery("(pointer: fine)");
  const flyover = chapter.generated.flyover;

  // Create both maps once, in the browser only.
  useEffect(() => {
    let cancelled = false;
    let cleanup = () => {};
    (async () => {
      const [ml, cog, deck] = await Promise.all([
        import("maplibre-gl"),
        import("@geomatico/maplibre-cog-protocol"),
        import("@deck.gl/mapbox"),
      ]);
      if (cancelled || !elA.current || !elB.current) return;
      if (!protocolRegistered) {
        ml.addProtocol("cog", cog.cogProtocol);
        protocolRegistered = true;
      }
      const first = flyover.waypoints[0].camera;
      const make = (container: HTMLElement) => {
        const map = new ml.Map({
          container,
          style: baseStyle(),
          center: first.center,
          zoom: first.zoom,
          pitch: first.pitch,
          bearing: first.bearing,
          maxPitch: 85,
          attributionControl: false,
          renderWorldCopies: false,
          fadeDuration: 0,
          pixelRatio: Math.min(window.devicePixelRatio || 1, 2),
        });
        for (const h of [map.scrollZoom, map.boxZoom, map.doubleClickZoom, map.keyboard, map.touchZoomRotate, map.dragPan, map.dragRotate, map.touchPitch]) h.disable();
        const overlay = new deck.MapboxOverlay({ layers: [] });
        map.addControl(overlay as unknown as IControl);
        return { map, overlay };
      };
      const A = make(elA.current);
      const B = make(elB.current);
      A.map.addControl(new ml.AttributionControl({ compact: true }), "bottom-left");
      // In radar mode B follows A, including while the user drags.
      A.map.on("move", () => modeRef.current === "radar" && B.map.jumpTo(cameraOf(A.map)));
      const observers = [
        [elA.current, A.map],
        [elB.current, B.map],
      ].map(([el, map]) => {
        const ro = new ResizeObserver(() => (map as MlMap).resize());
        ro.observe(el as HTMLElement);
        return ro;
      });
      await Promise.all([A, B].map(({ map }) => (map.loaded() ? Promise.resolve() : new Promise<void>((r) => map.once("load", () => r())))));
      if (cancelled) {
        A.map.remove();
        B.map.remove();
        return;
      }
      rt.current = { setColorFunction: cog.setColorFunction, a: A.map, b: B.map, overlayA: A.overlay, overlayB: B.overlay };
      // Test and debugging handle, only with ?debug in the URL.
      if (new URLSearchParams(window.location.search).has("debug")) (window as unknown as { __sar?: unknown }).__sar = { a: A.map, b: B.map };
      setReady(true);
      cleanup = () => {
        observers.forEach((o) => o.disconnect());
        rt.current?.mgrA?.dispose();
        rt.current?.mgrB?.dispose();
        A.overlay.finalize();
        B.overlay.finalize();
        A.map.remove();
        B.map.remove();
        rt.current = null;
      };
    })();
    return () => {
      cancelled = true;
      setReady(false);
      cleanup();
    };
    // The maps are created once; the first waypoint is only their starting camera.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // A new chapter: fresh layer managers, terrain exaggeration, and a camera jump.
  useEffect(() => {
    const r = rt.current;
    if (!ready || !r) return;
    r.mgrA?.dispose();
    r.mgrB?.dispose();
    const layers = chapter.generated.layers;
    r.mgrA = new LayerManager(r.a, layers, absoluteAssetUrl, assetUrl, r.setColorFunction);
    r.mgrB = new LayerManager(r.b, layers, absoluteAssetUrl, assetUrl, r.setColorFunction);
    for (const map of [r.a, r.b]) map.setTerrain({ source: TERRAIN_SOURCE, exaggeration: flyover.exaggeration });
    const cam = cameraAt(flyover.waypoints, clock.getState().t);
    r.a.jumpTo(cam);
    r.b.jumpTo(cam);
    return () => {
      r.mgrA?.dispose();
      r.mgrB?.dispose();
      r.mgrA = r.mgrB = undefined;
    };
  }, [ready, chapter.slug, chapter.generated.layers, flyover]);

  // A new beat or mode: which layers each map shows, and where radar mode looks.
  useEffect(() => {
    const r = rt.current;
    if (!ready || !r?.mgrA || !r.mgrB) return;
    const { a, b } = paneLayers(beat, mode);
    r.mgrA.setVisible(a);
    r.mgrB.setVisible(b);
    if (mode === "radar") {
      const target = radarCamera(beat, flyover.waypoints);
      if (reduced) r.a.jumpTo(target);
      else r.a.easeTo({ ...target, duration: CAMERA_MS, easing: springEase });
    }
  }, [ready, chapter.slug, beat, mode, reduced, flyover.waypoints]);

  // Flyover and split: the camera follows the flyover clock.
  useEffect(() => {
    const r = rt.current;
    if (!ready || !r || mode === "radar") return;
    let last = NaN;
    const apply = (t: number) => {
      if (Math.abs(t - last) < 1e-4) return;
      last = t;
      const cam = cameraAt(flyover.waypoints, t);
      if (!(videoActive && mode === "flyover")) r.a.jumpTo(cam);
      if (mode === "split") r.b.jumpTo(cam);
    };
    apply(clock.getState().t);
    return clock.subscribe((s) => apply(s.t));
  }, [ready, mode, videoActive, flyover.waypoints]);

  // Radar mode on a pointer with a mouse: drag to pan, right-drag to rotate. Touch keeps scrolling the page.
  useEffect(() => {
    const r = rt.current;
    if (!ready || !r) return;
    const on = mode === "radar" && finePointer;
    for (const handler of [r.a.dragPan, r.a.dragRotate]) {
      if (on) handler.enable();
      else handler.disable();
    }
  }, [ready, mode, finePointer]);

  // Annotations from deck.gl, pulsing, lifted to the terrain. Not shown during the flyover.
  useEffect(() => {
    const r = rt.current;
    if (!ready || !r) return;
    const ids = new Set(beat.stage.annotations ?? []);
    const annotations = mode === "flyover" ? [] : chapter.generated.annotations.filter((a) => ids.has(a.id));
    const targets: [MlMap, MapboxOverlay][] = [[r.a, r.overlayA], [r.b, r.overlayB]];
    if (!annotations.length) {
      for (const [, o] of targets) o.setProps({ layers: [] });
      return;
    }
    let raf = 0;
    let last = 0;
    const tick = (now: number) => {
      raf = requestAnimationFrame(tick);
      if (now - last < 33) return;
      last = now;
      const phase = reduced ? 0.4 : (now / 1600) % 1;
      for (const [map, overlay] of targets) {
        overlay.setProps({ layers: annotationLayers(annotations, chapter.accent, phase, (lon, lat) => map.queryTerrainElevation([lon, lat]) ?? 0) });
      }
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [ready, chapter, beat, mode, reduced]);

  const shown = paneLayers(beat, mode);
  const labelOf = (id?: string) => chapter.generated.layers.find((l) => l.id === id)?.label;
  const zoom = (dir: 1 | -1) => rt.current && (dir === 1 ? rt.current.a.zoomIn({ duration: 300 }) : rt.current.a.zoomOut({ duration: 300 }));

  return (
    <>
      <div className="pane pane-a">
        <div ref={elA} className="pane-a-map" style={FILL} />
        <PaneTag side="left" text={labelOf(shown.a[0])} />
      </div>
      <div className="pane pane-b">
        <div ref={elB} style={FILL} />
        <PaneTag side="right" text={labelOf(shown.b[0])} />
      </div>
      {mode === "radar" && (
        <div className="glass absolute right-5 top-[7.5rem] z-30 hidden flex-col overflow-hidden rounded-full! lg:flex">
          {([1, -1] as const).map((d) => (
            <button
              key={d}
              type="button"
              aria-label={d === 1 ? "Zoom in" : "Zoom out"}
              onClick={() => zoom(d)}
              className="grid size-11 place-items-center text-[20px] leading-none text-ink-dim transition-colors duration-[240ms] hover:bg-white/10 hover:text-ink focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-white/70"
            >
              {d === 1 ? "+" : "−"}
            </button>
          ))}
        </div>
      )}
    </>
  );
}
