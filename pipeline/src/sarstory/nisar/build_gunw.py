"""`sar build` for GUNW chapters: cached interferogram windows in, a chapter manifest with real layers out.

Needs `sar fetch` to have run. The unwrapped phase of each sequential pair becomes line-of-sight motion, the
pairs are referenced and summed (see `gunw_analysis`), and the result is written as a displacement layer.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
from scipy import ndimage

from .. import __version__
from ..change import largest_patches
from ..cog import write_layer
from ..config import CACHE_DIR, CHAPTERS_DIR, DATA_DIR, load_config
from ..fixture import COHERENCE_RENDER, DISPLACEMENT_RENDER, flyover_from_config
from ..manifest import read_manifest, write_manifest
from ..optical import Lattice, build_layers
from .build import pixel_to_lonlat, points, stat
from .fetch import load_pair, tile_path
from .gunw import Pair, los_motion_cm
from .gunw_analysis import (
    AREA_THRESHOLD_CM,
    GunwAnalysis,
    PairMotion,
    analyze_gunw,
    dominant_component,
    remove_plane,
    smooth_nan,
)

GUNW_URL = "https://www.earthdata.nasa.gov/data/catalog/asf-nisar-l2-gunw-provisional-v1-1"


def load_pairs(slug: str, index: dict, root: Path = CACHE_DIR) -> tuple[list[PairMotion], Pair]:
    """The cached pairs as motion in centimetres, all on one grid. Returns the first pair for its grid."""
    motions, first = [], None
    for p in index["pairs"]:
        pair = load_pair(tile_path(slug, p["name"], root))
        if first is None:
            first = pair
        elif (pair.phase.shape, pair.x0, pair.y0, pair.epsg) != (
            first.phase.shape,
            first.x0,
            first.y0,
            first.epsg,
        ):
            raise ValueError(f"{p['name']}: not on the same grid as the first pair")
        phase = pair.phase - np.where(
            np.isfinite(pair.ionosphere), pair.ionosphere, 0.0
        )  # ionosphere removed
        phase[~dominant_component(pair.components)] = (
            np.nan
        )  # one component only: each has its own 2 pi offset
        motions.append(
            PairMotion(
                date.fromisoformat(p["reference"]),
                date.fromisoformat(p["secondary"]),
                remove_plane(los_motion_cm(phase, pair.wavelength_m)),
                pair.coherence,
            )
        )
    if first is None:
        raise ValueError(f"{slug}: no cached interferograms")
    return motions, first


def gunw_annotations(specs: list[dict], grid: Pair, an: GunwAnalysis) -> list[dict]:
    """The deepest point as a pin and the area sinking past the threshold as an outline."""
    out = []
    smooth = smooth_nan(an.final_cm)
    for spec in specs:
        if spec["kind"] == "hotspot_pin":
            r, c = an.hotspot
            geometry = {"type": "Point", "coordinates": pixel_to_lonlat(grid, [r + 0.5], [c + 0.5])[0]}
            kind = "pin"
        else:
            labels, n = ndimage.label(np.nan_to_num(smooth) < -AREA_THRESHOLD_CM)
            if not n:
                continue
            sizes = ndimage.sum(labels > 0, labels, index=np.arange(1, n + 1))
            r0, c0, r1, c1 = largest_patches(labels == int(np.argmax(sizes)) + 1, 1)[0]
            ring = pixel_to_lonlat(grid, [r0, r0, r1, r1, r0], [c0, c1, c1, c0, c0])
            geometry, kind = {"type": "Polygon", "coordinates": [ring]}, "area"
        out.append({"id": spec["id"], "label": spec["label"], "kind": kind, "geometry": geometry})
    return out


def gunw_source(index: dict) -> dict:
    return {
        "id": "nisar-gunw",
        "mission": "NISAR",
        "product": "L2 GUNW, geocoded unwrapped interferogram (HH)",
        "collection": index["collection"],
        "maturity": index["maturity"],
        "granules": [p["name"] for p in index["pairs"]],
        "dates": sorted({d for p in index["pairs"] for d in (p["reference"], p["secondary"])}),
        "provider": "NASA-ISRO, distributed by the ASF DAAC",
        "license": "Open and free to use under NASA's Earth science data policy; cite NISAR and the ASF DAAC",
        "url": GUNW_URL,
        "nasa": True,
    }


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
    manifest = read_manifest(slug, chapters_dir)
    index = json.loads((cache_root / slug / "pairs.json").read_text())
    motions, grid = load_pairs(slug, index, cache_root)
    an = analyze_gunw(motions, pixel_area_m2=grid.res**2)
    span = f"{an.dates[0]}/{an.dates[-1]}"
    log(
        f"  deepest {an.stats['max_subsidence_cm']:.1f} cm at pixel {an.hotspot}, "
        f"{an.stats['area_over_5cm_ha']:,.0f} ha past {AREA_THRESHOLD_CM:g} cm, {len(motions)} pairs"
    )
    layers = []
    for layer_id, kind, label, data, render in (
        (
            "displacement",
            "displacement",
            "Ground motion along the radar line of sight",
            an.final_cm,
            DISPLACEMENT_RENDER,
        ),
        ("coherence", "coherence", "Radar coherence", an.coherence, COHERENCE_RENDER),
    ):
        layers.append(
            write_layer(
                slug,
                layer_id,
                kind=kind,
                label=label,
                date=span,
                data=data.astype(np.float32),
                transform=grid.transform,
                crs=f"EPSG:{grid.epsg}",
                render=render,
                source_ids=["nisar-gunw"],
                status="real",
                data_dir=data_dir,
            )
        )
    sources = [gunw_source(index)]
    old = manifest.get("generated", {})
    if optical == "reuse":
        kept = [lyr for lyr in old.get("layers", []) if lyr["kind"] == "optical" and lyr["status"] == "real"]
        hls = next((x for x in old.get("sources", []) if x["id"] == "hls"), None)
        if not kept or hls is None:
            raise RuntimeError(f"{slug}: no real optical layers to reuse; run a full build first")
        layers, sources = kept + layers, sources + [hls]
    elif optical:
        height, width = an.final_cm.shape
        o_layers, hls, _ = build_layers(
            slug,
            cfg["optical"],
            manifest["aoi"]["bbox"],
            Lattice(grid.transform, width, height, grid.epsg),
            data_dir,
            log=log,
        )
        layers, sources = o_layers + layers, sources + [hls]
    method = f"NISAR {index['collection']}, sequential pairs summed, each referenced to its scene median."
    stats = {
        "max_subsidence_cm": stat(
            an.stats["max_subsidence_cm"],
            "cm",
            1,
            "Deepest sinking",
            f"Largest downward motion of the smoothed cumulative map. {method}",
        ),
        "area_over_5cm_ha": stat(
            an.stats["area_over_5cm_ha"],
            "ha",
            0,
            "Area sinking past 5 cm",
            f"Area of the smoothed map below -{AREA_THRESHOLD_CM:g} cm. {method}",
        ),
        "rate_cm_per_month": stat(
            an.stats["rate_cm_per_month"],
            "cm/month",
            1,
            "Sinking rate at the deepest point",
            "Deepest sinking divided by the span of the series in months.",
        ),
        "n_pairs": stat(
            an.stats["n_pairs"], "count", 0, "Interferograms", "Sequential date pairs in the series."
        ),
    }
    series = {
        "id": "displacement_hotspot",
        "label": "Ground motion at the deepest point",
        "unit": "cm",
        "kind": "displacement",
        "points": points(an.hotspot_series),
        "sourceIds": ["nisar-gunw"],
        "status": "real",
    }
    if an.reference_series:
        series["reference"] = {"label": "Stable reference area", "points": points(an.reference_series)}
    manifest["generated"] = {
        "pipelineVersion": f"{__version__}+nisar",
        "builtAt": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "layers": layers,
        "series": [series],
        "stats": stats,
        "flyover": flyover_from_config(cfg),
        "annotations": gunw_annotations(cfg["annotations"], grid, an),
        "sources": sources,
    }
    return write_manifest(slug, manifest, chapters_dir)
