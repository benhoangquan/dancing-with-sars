// `{stat:key}` tokens in story text resolve against generated.stats, so numbers in copy come from the pipeline.
import type { Stat } from "@/types/chapter";
import { formatStat } from "./format";

const TOKEN = /\{stat:([a-z0-9_]+)\}/g;

export type TextPart = { kind: "text"; text: string } | { kind: "stat"; key: string; text: string };

/** Split text into plain runs and resolved stat runs, so a stat can render in its own tabular-nums span. */
export function splitTokens(text: string, stats: Record<string, Stat>): TextPart[] {
  const parts: TextPart[] = [];
  let last = 0;
  for (const m of text.matchAll(TOKEN)) {
    const stat = stats[m[1]];
    if (!stat) throw new Error(`token {stat:${m[1]}} has no stat`);
    if (m.index > last) parts.push({ kind: "text", text: text.slice(last, m.index) });
    parts.push({ kind: "stat", key: m[1], text: formatStat(stat) });
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push({ kind: "text", text: text.slice(last) });
  return parts;
}

/** Text with every token replaced by its formatted stat. */
export const fillTokens = (text: string, stats: Record<string, Stat>) =>
  splitTokens(text, stats)
    .map((p) => p.text)
    .join("");
