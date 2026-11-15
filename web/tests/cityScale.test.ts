import { describe, expect, it } from "vitest";
import { areaHa, extentMetres, svgPath, toLocalMetres } from "@/lib/cityScale";

/** A square of `km` kilometres a side centred at lon/lat, in degrees. */
function square(lon: number, lat: number, km: number) {
  const dLat = km / 2 / 111.195;
  const dLon = dLat / Math.cos((lat * Math.PI) / 180);
  const ring: [number, number][] = [
    [lon - dLon, lat - dLat],
    [lon + dLon, lat - dLat],
    [lon + dLon, lat + dLat],
    [lon - dLon, lat + dLat],
    [lon - dLon, lat - dLat],
  ];
  return { type: "Polygon" as const, coordinates: [ring] };
}

describe("city scale", () => {
  it("measures 1 km² as 100 ha at Montreal and at Jakarta", () => {
    expect(areaHa(toLocalMetres(square(-73.6, 45.5, 1)))).toBeCloseTo(100, 0);
    expect(areaHa(toLocalMetres(square(106.8, -6.2, 1)))).toBeCloseTo(100, 0);
  });
  it("draws equal ground areas at equal pixel sizes whatever the latitude", () => {
    const a = toLocalMetres(square(-73.6, 45.5, 2));
    const b = toLocalMetres(square(106.8, -6.2, 2));
    const half = extentMetres(a, b);
    const width = (path: string) => {
      const xs = [...path.matchAll(/([\d.]+),([\d.]+)/g)].map((m) => Number(m[1]));
      return Math.max(...xs) - Math.min(...xs);
    };
    expect(width(svgPath(a, half, 320))).toBeCloseTo(width(svgPath(b, half, 320)), 0);
  });
  it("keeps north up", () => {
    const local = toLocalMetres(square(0, 50, 1));
    const path = svgPath(local, extentMetres(local), 100);
    const ys = [...path.matchAll(/([\d.]+),([\d.]+)/g)].map((m) => Number(m[2]));
    expect(ys[0]).toBeGreaterThan(ys[3]); // first vertex is the south-west corner, lower on screen
  });
  it("subtracts holes", () => {
    const outer = square(10, 0, 2).coordinates[0];
    const hole = square(10, 0, 1).coordinates[0];
    expect(areaHa(toLocalMetres({ type: "Polygon", coordinates: [outer, hole] }))).toBeCloseTo(300, 0);
  });
});
