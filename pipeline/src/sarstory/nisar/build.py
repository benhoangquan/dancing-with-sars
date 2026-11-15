"""`sar build` for GCOV chapters: cached tiles in, a chapter manifest with real layers out.

Needs `sar fetch` to have run. Radar layers come from the cache (offline); optical layers are read from
Planetary Computer unless `optical=False`.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
from rasterio.warp import transform as warp_points
from scipy import ndimage

from .. import __version__
from ..change import largest_patches
from ..cog import write_layer
from ..composite import DEFAULT_STRETCH, sar_composite
from ..config import CACHE_DIR, CHAPTERS_DIR, DATA_DIR, load_config
from ..fixture import HV_DROP_RENDER, flyover_from_config
from ..manifest import read_manifest, write_manifest
from ..optical import Lattice, build_layers
from .analysis import Analysis, Stack, analyze, load_stack

NISAR_URL = "https://www.earthdata.nasa.gov/data/catalog/asf-nisar-l2-gcov-provisional-v1-1"
WATER_DB = -24.0  # L-band HV over open water, in both windows


def stat(value: float, unit: str, decimals: int, label: str, method: str) -> dict:
    return {
        "value": round(float(value), decimals),
        "unit": unit,
        "decimals": decimals,
        "label": label,
        "method": method,
    }


def span(days: list[date]) -> str:
    return days[0].isoformat() if len(days) == 1 else f"{days[0].isoformat()}/{days[-1].isoformat()}"


def points(rows: list[tuple[date, float]]) -> list[dict]:
    return [{"t": d.isoformat(), "v": round(v, 2)} for d, v in rows]


def pixel_to_lonlat(stack: Stack, rows, cols) -> list[list[float]]:
    xs = [stack.transform.c + c * stack.res for c in cols]
    ys = [stack.transform.f - r * stack.res for r in rows]
    lon, lat = warp_points(f"EPSG:{stack.epsg}", "EPSG:4326", xs, ys)
    return [[round(a, 6), round(b, 6)] for a, b in zip(lon, lat, strict=True)]


def _largest(mask: np.ndarray) -> np.ndarray | None:
    labels, n = ndimage.label(mask)
    if not n:
        return None
    sizes = ndimage.sum(mask, labels, index=np.arange(1, n + 1))
    return labels == (int(np.argmax(sizes)) + 1)


def annotations(specs: list[dict], stack: Stack, an: Analysis) -> list[dict]:
    """Pins and outlines from the data: the largest loss patch and, if asked, the largest water body."""
    out = []
    for spec in specs:
        kind = spec["kind"]
        if kind == "water_pin":
            patch = _largest((an.before_hv < WATER_DB) & (an.after_hv < WATER_DB))
            if patch is None or patch.sum() < 50:
                continue
        else:
            patch = _largest(an.mask)
            if patch is None:
                continue
        if kind == "patch_area":
            r0, c0, r1, c1 = largest_patches(patch, 1)[0]
            ring = pixel_to_lonlat(stack, [r0, r0, r1, r1, r0], [c0, c1, c1, c0, c0])
            geometry = {"type": "Polygon", "coordinates": [ring]}
        else:
            r, c = ndimage.center_of_mass(patch)
            geometry = {"type": "Point", "coordinates": pixel_to_lonlat(stack, [r + 0.5], [c + 0.5])[0]}
        out.append(
            {
                "id": spec["id"],
                "label": spec["label"],
                "kind": "area" if kind == "patch_area" else "pin",
                "geometry": geometry,
            }
        )
    return out


def mask_footprint(mask: np.ndarray, stack: Stack, area_ha: float, label: str) -> dict | None:
    """The loss mask as a simplified lon/lat MultiPolygon, for the city-scale comparison."""
    from rasterio.features import shapes
    from rasterio.warp import transform_geom
    from shapely.geometry import MultiPolygon, mapping, shape

    polys = [
        shape(transform_geom(f"EPSG:{stack.epsg}", "EPSG:4326", geom))
        for geom, v in shapes(mask.astype(np.uint8), mask=mask, transform=stack.transform)
        if v == 1
    ]
    if not polys:
        return None
    multi = MultiPolygon([p for p in polys if p.geom_type == "Polygon"]).simplify(
        0.0002, preserve_topology=True
    )

    def r(c):
        return [round(c[0], 6), round(c[1], 6)] if isinstance(c[0], float | int) else [r(x) for x in c]

    geom = mapping(multi)
    return {
        "kind": "shape",
        "label": label,
        "areaHa": round(float(area_ha), 1),
        "geometry": {"type": geom["type"], "coordinates": r(geom["coordinates"])},
        "sourceIds": ["nisar-gcov"],
        "status": "real",
    }


def nisar_source(index: dict, stack: Stack) -> dict:
    return {
        "id": "nisar-gcov",
        "mission": "NISAR",
        "product": "L2 GCOV, geocoded polarimetric covariance (HH, HV)",
        "collection": index["collection"],
        "maturity": index["maturity"],
        "granules": sorted({n for names in stack.granules.values() for n in names}),
        "dates": [d.isoformat() for d in stack.days],
        "provider": "NASA-ISRO, distributed by the ASF DAAC",
        "license": "Open and free to use under NASA's Earth science data policy; cite NISAR and the ASF DAAC",
        "url": NISAR_URL,
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
    index = json.loads((cache_root / slug / "acquisitions.json").read_text())
    stack = load_stack(slug, index, cache_root)
    proc, win, real = cfg["processing"], cfg["windows"], cfg["real"]
    an = analyze(
        stack,
        before=tuple(win["before"]),
        after=tuple(win["after"]),
        max_dates=proc["max_dates"],
        drop_threshold_db=proc["drop_threshold_db"],
        min_before_db=proc["min_before_db"],
        mmu_ha=proc["mmu_ha"],
    )
    log(
        f"  {an.stats['area_ha']:,.0f} ha of loss, HV drop {an.stats['hv_drop_db']:.1f} dB, "
        f"{len(an.series)} dates"
    )
    stretch = {k: tuple(proc.get(f"stretch_{k.lower()}", DEFAULT_STRETCH[k])) for k in DEFAULT_STRETCH}
    maturity_note = f"NISAR {index['collection']}"
    layers = []

    def add(layer_id, kind, label, date_text, data, render, stretch_=None):
        layers.append(
            write_layer(
                slug,
                layer_id,
                kind=kind,
                label=label,
                date=date_text,
                data=data,
                transform=stack.transform,
                crs=f"EPSG:{stack.epsg}",
                render=render,
                source_ids=["nisar-gcov"],
                status="real",
                stretch=stretch_,
                data_dir=data_dir,
            )
        )

    add(
        "sar_before",
        "sar-composite",
        "Radar composite, before",
        span(an.before_days),
        sar_composite(an.before_hh, an.before_hv, stretch),
        {"type": "rgba"},
        stretch,
    )
    add(
        "sar_after",
        "sar-composite",
        "Radar composite, after",
        span(an.after_days),
        sar_composite(an.after_hh, an.after_hv, stretch),
        {"type": "rgba"},
        stretch,
    )
    add(
        "hv_change",
        "change",
        "Radar HV drop",
        f"{an.before_days[0]}/{an.after_days[-1]}",
        np.where(an.mask, an.drop, np.nan).astype(np.float32),
        HV_DROP_RENDER,
    )

    sources = [nisar_source(index, stack)]
    extras: dict[str, float] = {}
    old = manifest.get("generated", {})
    if optical == "reuse":  # keep the optical layers already built, so tuning needs no network
        kept = [lyr for lyr in old.get("layers", []) if lyr["kind"] == "optical" and lyr["status"] == "real"]
        hls = next((x for x in old.get("sources", []) if x["id"] == "hls"), None)
        if not kept or hls is None:
            raise RuntimeError(f"{slug}: no real optical layers to reuse; run a full build first")
        layers = kept + layers
        sources.append(hls)
        if "smoke_cloud_pct" in old.get("stats", {}):
            extras["optical_smoke_blocked_pct"] = old["stats"]["smoke_cloud_pct"]["value"]
    elif optical:
        height, width = an.mask.shape
        o_layers, hls, extras = build_layers(
            slug,
            cfg["optical"],
            manifest["aoi"]["bbox"],
            Lattice(stack.transform, width, height, stack.epsg),
            data_dir,
            log=log,
        )
        order = {spec["id"]: i for i, spec in enumerate(cfg["optical"])}
        layers = sorted(o_layers, key=lambda lyr: order[lyr["id"]]) + layers
        sources.append(hls)

    method = (
        f"{maturity_note}, {proc['drop_threshold_db']:g} dB HV drop from forest, "
        f"{proc['mmu_ha']:g} ha minimum patch."
    )
    stats = {
        real["area_key"]: stat(
            an.stats["area_ha"], "ha", 0, real["area_label"], f"Area of the loss mask. {method}"
        ),
        "hv_drop_db": stat(
            an.stats["hv_drop_db"],
            "dB",
            1,
            "HV drop inside the mask",
            "Mean HV of the before composite minus the after composite inside the mask.",
        ),
        "hv_before_db": stat(
            an.stats["hv_before_db"], "dB", 1, "HV before", "Median composite of the before window."
        ),
        "hv_after_db": stat(
            an.stats["hv_after_db"], "dB", 1, "HV after", "Median composite of the after window."
        ),
        "n_dates": stat(an.stats["n_dates"], "count", 0, "Radar dates", "Acquisition dates in the series."),
    }
    for key, value in extras.items():
        if key.endswith("_blocked_pct"):
            stats["smoke_cloud_pct"] = stat(
                value,
                "%",
                0,
                "Optical scene blocked by smoke or cloud",
                "Share of pixels Fmask flags as cloud, cloud edge, shadow or snow.",
            )
    if real["series_kind"] == "area":
        series = {
            "id": real["series_id"],
            "label": real["series_label"],
            "unit": "ha",
            "kind": "affected-area",
            "points": points(an.area_series),
            "sourceIds": ["nisar-gcov"],
            "status": "real",
        }
    else:
        series = {
            "id": real["series_id"],
            "label": real["series_label"],
            "unit": "dB",
            "kind": "hv-backscatter",
            "points": points(an.series),
            "sourceIds": ["nisar-gcov"],
            "status": "real",
        }
        if an.reference_series:
            series["reference"] = {"label": real["reference_label"], "points": points(an.reference_series)}
    manifest["generated"] = {
        "pipelineVersion": f"{__version__}+nisar",
        "builtAt": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "layers": layers,
        "series": [series],
        "stats": stats,
        "flyover": flyover_from_config(cfg),
        "annotations": annotations(cfg["annotations"], stack, an),
        "sources": sources,
    }
    footprint = mask_footprint(
        an.mask, stack, an.stats["area_ha"], real.get("footprint_label", real["area_label"])
    )
    if footprint:
        manifest["generated"]["footprint"] = footprint
    return write_manifest(slug, manifest, chapters_dir)
