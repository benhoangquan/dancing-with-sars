import { describe, expect, it } from "vitest";
import { densifyRing, hexToRgb, ringCentroid, ringLabelAnchor } from "@/lib/annotations";

describe("annotation geometry helpers", () => {
  const ring = [
    [0, 0],
    [4, 0],
    [4, 2],
    [0, 2],
    [0, 0],
  ];
  it("parses hex colors", () => {
    expect(hexToRgb("#ff8000")).toEqual([255, 128, 0]);
  });
  it("densifies a closed ring, keeping its corners and closing exactly", () => {
    const out = densifyRing(ring, 4);
    expect(out).toHaveLength(4 * 4 + 1);
    expect(out[0]).toEqual([0, 0]);
    expect(out[4]).toEqual([4, 0]);
    expect(out[out.length - 1]).toEqual([0, 0]);
    expect(out[2]).toEqual([2, 0]);
  });
  it("finds the centroid from distinct corners, ignoring the repeated closing point", () => {
    expect(ringCentroid(ring)).toEqual([2, 1]);
  });
  it("anchors an area label over the middle of its northern edge", () => {
    expect(ringLabelAnchor(ring)).toEqual([2, 2]);
  });
});
