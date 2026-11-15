"""True-color optical layers from Harmonized Landsat Sentinel-2 (HLS, 30 m) via Microsoft Planetary Computer.

No login is needed. Each scene is read on the same UTM lattice as the radar (60 m cells, using the 60 m
overview of the COG so little data moves), cloud-masked with Fmask, and combined with a median.
"""

from __future__ import annotations

import warnings
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import numpy as np
from affine import Affine

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
COLLECTIONS = ["hls2-s30", "hls2-l30"]
RGB_BANDS = ("B04", "B03", "B02")  # red, green, blue in both Sentinel-2 and Landsat products
NODATA = -9999
SCALE = 1e-4
# Fmask bits: 1 cloud, 2 adjacent to cloud or shadow, 3 cloud shadow, 4 snow or ice.
BAD_BITS = 0b00011110
WHITE_POINT = 0.25  # reflectance that maps to full brightness
GAMMA = 0.6


@dataclass(frozen=True)
class Lattice:
    """The grid every layer of a chapter shares: UTM, row 0 at the north edge."""

    transform: Affine
    width: int
    height: int
    epsg: int

    @property
    def crs(self) -> str:
        return f"EPSG:{self.epsg}"


def clear_mask(fmask: np.ndarray) -> np.ndarray:
    """True where the pixel is usable: no cloud, cloud edge, shadow or snow."""
    return (fmask.astype(np.uint8) & BAD_BITS) == 0


def blocked_share(fmask: np.ndarray, valid: np.ndarray | None = None) -> float:
    """Share of the pixels with data that Fmask flags as cloud, cloud edge, shadow or snow."""
    has_data = np.ones(fmask.shape, bool) if valid is None else valid
    n = int(has_data.sum())
    return float((~clear_mask(fmask) & has_data).sum() / n) if n else float("nan")


def to_reflectance(raw: np.ndarray) -> np.ndarray:
    """HLS integers to reflectance (0 to about 1); the nodata value becomes NaN."""
    out = raw.astype(np.float32) * SCALE
    out[raw == NODATA] = np.nan
    return out


def median_composite(scenes: list[np.ndarray]) -> np.ndarray:
    """Per-pixel median of (3, H, W) reflectance scenes, ignoring NaN. NaN where no scene has data."""
    stack = np.stack(scenes)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        return np.nanmedian(stack, axis=0).astype(np.float32)


def stretch_rgba(rgb: np.ndarray) -> np.ndarray:
    """(3, H, W) reflectance to (4, H, W) uint8 RGBA with one fixed stretch, so scenes stay comparable.
    Alpha is 0 where any band is NaN."""
    valid = np.isfinite(rgb).all(axis=0)
    x = np.clip(np.nan_to_num(rgb) / WHITE_POINT, 0.0, 1.0) ** GAMMA
    out = np.zeros((4, *rgb.shape[1:]), np.uint8)
    out[:3] = np.where(valid, np.rint(x * 255.0), 0).astype(np.uint8)
    out[3] = np.where(valid, 255, 0).astype(np.uint8)
    return out


def _signed_client():
    import planetary_computer
    import pystac_client

    return pystac_client.Client.open(STAC, modifier=planetary_computer.sign_inplace)


def search_items(bbox, window: tuple[str, str], max_cloud: float = 70.0, limit: int = 40) -> list:
    """HLS items over `bbox` in the date window, least cloudy first."""
    client = _signed_client()
    found = client.search(
        collections=COLLECTIONS,
        bbox=list(bbox),
        datetime=f"{window[0]}/{window[1]}",
        query={"eo:cloud_cover": {"lt": max_cloud}},
    ).item_collection()
    return sorted(found, key=lambda i: i.properties.get("eo:cloud_cover", 100.0))[:limit]


def read_scene(item, lat: Lattice, *, mask_clouds: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """One scene on the lattice: (3, H, W) reflectance with NaN where there is no data or (optionally) cloud,
    and the (H, W) Fmask (255 where the scene has no data)."""
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.vrt import WarpedVRT

    env = {
        "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
        "GDAL_HTTP_MAX_RETRY": "4",
        "GDAL_HTTP_RETRY_DELAY": "2",
    }

    def warp(href: str, resampling: Resampling, dtype: str, nodata: float) -> np.ndarray:
        with rasterio.Env(**env), rasterio.open(href, overview_level=0) as src:
            with WarpedVRT(
                src,
                crs=lat.crs,
                transform=lat.transform,
                width=lat.width,
                height=lat.height,
                resampling=resampling,
                src_nodata=nodata,
                nodata=nodata,
                dtype=dtype,
            ) as vrt:
                return vrt.read(1)

    fmask = warp(item.assets["Fmask"].href, Resampling.nearest, "uint8", 255)
    bands = [
        to_reflectance(warp(item.assets[b].href, Resampling.average, "int16", NODATA)) for b in RGB_BANDS
    ]
    rgb = np.stack(bands)
    if mask_clouds:
        rgb[:, ~clear_mask(fmask)] = np.nan
    rgb[:, fmask == 255] = np.nan
    return rgb, fmask


def read_scenes(items: list, lat: Lattice, *, mask_clouds: bool = True, threads: int = 4):
    with ThreadPoolExecutor(threads) as pool:
        return list(pool.map(lambda i: read_scene(i, lat, mask_clouds=mask_clouds), items))


def hls_source(items: list) -> dict:
    """The manifest `Source` entry for the HLS scenes that were used."""
    return {
        "id": "hls",
        "mission": "HLS",
        "product": "Harmonized Landsat Sentinel-2 v2.0 (30 m)",
        "collection": "HLSS30, HLSL30",
        "maturity": "validated",
        "granules": sorted({i.id for i in items})[:80],
        "dates": sorted({i.datetime.date().isoformat() for i in items}),
        "provider": "NASA and USGS, through Microsoft Planetary Computer",
        "license": "Open and free to use under NASA's Earth science data policy",
        "url": "https://www.earthdata.nasa.gov/data/projects/hls",
        "nasa": True,
    }


def build_layers(
    slug: str, specs: list[dict], bbox, lat: Lattice, data_dir, log=print
) -> tuple[list, dict, dict]:
    """Write one optical layer per spec. Returns (layer entries, the HLS Source, extra stats by name).

    Spec modes: `median` (a window, clouds masked, per-pixel median) or `scene` (one date, nothing masked, so
    smoke stays in the picture; the share Fmask flags is returned as `<id>_blocked_pct`).
    """
    from .cog import write_layer

    layers, used, extras = [], [], {}
    for spec in specs:
        scene_mode = spec.get("mode", "median") == "scene"
        window = (spec["date"], spec["date"]) if scene_mode else tuple(spec["window"])
        items = search_items(
            bbox,
            window,
            max_cloud=100 if scene_mode else spec.get("max_cloud", 60),
            limit=spec.get("limit", 24),
        )
        if not items:
            raise RuntimeError(f"{spec['id']}: no HLS scene in {window}")
        log(f"  {spec['id']}: {len(items)} HLS scenes in {window[0]} to {window[1]}")
        scenes = read_scenes(items, lat, mask_clouds=not scene_mode)
        rgba = stretch_rgba(median_composite([rgb for rgb, _ in scenes]))
        if scene_mode:
            fmask = np.full((lat.height, lat.width), 255, np.uint8)
            for _, f in scenes:
                np.copyto(fmask, f, where=fmask == 255)
            extras[f"{spec['id']}_blocked_pct"] = 100.0 * blocked_share(fmask, fmask != 255)
        days = sorted({i.datetime.date().isoformat() for i in items})
        layers.append(
            write_layer(
                slug,
                spec["id"],
                kind="optical",
                label=spec["label"],
                date=days[0] if len(days) == 1 else f"{days[0]}/{days[-1]}",
                data=rgba,
                transform=lat.transform,
                crs=lat.crs,
                render={"type": "rgba"},
                source_ids=["hls"],
                status="real",
                data_dir=data_dir,
            )
        )
        used += items
    return layers, hls_source(used), extras
