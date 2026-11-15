import { type TokenContext, splitTokens } from "@/lib/tokens";

/**
 * Story text with `{stat:}` and `{fact:}` tokens resolved. Each figure sits in its own tabular-nums span; a figure
 * with a scale anchor is followed by its everyday comparison in a quieter tone.
 */
export function RichText({ text, ctx, anchors = true }: { text: string; ctx: TokenContext; anchors?: boolean }) {
  return (
    <>
      {splitTokens(text, ctx).map((part, i) =>
        part.kind === "text" ? (
          <span key={i}>{part.text}</span>
        ) : (
          <span key={i}>
            <span className="tabular whitespace-nowrap font-semibold" data-figure={part.key}>
              {part.text}
            </span>
            {anchors && part.anchor && <span className="anchor text-[0.88em] opacity-70"> ({part.anchor})</span>}
          </span>
        ),
      )}
    </>
  );
}
