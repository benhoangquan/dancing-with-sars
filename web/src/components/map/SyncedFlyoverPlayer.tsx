"use client";

import { useEffect, useRef } from "react";
import { assetUrl } from "@/lib/asset";
import { clock } from "@/lib/store";
import type { Chapter } from "@/types/chapter";

type Video = NonNullable<Chapter["generated"]["flyover"]["video"]>;

/** Seek only when the video is more than one frame from the target time, so scrubbing does not thrash. */
export const shouldSeek = (current: number, target: number, fps: number) =>
  Number.isFinite(target) && Math.abs(current - target) > 1 / fps;

/** Pre-rendered flyover video whose playback position follows the flyover clock. Muted, no controls. */
export function SyncedFlyoverPlayer({ video, label }: { video: Video; label: string }) {
  const ref = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const apply = (t: number) => {
      if (el.seeking || el.readyState < 1) return;
      const target = Math.min(Math.max(t, 0), el.duration || t);
      if (shouldSeek(el.currentTime, target, video.fps)) el.currentTime = target;
    };
    apply(clock.getState().t);
    el.addEventListener("loadedmetadata", () => apply(clock.getState().t));
    return clock.subscribe((s) => apply(s.t));
  }, [video.fps]);

  return (
    <video
      ref={ref}
      aria-label={label}
      className="size-full object-cover"
      src={assetUrl(video.src)}
      poster={assetUrl(video.poster)}
      muted
      playsInline
      preload="auto"
      disablePictureInPicture
    />
  );
}
