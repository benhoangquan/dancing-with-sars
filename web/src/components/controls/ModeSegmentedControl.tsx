"use client";

import { motion } from "motion/react";
import { MODES } from "@/lib/beats";
import type { StageMode } from "@/types/chapter";

const SPRING = { duration: 0.24, ease: [0.22, 1, 0.36, 1] } as const;

type Props = {
  value: StageMode;
  onChange: (mode: StageMode) => void;
  /** True when the flyover is the live 3D map rather than a pre-rendered video. */
  liveFlyover: boolean;
};

/** Compact segmented control: Flyover | Radar Compare | Split. A radio group with arrow-key navigation. */
export function ModeSegmentedControl({ value, onChange, liveFlyover }: Props) {
  const onKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>, index: number) => {
    const step = e.key === "ArrowRight" || e.key === "ArrowDown" ? 1 : e.key === "ArrowLeft" || e.key === "ArrowUp" ? -1 : 0;
    if (!step) return;
    e.preventDefault();
    const next = MODES[(index + step + MODES.length) % MODES.length].id;
    onChange(next);
    e.currentTarget.parentElement?.querySelector<HTMLButtonElement>(`[data-mode="${next}"]`)?.focus();
  };

  return (
    <div role="radiogroup" aria-label="Stage view" className="glass relative inline-flex rounded-full! p-1 text-[13px]">
      {MODES.map((m, i) => {
        const selected = value === m.id;
        return (
          <button
            key={m.id}
            type="button"
            role="radio"
            aria-checked={selected}
            data-mode={m.id}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(m.id)}
            onKeyDown={(e) => onKeyDown(e, i)}
            className={`relative rounded-full px-2.5 py-1.5 font-medium sm:px-3.5 transition-colors duration-[240ms] focus-visible:outline-2 focus-visible:outline-white/70 ${
              selected ? "text-ink" : "text-ink-dim hover:text-ink"
            }`}
          >
            {selected && (
              <motion.span layoutId="mode-thumb" transition={SPRING} className="absolute inset-0 rounded-full bg-white/16" />
            )}
            <span className="relative" aria-hidden>
              <span className="sm:hidden">{m.short}</span>
              <span className="max-sm:hidden">{m.label}</span>
            </span>
            <span className="sr-only">{m.label}</span>
            {m.id === "flyover" && liveFlyover && (
              <span className="relative ml-1.5 hidden rounded-full bg-white/10 px-1.5 py-px text-[10px] text-ink-dim sm:inline">
                Live 3D
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
