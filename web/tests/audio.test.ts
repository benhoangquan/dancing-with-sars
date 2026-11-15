import { describe, expect, it } from "vitest";
import { chapterProgress, crossfade } from "@/lib/audio";

describe("soundscape crossfade", () => {
  it("is all before at the start and all after at the end", () => {
    expect(crossfade(0)).toEqual([1, 0]);
    const [a, b] = crossfade(1);
    expect(a).toBeCloseTo(0);
    expect(b).toBeCloseTo(1);
  });
  it("keeps constant power in between", () => {
    for (const p of [0.1, 0.5, 0.9]) {
      const [a, b] = crossfade(p);
      expect(a * a + b * b).toBeCloseTo(1);
    }
    expect(crossfade(-1)).toEqual(crossfade(0));
  });
  it("tracks progress through a chapter's beats", () => {
    expect(chapterProgress(0, 0, 5)).toBe(0);
    expect(chapterProgress(2, 0.5, 5)).toBeCloseTo(0.5);
    expect(chapterProgress(4, 1, 5)).toBe(1);
  });
});
