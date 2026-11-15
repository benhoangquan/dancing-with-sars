import { splitTokens } from "@/lib/tokens";
import type { Stat } from "@/types/chapter";

/** Story text with `{stat:key}` tokens resolved and each number in its own tabular-nums span. */
export function RichText({ text, stats }: { text: string; stats: Record<string, Stat> }) {
  return (
    <>
      {splitTokens(text, stats).map((part, i) =>
        part.kind === "stat" ? (
          <span key={i} className="tabular whitespace-nowrap font-semibold text-ink">
            {part.text}
          </span>
        ) : (
          <span key={i}>{part.text}</span>
        ),
      )}
    </>
  );
}
