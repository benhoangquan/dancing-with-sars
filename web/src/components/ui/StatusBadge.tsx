import type { Layer } from "@/types/chapter";

const COPY: Record<Layer["status"], { label: string; dot: string; title: string }> = {
  real: { label: "NISAR data", dot: "#30d158", title: "Processed from NISAR data by this project" },
  fallback: { label: "Fallback data", dot: "#ff9f0a", title: "Another real mission, used because NISAR data was not available" },
  illustrative: {
    label: "Illustrative data",
    dot: "#ff9f0a",
    title: "A synthetic pattern that shows what the radar would reveal. Not a measurement.",
  },
};

/** Provenance chip. Always a dot plus words, never color alone. */
export function StatusBadge({ status, className = "" }: { status: Layer["status"]; className?: string }) {
  const c = COPY[status];
  return (
    <span
      title={c.title}
      className={`inline-flex items-center gap-1.5 rounded-full border border-hairline bg-white/5 px-2.5 py-0.5 text-[11px] font-medium text-ink-dim ${className}`}
    >
      <span aria-hidden className="size-1.5 rounded-full" style={{ background: c.dot }} />
      {c.label}
    </span>
  );
}
