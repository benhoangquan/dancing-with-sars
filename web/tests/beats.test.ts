import { describe, expect, it } from "vitest";
import {
  type Beat,
  type SectionBox,
  effectiveMode,
  locate,
  paneLayers,
  playHoldTime,
  radarCamera,
  scrubTime,
} from "@/lib/beats";
import { FlyoverClock, springStep } from "@/lib/clock";
import { useStory } from "@/lib/store";
import type { Waypoint } from "@/types/chapter";

const beat = (over: Partial<Beat["stage"]> = {}): Beat => ({
  id: "b",
  headline: "h",
  body: "b",
  stage: {
    mode: "radar",
    flyover: { from: 8, to: 16, playback: "scrub" },
    left: "sar_before",
    right: "sar_after",
    swipe: 0.5,
    ...over,
  },
});

describe("mode and layers", () => {
  it("lets a pin override the beat mode", () => {
    expect(effectiveMode(beat(), null)).toBe("radar");
    expect(effectiveMode(beat(), "split")).toBe("split");
  });
  it("shows the flyover layer alone in flyover mode", () => {
    expect(paneLayers(beat(), "flyover")).toEqual({ a: ["sar_before"], b: [] });
    expect(paneLayers(beat({ flyoverLayer: "optical_after", overlays: ["hv_change"] }), "flyover")).toEqual({
      a: ["optical_after"],
      b: [],
    });
  });
  it("puts left and right on A and B in radar mode, with overlays on the after side only", () => {
    expect(paneLayers(beat({ overlays: ["hv_change"] }), "radar")).toEqual({
      a: ["sar_before"],
      b: ["sar_after", "hv_change"],
    });
  });
  it("uses the flyover layer for pane 1 in split mode, overlays on pane 2 only", () => {
    expect(paneLayers(beat({ flyoverLayer: "optical_after", overlays: ["hv_change"] }), "split")).toEqual({
      a: ["optical_after"],
      b: ["sar_after", "hv_change"],
    });
  });
});

describe("flyover time", () => {
  const f = { from: 8, to: 16, playback: "scrub" as const };
  it("scrubs linearly and clamps progress", () => {
    expect(scrubTime(f, 0)).toBe(8);
    expect(scrubTime(f, 0.5)).toBe(12);
    expect(scrubTime(f, 1)).toBe(16);
    expect(scrubTime(f, -3)).toBe(8);
    expect(scrubTime(f, 9)).toBe(16);
  });
  it("plays at 1x from the start of the window and holds at the end", () => {
    expect(playHoldTime(f, 0)).toBe(8);
    expect(playHoldTime(f, 3)).toBe(11);
    expect(playHoldTime(f, 99)).toBe(16);
    expect(playHoldTime(f, -5)).toBe(8);
  });
});

describe("radar camera", () => {
  const wps: Waypoint[] = [
    { t: 0, camera: { center: [0, 0], zoom: 8, pitch: 0, bearing: 0 } },
    { t: 20, camera: { center: [2, 2], zoom: 10, pitch: 40, bearing: 20 } },
  ];
  it("uses the beat camera when set, else the flyover camera at the end of the window", () => {
    const own = { center: [1, 1] as [number, number], zoom: 12, pitch: 10, bearing: 5 };
    expect(radarCamera(beat({ camera: own }), wps)).toEqual(own);
    const fallback = radarCamera(beat({ flyover: { from: 0, to: 20, playback: "scrub" } }), wps);
    expect(fallback).toEqual({ center: [2, 2], zoom: 10, pitch: 40, bearing: 20 });
  });
});

describe("locate", () => {
  const boxes: SectionBox[] = [
    { kind: "hero", chapter: 0, beat: 0, top: 0, bottom: 100 },
    { kind: "header", chapter: 0, beat: 0, top: 100, bottom: 200 },
    { kind: "beat", chapter: 0, beat: 0, top: 200, bottom: 400 },
    { kind: "beat", chapter: 0, beat: 1, top: 400, bottom: 600 },
    { kind: "header", chapter: 1, beat: 0, top: 600, bottom: 700 },
    { kind: "beat", chapter: 1, beat: 0, top: 700, bottom: 900 },
    { kind: "outro", chapter: 1, beat: 0, top: 900, bottom: 1100 },
  ];
  it("reports progress inside a beat", () => {
    expect(locate(boxes, 300)).toEqual({ chapterIdx: 0, beatIdx: 0, p: 0.5 });
    expect(locate(boxes, 400)).toEqual({ chapterIdx: 0, beatIdx: 1, p: 0 });
    expect(locate(boxes, 599).beatIdx).toBe(1);
  });
  it("treats hero and headers as progress 0 of the next beat", () => {
    expect(locate(boxes, 50)).toEqual({ chapterIdx: 0, beatIdx: 0, p: 0 });
    expect(locate(boxes, 650)).toEqual({ chapterIdx: 1, beatIdx: 0, p: 0 });
  });
  it("treats the outro and anything below as the end of the last beat", () => {
    expect(locate(boxes, 1000)).toEqual({ chapterIdx: 1, beatIdx: 0, p: 1 });
    expect(locate(boxes, 5000)).toEqual({ chapterIdx: 1, beatIdx: 0, p: 1 });
  });
  it("handles a position above the first box and no boxes", () => {
    expect(locate(boxes, -40)).toEqual({ chapterIdx: 0, beatIdx: 0, p: 0 });
    expect(locate([], 10)).toEqual({ chapterIdx: 0, beatIdx: 0, p: 0 });
  });
});

describe("springStep", () => {
  it("converges to the target without overshooting from rest", () => {
    let s = { x: 0, v: 0 };
    let max = 0;
    for (let i = 0; i < 600; i++) {
      s = springStep(s, 10, 1 / 60);
      max = Math.max(max, s.x);
    }
    expect(s.x).toBeCloseTo(10, 4);
    expect(max).toBeLessThanOrEqual(10 + 1e-9);
  });
  it("gives the same result for one big step as many small ones", () => {
    let a = { x: 3, v: 0 };
    for (let i = 0; i < 60; i++) a = springStep(a, 8, 1 / 60);
    const b = springStep({ x: 3, v: 0 }, 8, 1);
    expect(a.x).toBeCloseTo(b.x, 9);
    expect(a.v).toBeCloseTo(b.v, 9);
  });
  it("stays put when already at the target", () => {
    expect(springStep({ x: 5, v: 0 }, 5, 0.016)).toEqual({ x: 5, v: 0 });
  });
});

describe("FlyoverClock", () => {
  const play = beat({ flyover: { from: 26, to: 36, playback: "play-hold" } });
  it("snaps to the target when reduced motion is on", () => {
    const c = new FlyoverClock();
    c.reduced = true;
    expect(c.update(0, 0.016, "0:0", beat(), 0.5)).toBe(12);
  });
  it("eases toward a scrub target", () => {
    const c = new FlyoverClock();
    const t1 = c.update(0, 0.016, "0:0", beat(), 1);
    expect(t1).toBeGreaterThan(0);
    expect(t1).toBeLessThan(16);
    let t = t1;
    for (let i = 0; i < 300; i++) t = c.update(i * 16, 0.016, "0:0", beat(), 1);
    expect(t).toBeCloseTo(16, 2);
  });
  it("plays a play-hold beat from its start, holds, and replays after a scrub beat", () => {
    const c = new FlyoverClock();
    c.reduced = true;
    expect(c.update(1000, 0.016, "0:4", play, 0)).toBe(26);
    expect(c.update(4000, 0.016, "0:4", play, 0)).toBe(29);
    expect(c.update(60000, 0.016, "0:4", play, 0)).toBe(36);
    c.update(61000, 0.016, "0:3", beat(), 0.5); // a scrub beat in between
    expect(c.update(70000, 0.016, "0:4", play, 0)).toBe(26);
  });
});

describe("store", () => {
  it("clears the pinned mode on chapter change only, and resets swipe per beat", () => {
    const s = useStory;
    s.setState({ chapterIdx: 0, beatIdx: 0, pinnedMode: null, swipe: 0.5 });
    s.getState().pinMode("split");
    s.getState().setSwipe(0.8);
    s.getState().setActive(0, 1, 0.3);
    expect(s.getState().pinnedMode).toBe("split");
    expect(s.getState().swipe).toBe(0.3);
    s.getState().setActive(1, 0, 0.5);
    expect(s.getState().pinnedMode).toBeNull();
    expect(s.getState().swipe).toBe(0.5);
  });
  it("keeps the user's swipe when the active beat has not changed", () => {
    const s = useStory;
    s.setState({ chapterIdx: 0, beatIdx: 2, pinnedMode: null, swipe: 0.5 });
    s.getState().setSwipe(0.9);
    s.getState().setActive(0, 2, 0.5);
    expect(s.getState().swipe).toBe(0.9);
  });
  it("clamps the swipe position", () => {
    useStory.getState().setSwipe(4);
    expect(useStory.getState().swipe).toBe(1);
    useStory.getState().setSwipe(-4);
    expect(useStory.getState().swipe).toBe(0);
  });
});
