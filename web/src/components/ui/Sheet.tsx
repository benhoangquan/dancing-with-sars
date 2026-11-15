"use client";

import { AnimatePresence, motion } from "motion/react";
import { type ReactNode, useRef } from "react";
import { useDialog } from "@/lib/useDialog";

type Props = { open: boolean; onClose: () => void; labelledBy: string; children: ReactNode };

const EASE = [0.22, 1, 0.36, 1] as const;

/** Centered Apple-style sheet (max 680 px) over a dimmed scrim. Locks the page behind it while open. */
export function Sheet({ open, onClose, labelledBy, children }: Props) {
  const panel = useRef<HTMLDivElement>(null);
  useDialog(open, onClose, panel);
  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 grid place-items-center p-4 max-sm:items-end max-sm:p-0">
          <motion.div
            key="scrim"
            className="absolute inset-0 bg-black/40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.24 }}
            onClick={onClose}
          />
          <motion.div
            key="sheet"
            ref={panel}
            role="dialog"
            aria-modal="true"
            aria-labelledby={labelledBy}
            className="sheet relative flex max-h-[min(88svh,860px)] w-full max-w-[680px] flex-col overflow-hidden"
            initial={{ opacity: 0, y: 24, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 24, scale: 0.98 }}
            transition={{ duration: 0.42, ease: EASE }}
          >
            <button
              type="button"
              onClick={onClose}
              aria-label="Close"
              className="absolute right-4 top-4 z-10 grid size-9 place-items-center rounded-full bg-black/5 text-[18px] text-light-ink-dim transition-colors duration-[240ms] hover:bg-black/10 focus-visible:outline-2 focus-visible:outline-apple-blue"
            >
              ×
            </button>
            <div className="overflow-y-auto overscroll-contain">{children}</div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
