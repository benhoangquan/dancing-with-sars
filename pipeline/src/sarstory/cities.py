"""`sar cities`: reference city outlines for the "Act Where You Live" comparison.

Boundaries come from OpenStreetMap (ODbL) through Nominatim, one request per city at most once a second, and
are simplified to about 100 m and stored in lon/lat under `web/public/cities/<id>.json`. Small islands are
dropped so the outline reads as the city most people picture.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

from shapely.geometry import MultiPolygon, mapping, shape

from .config import DATA_DIR

CITIES_DIR = DATA_DIR.parent / "cities"
USER_AGENT = "dancing-with-sars-pipeline/0.1 (NASA Space Apps 2026 project)"
# id -> (label, OSM relation id)
CITIES = {
    "montreal": ("Montréal", 1634158),
    "new-york": ("New York City", 175905),
    "toronto": ("Toronto", 324211),
    "london": ("Greater London", 175342),
    "jakarta": ("Jakarta", 6362934),
}
SIMPLIFY_DEG = 0.001
MIN_PART_SHARE = 0.01  # drop islands smaller than 1% of the largest part


def clean(geom: dict) -> dict:
    """Simplify and keep the parts that matter."""
    g = shape(geom).simplify(SIMPLIFY_DEG, preserve_topology=True)
    parts = list(g.geoms) if isinstance(g, MultiPolygon) else [g]
    big = max(p.area for p in parts)
    kept = [p for p in parts if p.area >= MIN_PART_SHARE * big]
    out = mapping(kept[0] if len(kept) == 1 else MultiPolygon(kept))

    def r(c):
        return [round(c[0], 5), round(c[1], 5)] if isinstance(c[0], float | int) else [r(x) for x in c]

    return {"type": out["type"], "coordinates": r(out["coordinates"])}


def fetch_city(relation: int) -> dict:
    query = urllib.parse.urlencode({"osm_ids": f"R{relation}", "format": "json", "polygon_geojson": 1})
    req = urllib.request.Request(
        f"https://nominatim.openstreetmap.org/lookup?{query}", headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 (fixed https host)
        found = json.load(r)
    if not found:
        raise RuntimeError(f"OSM relation {relation} not found")
    return found[0]["geojson"]


def build_cities(out: Path = CITIES_DIR, get=fetch_city, pause: float = 1.1, log=print) -> list[Path]:
    paths = []
    for cid, (label, relation) in CITIES.items():
        path = out / f"{cid}.json"
        if not path.exists():
            geom = clean(get(relation))
            path.parent.mkdir(parents=True, exist_ok=True)
            doc = {
                "id": cid,
                "label": label,
                "osm": f"relation/{relation}",
                "license": "ODbL, OpenStreetMap contributors",
                "geometry": geom,
            }
            path.write_text(json.dumps(doc, separators=(",", ":")) + "\n", encoding="utf-8")
            time.sleep(pause)
        log(f"  {cid}: {path.stat().st_size / 1e3:.0f} kB")
        paths.append(path)
    return paths
