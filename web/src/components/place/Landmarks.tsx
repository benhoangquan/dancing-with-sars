"use client";

import type { Map as MlMap } from "maplibre-gl";
import { useEffect, useMemo, useRef, useState } from "react";
import { assetUrl } from "@/lib/asset";
import { formatCoordinate, formatStat } from "@/lib/format";
import { shouldClosePopover } from "@/lib/scenes";
import { useStory } from "@/lib/store";
import type { Chapter } from "@/types/chapter";

type Pin = { id: string; x: number; y: number; visible: boolean };

/**
 * Ground-truth pins (Apple Maps style) drawn above both radar panes at map A's projection, and the one popover
 * that can be open: a photo with its credit where one exists, and the radar readings at the pin.
 */
export function Landmarks({ map, chapter, show }: { map: MlMap; chapter: Chapter; show: boolean }) {
  const landmarks = useMemo(() => chapter.landmarks ?? [], [chapter.landmarks]);
  const readings = chapter.generated.landmarkReadings ?? {};
  const popover = useStory((s) => s.popover);
  const setPopover = useStory((s) => s.setPopover);
  const [pins, setPins] = useState<Pin[]>([]);
  const scrollAtOpen = useRef(0);

  useEffect(() => {
    if (!show || !landmarks.length) return;
    let raf = 0;
    const update = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        const { clientWidth: w, clientHeight: h } = map.getContainer();
        setPins(
          landmarks.map((l) => {
            const p = map.project(l.lonLat); // follows the terrain surface when terrain is on
            return { id: l.id, x: p.x, y: p.y, visible: p.x > 0 && p.y > 0 && p.x < w && p.y < h };
          }),
        );
      });
    };
    update();
    map.on("move", update);
    return () => {
      cancelAnimationFrame(raf);
      map.off("move", update);
    };
  }, [map, show, landmarks]);

  // One popover at a time; it closes once the page scrolls more than 40 px.
  useEffect(() => {
    if (!popover) return;
    scrollAtOpen.current = window.scrollY;
    const onScroll = () => shouldClosePopover(scrollAtOpen.current, window.scrollY) && setPopover(null);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [popover, setPopover]);

  if (!show || !landmarks.length) return null;
  const open = landmarks.find((l) => l.id === popover);
  const openPin = pins.find((p) => p.id === popover);
  return (
    <div className="pointer-events-none absolute inset-0 z-[3]" aria-label="Places on the ground">
      {pins
        .filter((p) => p.visible)
        .map((p) => {
          const l = landmarks.find((x) => x.id === p.id)!;
          return (
            <button
              key={p.id}
              type="button"
              aria-expanded={popover === p.id}
              aria-label={`${l.label}: ground view`}
              onClick={() => setPopover(popover === p.id ? null : p.id)}
              className="landmark-pin pointer-events-auto absolute -translate-x-1/2 -translate-y-full"
              style={{ left: p.x, top: p.y }}
            >
              <span className="landmark-pin-head" style={{ background: chapter.accent }} />
              <span className="landmark-pin-label">{l.label}</span>
            </button>
          );
        })}
      {open && openPin && (
        <div
          role="dialog"
          aria-label={open.label}
          className="glass-dark pointer-events-auto absolute w-[min(320px,86vw)] -translate-x-1/2 overflow-hidden p-0 text-ink"
          style={{ left: Math.min(Math.max(openPin.x, 170), window.innerWidth - 170), top: Math.max(openPin.y + 14, 80) }}
        >
          {open.photo && (
            <figure>
              {/* eslint-disable-next-line @next/next/no-img-element -- static export, no image optimizer */}
              <img src={assetUrl(open.photo.src)} alt={open.photo.caption} className="aspect-[4/3] w-full object-cover" />
              <figcaption className="px-4 pt-2 text-[11px] leading-[1.4] text-ink-faint">
                {open.photo.caption} {open.photo.where}. Photo: {open.photo.credit},{" "}
                <a href={open.photo.licenseUrl} target="_blank" rel="noopener noreferrer" className="underline">
                  {open.photo.license}
                </a>
                .
              </figcaption>
            </figure>
          )}
          <div className="p-4">
            <p className="text-[15px] font-semibold">{open.label}</p>
            <p className="tabular mt-0.5 text-[12px] text-ink-faint">{formatCoordinate(open.lonLat[0], open.lonLat[1])}</p>
            {open.note && <p className="mt-2 text-[14px] leading-[1.45] text-ink/85">{open.note}</p>}
            {(readings[open.id] ?? []).length > 0 && (
              <dl className="mt-3 grid grid-cols-2 gap-2">
                {readings[open.id].map((r) => (
                  <div key={r.label} className="rounded-xl bg-white/5 px-3 py-2">
                    <dt className="text-[11px] text-ink-faint">{r.label}</dt>
                    <dd className="tabular text-[15px] font-semibold">{formatStat(r)}</dd>
                  </div>
                ))}
              </dl>
            )}
            <button type="button" onClick={() => setPopover(null)} className="mt-3 text-[13px] font-semibold text-[#64D2FF]">
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
