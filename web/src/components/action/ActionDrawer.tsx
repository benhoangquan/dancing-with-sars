"use client";

import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef } from "react";
import { RichText } from "@/components/ui/RichText";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatNumber, formatStat } from "@/lib/format";
import { useMediaQuery } from "@/lib/useMediaQuery";
import type { Chapter } from "@/types/chapter";

type Props = { chapter: Chapter; open: boolean; onClose: () => void };

const EASE = [0.22, 1, 0.36, 1] as const;
const FOCUSABLE = 'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])';

/** Slide-over sheet (bottom sheet on narrow screens) with impact metrics and vetted conservation organizations. */
export function ActionDrawer({ chapter, open, onClose }: Props) {
  const narrow = useMediaQuery("(max-width: 1023px)");
  const panel = useRef<HTMLElement>(null);
  const { action, generated } = chapter;
  const statuses = new Set([...generated.layers.map((l) => l.status), ...generated.series.map((s) => s.status)]);
  const caution = statuses.has("illustrative") ? "illustrative" : statuses.has("fallback") ? "fallback" : null;

  // Inert background, Escape to close, focus trap, and focus restored to the trigger.
  useEffect(() => {
    if (!open) return;
    const trigger = document.activeElement as HTMLElement | null;
    const background = document.querySelectorAll<HTMLElement>("[data-story-root]");
    background.forEach((el) => el.setAttribute("inert", ""));
    panel.current?.querySelector<HTMLElement>("[data-autofocus]")?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") return onClose();
      if (e.key !== "Tab" || !panel.current) return;
      const items = [...panel.current.querySelectorAll<HTMLElement>(FOCUSABLE)];
      if (!items.length) return;
      const [first, last] = [items[0], items[items.length - 1]];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      background.forEach((el) => el.removeAttribute("inert"));
      trigger?.focus();
    };
  }, [open, onClose]);

  const hidden = narrow ? { y: "100%" } : { x: "100%" };
  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            key="scrim"
            aria-hidden
            onClick={onClose}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="fixed inset-0 z-40 bg-black/50"
          />
          <motion.aside
            key="sheet"
            ref={panel}
            role="dialog"
            aria-modal="true"
            aria-labelledby="action-title"
            initial={hidden}
            animate={{ x: 0, y: 0 }}
            exit={hidden}
            transition={{ duration: 0.5, ease: EASE }}
            className="glass-data fixed z-50 flex flex-col overflow-hidden max-lg:inset-x-2 max-lg:bottom-2 max-lg:max-h-[88svh] lg:bottom-4 lg:right-4 lg:top-4 lg:w-[420px]"
          >
            <header className="flex items-start justify-between gap-4 p-6 pb-3">
              <p className="text-[12px] font-medium uppercase tracking-[0.08em]" style={{ color: chapter.accent }}>
                {chapter.aoi.placeName}
              </p>
              <button
                type="button"
                data-autofocus
                onClick={onClose}
                aria-label="Close"
                className="-mr-2 -mt-1 grid size-9 place-items-center rounded-full text-ink-dim transition-colors duration-[240ms] hover:bg-white/10 hover:text-ink focus-visible:outline-2 focus-visible:outline-white/70"
              >
                <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden>
                  <path d="M1 1l12 12M13 1L1 13" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                </svg>
              </button>
            </header>
            <div className="flex-1 space-y-6 overflow-y-auto px-6 pb-6">
              <div>
                <h2 id="action-title" className="display text-[26px] font-semibold leading-tight">
                  {action.headline}
                </h2>
                <p className="mt-3 text-[15px] leading-snug text-ink-dim">
                  <RichText text={action.body} stats={generated.stats} />
                </p>
                {caution && (
                  <p className="mt-3 flex flex-wrap items-center gap-2 text-[12px] leading-snug text-ink-dim">
                    <StatusBadge status={caution} />
                    {caution === "illustrative"
                      ? "The numbers here come from a synthetic pattern, not a measurement."
                      : "Some numbers here come from a fallback mission."}
                  </p>
                )}
              </div>

              <section aria-label="Impact metrics">
                <ul className="grid grid-cols-2 gap-3">
                  {action.metrics.map((m) => (
                    <li key={m.label} className="rounded-2xl border border-hairline bg-white/5 p-4">
                      <p className="tabular text-[24px] font-semibold leading-none display">
                        {"statKey" in m ? formatStat(generated.stats[m.statKey]) : `${formatNumber(m.value, Number.isInteger(m.value) ? 0 : 1)} ${m.unit}`}
                      </p>
                      <p className="mt-2 text-[12px] leading-snug text-ink-dim">{m.label}</p>
                      <a
                        href={m.source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-2 block text-[11px] leading-snug text-ink-faint underline decoration-white/20 underline-offset-2 hover:text-ink-dim"
                      >
                        {m.source.name}, {m.source.accessed}
                      </a>
                    </li>
                  ))}
                </ul>
              </section>

              <section aria-label="Organizations you can support" className="space-y-3">
                <h3 className="text-[11px] font-medium uppercase tracking-[0.08em] text-ink-faint">Organizations doing this work</h3>
                {action.organizations.map((o) => (
                  <article key={o.name} className="rounded-2xl border border-hairline bg-white/5 p-4">
                    <h4 className="text-[17px] font-semibold">
                      <a href={o.url} target="_blank" rel="noopener noreferrer" className="hover:underline">
                        {o.name}
                      </a>
                    </h4>
                    <p className="mt-1 text-[13px] leading-snug text-ink-dim">{o.focus}</p>
                    <p className="mt-1 text-[12px] text-ink-faint">{o.region}</p>
                    <a
                      href={o.cta.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-4 inline-flex items-center rounded-full bg-white px-5 py-2.5 text-[14px] font-semibold text-black transition-transform duration-[240ms] ease-[cubic-bezier(0.22,1,0.36,1)] hover:scale-[1.03] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
                    >
                      {o.cta.label}
                      <span aria-hidden className="ml-1.5">↗</span>
                    </a>
                    <p className="mt-3 text-[11px] text-ink-faint">
                      Link checked {o.verified.on}: {o.verified.how}.
                    </p>
                  </article>
                ))}
              </section>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
