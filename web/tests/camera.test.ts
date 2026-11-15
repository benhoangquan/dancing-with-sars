import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { cameraAt, normalizeBearing, shortestArc } from "@/lib/camera";
import type { Camera, Waypoint } from "@/types/chapter";

type Golden = {
  tolerance: number;
  sets: Record<string, { waypoints: Waypoint[]; cases: { t: number; camera: Camera }[] }>;
};
const golden: Golden = JSON.parse(
  readFileSync(new URL("../../schema/golden/camera_interp.json", import.meta.url), "utf8"),
);
const digits = -Math.log10(golden.tolerance);

describe("cameraAt matches the shared golden vectors", () => {
  for (const [name, set] of Object.entries(golden.sets)) {
    for (const c of set.cases) {
      it(`${name} @ t=${c.t}`, () => {
        const got = cameraAt(set.waypoints, c.t);
        expect(got.center[0]).toBeCloseTo(c.camera.center[0], digits - 1);
        expect(got.center[1]).toBeCloseTo(c.camera.center[1], digits - 1);
        expect(got.zoom).toBeCloseTo(c.camera.zoom, digits - 1);
        expect(got.pitch).toBeCloseTo(c.camera.pitch, digits - 1);
        expect(got.bearing).toBeCloseTo(c.camera.bearing, digits - 1);
      });
    }
  }
});

describe("cameraAt", () => {
  const wps: Waypoint[] = [
    { t: 0, camera: { center: [0, 0], zoom: 8, pitch: 0, bearing: 0 } },
    { t: 10, camera: { center: [2, 4], zoom: 10, pitch: 60, bearing: 40 } },
  ];
  it("returns the mean at a segment midpoint for linear fields", () => {
    expect(cameraAt(wps, 5)).toEqual({ center: [1, 2], zoom: 9, pitch: 30, bearing: 20 });
  });
  it("clamps outside the range", () => {
    expect(cameraAt(wps, -50)).toEqual(wps[0].camera);
    expect(cameraAt(wps, 999)).toEqual(wps[1].camera);
  });
  it("needs two waypoints", () => {
    expect(() => cameraAt([wps[0]], 0)).toThrow();
  });
});

describe("bearing helpers", () => {
  it("normalizes into [-180, 180)", () => {
    expect(normalizeBearing(180)).toBe(-180);
    expect(normalizeBearing(-180)).toBe(-180);
    expect(normalizeBearing(540)).toBe(-180);
    expect(normalizeBearing(359)).toBe(-1);
  });
  it("takes the shortest arc, resolving a half turn to -180", () => {
    expect(shortestArc(170, -170)).toBe(20);
    expect(shortestArc(-170, 170)).toBe(-20);
    expect(shortestArc(0, 180)).toBe(-180);
  });
});
