"""`sar overture`: human infrastructure drawn on the radar stage (Layer 1 of the story).

Buildings and road segments come from Overture Maps (GeoParquet, read with the `overturemaps` client, ODbL);
Indigenous and protected areas come from OpenStreetMap through Nominatim (ODbL). Everything is clipped to the
chapter's `[impact]` area, simplified, and written as one small GeoJSON. Counts near the chapter's footprint
become stats only when that footprint is a real shape (measured, or a mapped perimeter), never a stand-in
square.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

from shapely.geometry import box, mapping, shape
from shapely.ops import transform

from .cog import sha256_file
from .config import CHAPTERS_DIR, DATA_DIR, load_config
from .manifest import read_manifest, write_manifest

MAX_BYTES = 400_000
USER_AGENT = "dancing-with-sars-pipeline/0.1 (NASA Space Apps 2026 project)"
OVERTURE = {
    "id": "overture",
    "mission": "Overture Maps",
    "product": "Overture Maps buildings and transportation themes",
    "collection": "overturemaps-us-west-2",
    "maturity": "n/a",
    "granules": [],
    "dates": [],
    "provider": "Overture Maps Foundation",
    "license": "ODbL (buildings and roads include OpenStreetMap data, (c) OpenStreetMap contributors)",
    "url": "https://overturemaps.org/",
    "nasa": False,
}
OSM = {
    "id": "osm",
    "mission": "OpenStreetMap",
    "product": "Indigenous and protected area boundaries",
    "collection": "OpenStreetMap relations via Nominatim",
    "maturity": "n/a",
    "granules": [],
    "dates": [],
    "provider": "OpenStreetMap contributors",
    "license": "ODbL, (c) OpenStreetMap contributors",
    "url": "https://www.openstreetmap.org/copyright",
    "nasa": False,
}


def overture(kind: str, bbox: list[float]) -> list[dict]:
    """Features of one Overture type (`building` or `segment`) in bbox, via the overturemaps command line."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / f"{kind}.geojson"
        cmd = [
            sys.executable,
            "-m",
            "overturemaps.cli",
            "download",
            f"--bbox={','.join(map(str, bbox))}",
            "-f",
            "geojson",
            f"--type={kind}",
            "-o",
            str(out),
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=900)
        return json.loads(out.read_text())["features"]


def osm_relation(relation: int) -> dict:
    query = urllib.parse.urlencode(
        {"osm_ids": f"R{relation}", "format": "json", "polygon_geojson": 1, "polygon_threshold": 0.001}
    )
    req = urllib.request.Request(
        f"https://nominatim.openstreetmap.org/lookup?{query}", headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 (fixed https host)
        found = json.load(r)
    if not found:
        raise RuntimeError(f"OSM relation {relation} not found")
    return {
        "name": found[0].get("name") or found[0]["display_name"].split(",")[0],
        "geometry": found[0]["geojson"],
    }


def _metric(epsg: int):
    """A shapely-compatible function from lon/lat to metres in `epsg`."""
    from rasterio.warp import transform as warp

    def project(x, y, z=None):
        xs, ys = warp("EPSG:4326", f"EPSG:{epsg}", list(x), list(y))
        return xs, ys

    return project


def utm_epsg(lon: float, lat: float) -> int:
    return (32600 if lat >= 0 else 32700) + int((lon + 180) // 6) + 1


def round_geom(geom: dict, nd: int = 5) -> dict:
    def r(c):
        return [round(c[0], nd), round(c[1], nd)] if isinstance(c[0], float | int) else [r(x) for x in c]

    return {"type": geom["type"], "coordinates": r(geom["coordinates"])}


def build_impact(
    slug: str,
    *,
    data_dir: Path = DATA_DIR,
    chapters_dir: Path = CHAPTERS_DIR,
    get=overture,
    rel=osm_relation,
    log=print,
) -> Path:
    cfg = load_config(slug)
    spec = cfg["impact"]
    manifest = read_manifest(slug, chapters_dir)
    gen = manifest["generated"]
    area = box(*spec["area"])
    fp = gen.get("footprint")
    real_shape = fp is not None and fp["kind"] == "shape"
    lon0, lat0 = area.centroid.x, area.centroid.y
    to_m = _metric(utm_epsg(lon0, lat0))
    near_m = float(spec.get("near_m", 2000))
    near_zone = transform(to_m, shape(fp["geometry"])).buffer(near_m) if real_shape else None

    features: list[dict] = []
    counts: dict[str, int] = {}
    if spec.get("buildings"):
        found = [f for f in get("building", spec["area"]) if shape(f["geometry"]).intersects(area)]
        near = 0
        for f in found:
            g = shape(f["geometry"])
            is_near = bool(near_zone is not None and near_zone.intersects(transform(to_m, g)))
            near += is_near
            # Dense villages: one point per building keeps the file inside the budget.
            geom = g.representative_point() if spec.get("building_points") else g.simplify(0.00002)
            props = {"kind": "building", "near": is_near}
            if spec.get("near_only") and not is_near:
                continue  # dense areas: draw only the buildings near the footprint; counts still cover all
            features.append(
                {"type": "Feature", "properties": props, "geometry": round_geom(mapping(geom), 4)}
            )
        counts["buildings"] = len(found)
        if near_zone is not None:
            counts["buildings_near"] = near
        log(
            f"  {len(found)} buildings" + (f", {near} within {near_m:.0f} m" if near_zone is not None else "")
        )
    if spec.get("roads"):
        classes = set(spec.get("road_classes", []))
        km_near = 0.0
        n = 0
        for f in get("segment", spec["area"]):
            p = f["properties"]
            if p.get("subtype") != "road" or (classes and p.get("class") not in classes):
                continue
            g = shape(f["geometry"]).intersection(area)
            if g.is_empty:
                continue
            gm = transform(to_m, g)
            is_near = bool(near_zone is not None and near_zone.intersects(gm))
            if near_zone is not None:
                km_near += gm.intersection(near_zone).length / 1000
            n += 1
            features.append(
                {
                    "type": "Feature",
                    "properties": {"kind": "road", "class": p.get("class"), "near": is_near},
                    "geometry": round_geom(mapping(g.simplify(0.0001))),
                }
            )
        counts["road_segments"] = n
        if near_zone is not None:
            counts["road_km_near"] = round(km_near)
        log(
            f"  {n} road segments"
            + (f", {km_near:.0f} km within {near_m:.0f} m" if near_zone is not None else "")
        )
    for relation in spec.get("territories", []):
        t = rel(relation)
        g = shape(t["geometry"]).simplify(0.002, preserve_topology=True)
        features.append(
            {
                "type": "Feature",
                "properties": {"kind": "territory", "name": t["name"], "near": False},
                "geometry": round_geom(mapping(g), 4),
            }
        )
        counts["territories"] = counts.get("territories", 0) + 1
        log(f"  territory: {t['name']}")

    path = data_dir / slug / "impact.geojson"
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":"))
    if len(text.encode()) > MAX_BYTES:
        raise RuntimeError(
            f"{slug}: impact overlay is {len(text) / 1e3:.0f} kB, over the {MAX_BYTES / 1e3:.0f} kB budget; "
            "shrink the [impact] area"
        )
    path.write_text(text, encoding="utf-8")
    source_ids = (["overture"] if spec.get("buildings") or spec.get("roads") else []) + (
        ["osm"] if spec.get("territories") else []
    )
    gen["impact"] = {
        "geojson": path.relative_to(data_dir.parent).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "counts": counts,
        "sourceIds": source_ids,
    }
    keep = [s for s in gen["sources"] if s["id"] not in {"overture", "osm"}]
    gen["sources"] = keep + [s for s in (OVERTURE, OSM) if s["id"] in source_ids]
    for key, label, unit, method in (
        (
            "buildings_near",
            f"Buildings mapped within {near_m / 1000:g} km of the {fp['label'] if fp else ''}",
            "count",
            "Overture Maps building footprints intersecting a buffer around the footprint.",
        ),
        (
            "road_km_near",
            f"Road within {near_m / 1000:g} km of the {fp['label'] if fp else ''}",
            "km",
            "Length of Overture Maps road segments inside a buffer around the footprint.",
        ),
    ):
        if key in counts:
            gen["stats"][f"impact_{key}"] = {
                "value": counts[key],
                "unit": unit,
                "decimals": 0,
                "label": label.strip(),
                "method": method,
            }
    return write_manifest(slug, manifest, chapters_dir)
