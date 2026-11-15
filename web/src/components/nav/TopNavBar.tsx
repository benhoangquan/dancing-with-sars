"use client";

import { overlays } from "@/lib/scenes";
import { useStory } from "@/lib/store";

type Props = { act: 1 | 2 | 3; onGlobe: () => void };

/** Persistent top bar: ‹ Globe on the left, the wordmark, and the Sound toggle on the right. */
export function TopNavBar({ act, onGlobe }: Props) {
  const scene = useStory((s) => s.scene);
  const soundOn = useStory((s) => s.soundOn);
  const setSoundOn = useStory((s) => s.setSoundOn);
  const modal = useStory((s) => s.modal);
  const setModal = useStory((s) => s.setModal);
  const o = overlays({ scene, act, dragging: false, popover: null, modal });
  const dark = scene === "PLACE_CHAPTER";
  const pill = dark ? "glass-dark text-ink" : "glass-light text-light-ink";

  return (
    <header data-story-root className="pointer-events-none fixed inset-x-0 top-0 z-30 flex items-center justify-between gap-2 px-6 py-6 max-sm:px-3 max-sm:py-3">
      <div className="flex items-center gap-2">
        {o.backToGlobe !== "hidden" && (
          <button
            type="button"
            onClick={onGlobe}
            disabled={o.backToGlobe === "disabled"}
            aria-label="Back to the globe"
            className={`pointer-events-auto rounded-full px-4 py-2 text-[13px] font-semibold transition-opacity duration-[240ms] disabled:opacity-40 ${pill}`}
          >
            ‹ Globe
          </button>
        )}
        <span className={`rounded-full px-4 py-2 text-[13px] font-semibold display max-md:hidden ${pill}`}>Dancing with the SARs</span>
      </div>
      <div className="flex items-center gap-2">
        {scene === "HOTSPOT_GLOBE" && (
          <button
            type="button"
            onClick={() => setModal("discovery")}
            className="pointer-events-auto rounded-full bg-apple-blue px-4 py-2 text-[13px] font-semibold text-white transition-colors duration-[240ms] hover:bg-apple-blue-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-apple-blue"
          >
            Take Action
          </button>
        )}
        <button
          type="button"
          role="switch"
          aria-checked={soundOn}
          onClick={() => setSoundOn(!soundOn)}
          className={`pointer-events-auto rounded-full px-4 py-2 text-[13px] font-semibold ${pill}`}
        >
          Sound: {soundOn ? "On" : "Off"}
        </button>
      </div>
    </header>
  );
}
