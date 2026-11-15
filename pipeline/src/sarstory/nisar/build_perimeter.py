"""`sar build` for chapters measured inside a mapped fire perimeter (config `[perimeter]`).

Radar layers come from the cached GCOV stack; the perimeter comes from BC Wildfire Service open data (cached
after the first download); optical layers come from HLS on Planetary Computer unless `optical` is False or
"reuse". The perimeter is a labeled real fallback: it is not a NISAR measurement, the HV drop inside it is.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
from rasterio.features import rasterize
from rasterio.warp import transform_geom
from shapely.geometry import mapping, shape

from .. import __version__
from ..cog import write_layer
from ..composite import DEFAULT_STRETCH, sar_composite
from ..config import CACHE_DIR, CHAPTERS_DIR, DATA_DIR, load_config
from ..fixture import flyover_from_config
from ..manifest import read_manifest, write_manifest
from ..optical import Lattice, build_layers
from .analysis import load_stack, median_db
from .build import nisar_source, points, span, stat
from .perimeter import analyze_perimeter

SIMPLIFY_DEG = 0.0001  # about 10 m
BCWS_LICENSE = "Open Government Licence - British Columbia"


def _wfigs_feature(per: dict) -> dict:
    """One feature from the US interagency WFIGS perimeters (ArcGIS), shaped like the BC one."""
    query = {
        "where": f"poly_IncidentName='{per['fire_name']}' AND poly_GISAcres>{per.get('min_acres', 50000)}",
        "outFields": "poly_IncidentName,poly_GISAcres,poly_PolygonDateTime,attr_FireDiscoveryDateTime",
        "outSR": "4326",
        "f": "geojson",
    }
    with urllib.request.urlopen(f"{per['url']}/query?{urllib.parse.urlencode(query)}", timeout=60) as r:  # noqa: S310
        features = json.load(r)["features"]
    if len(features) != 1:
        raise RuntimeError(f"expected one perimeter for {per['fire_name']}, got {len(features)}")
    f = features[0]
    props = f["properties"]
    f["properties"] = {
        "FIRE_SIZE_HECTARES": round(props["poly_GISAcres"] * 0.404686, 1),
        "TRACK_DATE": datetime.fromtimestamp(props["poly_PolygonDateTime"] / 1000, UTC).date().isoformat(),
    }
    return f


def fetch_perimeter(cfg: dict, cache_root: Path) -> dict:
    """The fire's perimeter feature as GeoJSON in lon/lat, downloaded once and cached."""
    per = cfg["perimeter"]
    key = per.get("fire_number") or per["fire_name"].lower().replace(" ", "-")
    path = cache_root / cfg["slug"] / f"perimeter_{key}.geojson"
    if not path.exists():
        if per.get("provider") == "wfigs":
            feature = _wfigs_feature(per)
        else:
            query = {
                "service": "WFS",
                "version": "2.0.0",
                "request": "GetFeature",
                "typeName": per["layer"],
                "outputFormat": "application/json",
                "srsName": "EPSG:4326",
                "CQL_FILTER": f"FIRE_NUMBER='{per['fire_number']}' AND FIRE_YEAR={per['started'][:4]}",
            }
            url = f"{per['wfs']}?{urllib.parse.urlencode(query)}"
            with urllib.request.urlopen(url, timeout=60) as r:  # noqa: S310 (fixed https host from config)
                features = json.load(r)["features"]
            if len(features) != 1:
                raise RuntimeError(f"expected one perimeter for {per['fire_number']}, got {len(features)}")
            feature = features[0]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(feature), encoding="utf-8")
    return json.loads(path.read_text(encoding="utf-8"))


def _rounded(geom: dict) -> dict:
    def r(c):
        return [round(c[0], 6), round(c[1], 6)] if isinstance(c[0], float | int) else [r(x) for x in c]

    return {"type": geom["type"], "coordinates": r(geom["coordinates"])}


def perimeter_source(cfg: dict, feature: dict) -> dict:
    p, per = feature["properties"], cfg["perimeter"]
    wfigs = per.get("provider") == "wfigs"
    return {
        "id": per.get("source_id", "wfigs" if wfigs else "bcws"),
        "mission": "US Interagency Fire (WFIGS)" if wfigs else "BC Wildfire Service",
        "product": f"Fire perimeter, {per['fire_name']} ({p['FIRE_SIZE_HECTARES']:,} ha)",
        "collection": "WFIGS Interagency Fire Perimeters" if wfigs else per["layer"].split(":", 1)[1],
        "maturity": "n/a",
        "granules": [per.get("fire_number", per["fire_name"])],
        "dates": [str(p["TRACK_DATE"])[:10]],
        "provider": "NIFC, US Interagency Fire Program"
        if wfigs
        else "BC Wildfire Service, Government of British Columbia",
        "license": "Public domain (US government data)" if wfigs else BCWS_LICENSE,
        "url": per["catalog_url"],
        "nasa": False,
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
    per, proc = cfg["perimeter"], cfg["processing"]
    manifest = read_manifest(slug, chapters_dir)
    index = json.loads((cache_root / slug / "acquisitions.json").read_text())
    stack = load_stack(slug, index, cache_root)
    feature = fetch_perimeter(cfg, cache_root)
    geom = transform_geom("EPSG:4326", f"EPSG:{stack.epsg}", feature["geometry"])
    h, w = stack.hv.shape[1:]
    inside = rasterize([(geom, 1)], out_shape=(h, w), transform=stack.transform, fill=0).astype(bool)
    with np.errstate(divide="ignore", invalid="ignore"):
        hv_db = (10 * np.log10(stack.hv)).astype(np.float32)
    an = analyze_perimeter(
        stack.days,
        hv_db,
        inside,
        started=date.fromisoformat(per["started"]),
        mapped=date.fromisoformat(per["mapped"]),
        min_before_db=proc["min_before_db"],
        pixel_area_m2=stack.res**2,
    )
    s = an.stats
    log(
        f"  HV fell {an.drop_db:.2f} dB inside {per['fire_name']} relative to the ring; placebo "
        f"{s['placebo_mean_db']:+.2f} +/- {s['placebo_sd_db']:.2f} dB (n={s['placebo_n']:.0f}, "
        f"{s['placebo_share_as_low']:.1%} as low)"
    )

    pre = [stack.days.index(d) for d in an.pre_days]
    post = [stack.days.index(d) for d in an.post_days]
    stretch = {k: tuple(proc.get(f"stretch_{k.lower()}", DEFAULT_STRETCH[k])) for k in DEFAULT_STRETCH}
    layers = []
    for layer_id, label, idx, days in (
        ("sar_before", "Radar composite, before the fire", pre, an.pre_days),
        ("sar_after", "Radar composite, after the fire", post, an.post_days),
    ):
        rgba = sar_composite(median_db(stack.hh[idx]), median_db(stack.hv[idx]), stretch)
        layers.append(
            write_layer(
                slug,
                layer_id,
                kind="sar-composite",
                label=label,
                date=span(days),
                data=rgba,
                transform=stack.transform,
                crs=f"EPSG:{stack.epsg}",
                render={"type": "rgba"},
                source_ids=["nisar-gcov"],
                status="real",
                stretch=stretch,
                data_dir=data_dir,
            )
        )

    sources = [nisar_source(index, stack), perimeter_source(cfg, feature)]
    extras: dict[str, float] = {}
    old = manifest.get("generated", {})
    if optical == "reuse":
        kept = [x for x in old.get("layers", []) if x["kind"] == "optical" and x["status"] == "real"]
        hls = next((x for x in old.get("sources", []) if x["id"] == "hls"), None)
        if not kept or hls is None:
            raise RuntimeError(f"{slug}: no real optical layers to reuse; run a full build first")
        layers = kept + layers
        sources.append(hls)
        if "smoke_cloud_pct" in old.get("stats", {}):
            extras["optical_smoke_blocked_pct"] = old["stats"]["smoke_cloud_pct"]["value"]
    elif optical:
        o_layers, hls, extras = build_layers(
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

    bcws_ha = float(feature["properties"]["FIRE_SIZE_HECTARES"])
    method = (
        f"NISAR {index['collection']}. Median HV inside the {per['fire_name']} perimeter minus median HV of "
        "a ring of "
        f"forest {8 * stack.res / 1000:.1f} to {40 * stack.res / 1000:.1f} km outside it, averaged over the "
        f"{len(pre)} passes before {per['started']} and the {len(post)} passes after {per['mapped']}; "
        "the stat is "
        "the fall in that gap."
    )
    stats = {
        "burn_hv_drop_db": stat(
            an.drop_db, "dB", 1, "HV drop inside the perimeter, relative to the forest around it", method
        ),
        "placebo_sd_db": stat(
            s["placebo_sd_db"],
            "dB",
            1,
            "Spread of the same measure where nothing burned",
            f"Standard deviation over {s['placebo_n']:.0f} {an.placebo_kind} moved onto unburned "
            f"forest in the same scene; mean {s['placebo_mean_db']:+.2f} dB, "
            f"{s['placebo_share_as_low']:.1%} as low as the fire.",
        ),
        "burned_ha": stat(
            bcws_ha,
            "ha",
            0,
            "Area inside the mapped perimeter",
            f"{per.get('agency', 'BC Wildfire Service')} perimeter of {per['fire_name']}, "
            f"mapped {per['mapped']}. Not a NISAR measurement.",
        ),
        "n_dates": stat(s["n_dates"], "count", 0, "Radar dates", "NISAR acquisition dates in the series."),
    }
    if "optical_smoke_blocked_pct" in extras:
        stats["smoke_cloud_pct"] = stat(
            extras["optical_smoke_blocked_pct"],
            "%",
            0,
            "Optical scene blocked by smoke or cloud",
            "Share of pixels Fmask flags as cloud, cloud edge, shadow or snow on the day of the optical "
            "scene.",
        )
    series = {
        "id": "hv_burned",
        "label": "HV inside the fire perimeter",
        "unit": "dB",
        "kind": "hv-backscatter",
        "points": points(an.inside_series),
        "reference": {"label": "Forest around it", "points": points(an.ring_series)},
        "sourceIds": ["nisar-gcov"],
        "status": "real",
    }
    # A large perimeter has tens of thousands of vertices; the page queries terrain at each one every frame.
    tolerance = SIMPLIFY_DEG if bcws_ha < 5_000 else 0.0015 if bcws_ha < 50_000 else 0.004  # 10, 150 or 400 m
    simple = shape(feature["geometry"]).simplify(tolerance, preserve_topology=True)
    outline = max(simple.geoms, key=lambda g: g.area) if simple.geom_type == "MultiPolygon" else simple
    footprint = {
        "kind": "shape",
        "label": f"{per['fire_name']} fire perimeter",
        "areaHa": round(bcws_ha, 1),
        "geometry": _rounded(mapping(simple)),
        "sourceIds": [per.get("source_id", "wfigs" if per.get("provider") == "wfigs" else "bcws")],
        "status": "fallback",
    }
    annotations = [
        {
            "id": "fire_perimeter",
            "label": f"{per['fire_name']} fire, mapped perimeter",
            "kind": "area",
            "geometry": _rounded(mapping(outline)),
        }
    ]
    manifest["generated"] = {
        "pipelineVersion": f"{__version__}+nisar-perimeter",
        "builtAt": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "layers": layers,
        "series": [series],
        "stats": stats,
        "flyover": flyover_from_config(cfg),
        "annotations": annotations,
        "sources": sources,
        "footprint": footprint,
    }
    return write_manifest(slug, manifest, chapters_dir)
