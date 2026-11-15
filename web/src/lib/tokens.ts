// `{stat:key}` and `{fact:key}` tokens in story text resolve against generated.stats (measured by the pipeline)
// and the chapter's sourced facts, so numbers in copy are never typed by hand. A figure with a scale anchor
// carries its everyday comparison along.
import type { Fact, ScaleReference, Stat } from "@/types/chapter";
import { formatStat } from "./format";
import { anchorText } from "./references";

const TOKEN = /\{(stat|fact):([a-z0-9_]+)\}/g;

export type TextPart =
  | { kind: "text"; text: string }
  | { kind: "stat" | "fact"; key: string; text: string; anchor?: string };

export interface TokenContext {
  stats: Record<string, Stat>;
  facts?: Fact[];
  anchors?: Record<string, ScaleReference>;
}

/** Split text into plain runs and resolved figures, so each figure can render in its own tabular-nums span. */
export function splitTokens(text: string, c: TokenContext): TextPart[] {
  const facts = new Map((c.facts ?? []).map((f) => [f.id, f]));
  const parts: TextPart[] = [];
  let last = 0;
  for (const m of text.matchAll(TOKEN)) {
    const [, kind, key] = m as unknown as [string, "stat" | "fact", string];
    const figure = kind === "stat" ? c.stats[key] : facts.get(key);
    if (!figure) throw new Error(`token {${kind}:${key}} has no ${kind}`);
    if (m.index > last) parts.push({ kind: "text", text: text.slice(last, m.index) });
    const ref = c.anchors?.[key];
    parts.push({ kind, key, text: formatStat(figure), ...(ref ? { anchor: anchorText(ref, figure.value, figure.unit) } : {}) });
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push({ kind: "text", text: text.slice(last) });
  return parts;
}

/** Text with every token replaced by its formatted figure. */
export const fillTokens = (text: string, ctx: TokenContext) =>
  splitTokens(text, ctx)
    .map((p) => p.text)
    .join("");

/** The token context of a chapter: its stats, facts and scale anchors. */
export const chapterTokens = (chapter: { generated: { stats: Record<string, Stat> }; facts?: Fact[]; scaleAnchors?: Record<string, ScaleReference> }): TokenContext => ({
  stats: chapter.generated.stats,
  facts: chapter.facts,
  anchors: chapter.scaleAnchors,
});
