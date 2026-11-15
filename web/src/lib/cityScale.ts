// Draw a chapter's footprint and a reference city at the same metres per pixel. Each shape is projected
// equirectangularly around its own centroid (accurate to well under 1% across a city), so shapes from different
// latitudes compare fairly. Pure, so it is unit-tested.

type Ring = [number, number][];
type Geometry = { type: "Polygon"; coordinates: Ring[] } | { type: "MultiPolygon"; coordinates: Ring[][] };

const R = 6_371_008.8; // mean Earth radius, m

export const polygonsOf = (g: Geometry): Ring[][] => (g.type === "Polygon" ? [g.coordinates] : g.coordinates);

function centroid(g: Geometry): [number, number] {
  let x = 0;
  let y = 0;
  let n = 0;
  for (const poly of polygonsOf(g))
    for (const [lon, lat] of poly[0]) {
      x += lon;
      y += lat;
      n += 1;
    }
  return [x / n, y / n];
}

/** Rings in metres east and north of the geometry's own centroid. */
export function toLocalMetres(g: Geometry): Ring[][] {
  const [lon0, lat0] = centroid(g);
  const k = Math.cos((lat0 * Math.PI) / 180);
  return polygonsOf(g).map((poly) =>
    poly.map((ring) => ring.map(([lon, lat]) => [(((lon - lon0) * Math.PI) / 180) * R * k, (((lat - lat0) * Math.PI) / 180) * R] as [number, number])),
  );
}

/** Shoelace area of local-metre polygons (outer ring minus holes), in hectares. */
export function areaHa(polys: Ring[][]): number {
  const ring = (r: Ring) => {
    let a = 0;
    for (let i = 0; i < r.length - 1; i++) a += r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1];
    return Math.abs(a) / 2;
  };
  return polys.reduce((sum, [outer, ...holes]) => sum + ring(outer) - holes.reduce((h, r) => h + ring(r), 0), 0) / 10_000;
}

/** Half-width of the box (metres) that holds every shape. */
export function extentMetres(...shapes: Ring[][][]): number {
  let m = 0;
  for (const polys of shapes) for (const poly of polys) for (const ring of poly) for (const [x, y] of ring) m = Math.max(m, Math.abs(x), Math.abs(y));
  return m;
}

/** An SVG path for local-metre polygons in a `size`-pixel square that spans ±`halfMetres`. North is up. */
export function svgPath(polys: Ring[][], halfMetres: number, size: number): string {
  const s = size / (2 * halfMetres);
  const pt = ([x, y]: [number, number]) => `${(size / 2 + x * s).toFixed(1)},${(size / 2 - y * s).toFixed(1)}`;
  return polys.map((poly) => poly.map((ring) => `M${ring.map(pt).join("L")}Z`).join("")).join("");
}
