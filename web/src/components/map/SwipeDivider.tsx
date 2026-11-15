"use client";

import { useRef } from "react";
import { useStory } from "@/lib/store";

const STEP = 0.05;

/**
 * The before/after divider: a 1.5px hairline with a 44px frosted grabber. Its position comes from the
 * `--swipe` CSS variable that the stage keeps in sync with the store, so dragging never re-renders React.
 * Pointer drag, and arrow / Home / End keys on the slider.
 */
export function SwipeDivider() {
  const swipe = useStory((s) => s.swipe);
  const setSwipe = useStory((s) => s.setSwipe);
  const dragging = useRef(false);

  const move = (clientX: number) => setSwipe(clientX / window.innerWidth);
  const onKeyDown = (e: React.KeyboardEvent) => {
    const keys: Record<string, number> = { ArrowLeft: swipe - STEP, ArrowDown: swipe - STEP, ArrowRight: swipe + STEP, ArrowUp: swipe + STEP, Home: 0, End: 1 };
    if (!(e.key in keys)) return;
    e.preventDefault();
    setSwipe(keys[e.key]);
  };

  return (
    <div
      role="slider"
      tabIndex={0}
      aria-label="Before and after divider"
      aria-orientation="horizontal"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(swipe * 100)}
      onKeyDown={onKeyDown}
      onPointerDown={(e) => {
        dragging.current = true;
        e.currentTarget.setPointerCapture(e.pointerId);
        move(e.clientX);
      }}
      onPointerMove={(e) => dragging.current && move(e.clientX)}
      onPointerUp={() => (dragging.current = false)}
      onPointerCancel={() => (dragging.current = false)}
      className="group absolute inset-y-0 z-20 w-11 -translate-x-1/2 cursor-ew-resize touch-none outline-none"
      style={{ left: "calc(var(--swipe, 0.5) * 100%)" }}
    >
      <div className="absolute inset-y-0 left-1/2 w-[1.5px] -translate-x-1/2 bg-white/80" />
      <div className="glass absolute left-1/2 top-1/2 grid size-11 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full! text-ink transition-transform duration-[240ms] ease-[cubic-bezier(0.22,1,0.36,1)] group-hover:scale-105 group-focus-visible:outline-2 group-focus-visible:outline-white/80">
        <svg width="18" height="12" viewBox="0 0 18 12" aria-hidden>
          <path d="M5 1L1 6l4 5M13 1l4 5-4 5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
    </div>
  );
}
