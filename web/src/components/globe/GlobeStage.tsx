"use client";

import "maplibre-gl/dist/maplibre-gl.css";
import type { Map as MlMap, Marker } from "maplibre-gl";
import { useEffect, useRef } from "react";
import { assetUrl } from "@/lib/asset";
import { springEase } from "@/lib/ease";
import { heroPose } from "@/lib/scenes";
import { type GlobeView, heroClock, useStory } from "@/lib/store";
import type { WatchedPlace } from "@/lib/watched";
import type { Chapter } from "@/types/chapter";

type Props = { chapters: Chapter[]; watched: WatchedPlace[]; reduced: boolean };

const FILL = { position: "absolute", inset: 0 } as const;
const HOME: GlobeView = { center: [-40, 8], zoom: 1.15, bearing: 0, pitch: 0 };
const PIN_ZOOM = 5.2;

const shortName = (c: Chapter) => c.aoi.placeName.split(",")[0];
const pinOf = (c: Chapter): [number, number] => c.globe?.pin ?? [(c.aoi.bbox[0] + c.aoi.bbox[2]) / 2, (c.aoi.bbox[1] + c.aoi.bbox[3]) / 2];
const viewOf = (m: MlMap): GlobeView => ({ center: m.getCenter().toArray() as [number, number], zoom: m.getZoom(), bearing: m.getBearing(), pitch: m.getPitch() });

/** A pin: a beacon dot and an Apple Maps style callout pill ("Rondônia · BRA"). */
function pinElement(label: string, active: boolean, onClick: () => void): HTMLElement {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = `globe-pin ${active ? "globe-pin-active" : "globe-pin-watched"}`;
  btn.setAttribute("aria-label", active ? `Open ${label}` : `${label}: checked, no chapter yet`);
  btn.innerHTML = `<span class="globe-pin-dot" aria-hidden="true"></span><span class="globe-pin-label tabular"></span>`;
  (btn.querySelector(".globe-pin-label") as HTMLElement).textContent = label;
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    onClick();
  });
  return btn;
}

/**
 * The NASA Blue Marble globe on a white canvas. In the hero it turns and zooms with scroll; on the hotspot
 * globe the reader spins it and picks a place. Opening a place flies toward its pin first; coming back zooms
 * out from the place to the view the reader left.
 */
export default function GlobeStage({ chapters, watched, reduced }: Props) {
  const el = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const scene = useStory((s) => s.scene);
  const sceneRef = useRef(scene);
  useEffect(() => {
    sceneRef.current = scene;
  }, [scene]);

  useEffect(() => {
    let cancelled = false;
    let cleanup = () => {};
    (async () => {
      const ml = await import("maplibre-gl");
      if (cancelled || !el.current) return;
      const map = new ml.Map({
        container: el.current,
        style: {
          version: 8,
          projection: { type: "globe" },
          sources: {
            earth: {
              type: "raster",
              // Built by hand: new URL() would percent-encode the {z}/{x}/{y} placeholders.
              tiles: [`${window.location.origin}${assetUrl("globe/{z}/{x}/{y}.webp")}`],
              tileSize: 256,
              maxzoom: 4,
              attribution: "NASA Blue Marble, via NASA GIBS",
            },
          },
          layers: [{ id: "earth", type: "raster", source: "earth", paint: { "raster-fade-duration": 0 } }],
          sky: { "atmosphere-blend": ["interpolate", ["linear"], ["zoom"], 0, 0.9, 4, 0.6, 7, 0] },
        },
        center: HOME.center,
        zoom: HOME.zoom,
        attributionControl: false,
        renderWorldCopies: false,
        pixelRatio: Math.min(window.devicePixelRatio || 1, 2),
      });
      map.scrollZoom.disable();
      map.boxZoom.disable();
      map.doubleClickZoom.disable();
      map.addControl(new ml.AttributionControl({ compact: true }), "bottom-left");
      mapRef.current = map;
      if (new URLSearchParams(window.location.search).has("debug")) (window as unknown as { __globe?: MlMap }).__globe = map;

      const enter = (c: Chapter) => {
        if (sceneRef.current !== "HOTSPOT_GLOBE") return;
        const view = viewOf(map);
        const go = () => useStory.getState().enterPlace(c.slug, view);
        if (reduced) return go();
        map.flyTo({ center: pinOf(c), zoom: PIN_ZOOM, duration: 1200, easing: springEase });
        map.once("moveend", go);
      };
      const markers: Marker[] = [
        ...chapters.map((c) =>
          new ml.Marker({ element: pinElement(`${shortName(c)} · ${c.aoi.iso3 ?? c.aoi.countryCode}`, true, () => enter(c)), anchor: "bottom" }).setLngLat(pinOf(c)),
        ),
        ...watched.map((w) =>
          new ml.Marker({
            element: pinElement(`${w.name} · ${w.iso3}`, false, () => window.dispatchEvent(new CustomEvent("sar:watched", { detail: w.id }))),
            anchor: "bottom",
          }).setLngLat(w.pin),
        ),
      ];
      markers.forEach((m) => m.addTo(map));

      // Hero: the globe follows scroll progress and turns slowly until it settles.
      let spin = 0;
      let raf = 0;
      let prev = performance.now();
      const frame = (now: number) => {
        raf = requestAnimationFrame(frame);
        const dt = Math.min(0.1, (now - prev) / 1000);
        prev = now;
        if (sceneRef.current !== "HERO_GLOBE") return;
        if (!reduced) spin += dt * 4;
        const pose = heroPose(heroClock.getState().p);
        const top = map.getContainer().clientHeight * pose.padTop;
        map.jumpTo({ center: [HOME.center[0] + spin, HOME.center[1]], zoom: pose.zoom, pitch: pose.pitch, bearing: 0, padding: { top, bottom: 0, left: 0, right: 0 } });
      };
      raf = requestAnimationFrame(frame);
      const ro = new ResizeObserver(() => map.resize());
      ro.observe(el.current);
      cleanup = () => {
        cancelAnimationFrame(raf);
        ro.disconnect();
        markers.forEach((m) => m.remove());
        map.remove();
        mapRef.current = null;
      };
    })();
    return () => {
      cancelled = true;
      cleanup();
    };
  }, [chapters, watched, reduced]);

  // Coming back from a place: start close to it, then zoom out to the saved view.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || scene !== "HOTSPOT_GLOBE") return;
    const { leftPlace, savedGlobeView } = useStory.getState();
    const from = chapters.find((c) => c.slug === leftPlace);
    if (!from) return; // arriving from the hero: keep the pose the hero left
    const to = savedGlobeView ?? { ...HOME, zoom: 2 };
    if (!reduced) {
      map.jumpTo({ center: pinOf(from), zoom: PIN_ZOOM, bearing: 0, pitch: 0 });
      map.flyTo({ ...to, duration: 2200, easing: springEase });
    } else map.jumpTo(to);
    useStory.setState({ leftPlace: null });
  }, [scene, chapters, reduced]);

  return (
    <div className="globe-root fixed inset-0 z-0 bg-white" data-scene={scene} aria-label="Globe of the places in this story" role="group">
      <div ref={el} style={FILL} />
    </div>
  );
}
