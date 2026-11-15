"""`sar build` for chapters that show NISAR imagery without a change measurement (`[real] mode = "imagery"`).

Used where the radar record does not support a defensible change number (Demak: the 2026 change is the rice
cycle). The radar layer is real: a median composite of every cached date. Numbers in the story come from cited
facts in the authored manifest, and the city-scale footprint is a square of a cited area.
"""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from pathlib import Path

from .. import __version__
from ..cog import write_layer
from ..composite import DEFAULT_STRETCH, sar_composite
from ..config import CACHE_DIR, CHAPTERS_DIR, DATA_DIR, load_config
from ..fixture import flyover_from_config
from ..manifest import read_manifest, write_manifest
from ..optical import Lattice, build_layers
from .analysis import load_stack, median_db
from .build import nisar_source, span, stat


def equal_area_square(center: list[float], area_ha: float) -> dict:
    """A square of `area_ha` centred on `center` (lon, lat), in lon/lat degrees at that latitude."""
    side_m = math.sqrt(area_ha * 10_000.0)
    lon, lat = center
    dlat = side_m / 2 / 111_320.0
    dlon = side_m / 2 / (111_320.0 * math.cos(math.radians(lat)))
    ring = [
        [lon - dlon, lat - dlat],
        [lon + dlon, lat - dlat],
        [lon + dlon, lat + dlat],
        [lon - dlon, lat + dlat],
    ]
    ring.append(ring[0])
    return {"type": "Polygon", "coordinates": [[[round(x, 6), round(y, 6)] for x, y in ring]]}


def build(
    slug: str,
    *,
    data_dir: Path = DATA_DIR,
    chapters_dir: Path = CHAPTERS_DIR,
    cache_root: Path = CACHE_DIR,
    optical: bool | str = True,
    log=print,
) -> Path:
    cfg = load_config(slug)
    real, proc = cfg["real"], cfg["processing"]
    manifest = read_manifest(slug, chapters_dir)
    index = json.loads((cache_root / slug / "acquisitions.json").read_text())
    stack = load_stack(slug, index, cache_root)
    h, w = stack.hv.shape[1:]
    stretch = {k: tuple(proc.get(f"stretch_{k.lower()}", DEFAULT_STRETCH[k])) for k in DEFAULT_STRETCH}
    log(f"  {len(stack.days)} radar dates, {span(stack.days)}")
    layers = [
        write_layer(
            slug,
            "sar_2026",
            kind="sar-composite",
            label="Radar composite, 2026",
            date=span(stack.days),
            data=sar_composite(median_db(stack.hh), median_db(stack.hv), stretch),
            transform=stack.transform,
            crs=f"EPSG:{stack.epsg}",
            render={"type": "rgba"},
            source_ids=["nisar-gcov"],
            status="real",
            stretch=stretch,
            data_dir=data_dir,
        )
    ]
    sources = [nisar_source(index, stack)]
    old = manifest.get("generated", {})
    if optical == "reuse":
        kept = [x for x in old.get("layers", []) if x["kind"] == "optical" and x["status"] == "real"]
        hls = next((x for x in old.get("sources", []) if x["id"] == "hls"), None)
        if not kept or hls is None:
            raise RuntimeError(f"{slug}: no real optical layers to reuse; run a full build first")
        layers = kept + layers
        sources.append(hls)
    elif optical:
        o_layers, hls, _ = build_layers(
            slug,
            cfg["optical"],
            manifest["aoi"]["bbox"],
            Lattice(stack.transform, w, h, stack.epsg),
            data_dir,
            log=log,
        )
        order = {spec["id"]: i for i, spec in enumerate(cfg["optical"])}
        layers = sorted(o_layers, key=lambda x: order[x["id"]]) + layers
        sources.append(hls)

    facts = {f["id"]: f for f in manifest.get("facts", [])}
    fact = facts[real["footprint_fact"]]
    cited = {
        "id": "cited",
        "mission": "Published study",
        "product": fact["source"]["name"],
        "collection": "n/a",
        "maturity": "n/a",
        "granules": [],
        "dates": [fact["source"]["accessed"]],
        "provider": fact["source"]["name"],
        "license": "Cited, not redistributed",
        "url": fact["source"]["url"],
        "nasa": False,
    }
    generated = {
        "pipelineVersion": f"{__version__}+nisar-imagery",
        "builtAt": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "layers": layers,
        "series": [],
        "stats": {
            "n_dates": stat(
                len(stack.days), "count", 0, "Radar dates", "NISAR acquisition dates in the composite."
            )
        },
        "flyover": flyover_from_config(cfg),
        "annotations": [],
        "sources": [*sources, cited],
        "footprint": {
            "kind": "equal-area",
            "label": fact["label"],
            "areaHa": float(fact["value"]),
            "geometry": equal_area_square(manifest["globe"]["pin"], float(fact["value"])),
            "sourceIds": ["cited"],
            "status": "fallback",
        },
    }
    manifest["generated"] = generated
    return write_manifest(slug, manifest, chapters_dir)
