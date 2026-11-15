"use client";

import { useStory } from "@/lib/store";
import type { Chapter } from "@/types/chapter";

/** While sound is on: what is playing, who recorded it, and that it was not recorded at this place. */
export function SoundCredit({ chapter }: { chapter: Chapter }) {
  const soundOn = useStory((s) => s.soundOn);
  const sound = chapter.soundscape;
  if (!soundOn || !sound) return null;
  return (
    <p data-story-root className="glass-dark pointer-events-auto fixed bottom-4 right-4 z-30 max-w-[340px] px-4 py-2 text-[11px] leading-[1.4] text-ink-dim max-sm:hidden">
      Sound: {sound.before.label} fading to {sound.after.label}.{" "}
      {[sound.before, sound.after].map((s, i) => (
        <span key={s.src}>
          {i > 0 && " "}
          <a href={s.sourceUrl} target="_blank" rel="noopener noreferrer" className="underline">
            {s.label}
          </a>
          : {s.credit} {s.license}.
        </span>
      ))}
    </p>
  );
}
