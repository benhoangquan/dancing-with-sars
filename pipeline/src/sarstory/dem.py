"""`sar dem`: Copernicus GLO-30 terrain for a chapter, as a static COG read with `cog://...#dem`.

The map and the captured flyover both use this file, so the site needs no terrain tile server. The study area
is padded so cameras looking toward the horizon still see terrain; outside the file the map is flat.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .cog import COG_OPTIONS, sha256_file
from .config import CHAPTERS_DIR, DATA_DIR
from .manifest import read_manifest, write_manifest

COLLECTION = "cop-dem-glo-30"
PAD = 0.35  # share of the bbox size added on every side
MAX_PX = 1600  # longest side; keeps each terrain file to a few MB
SOURCE = {
    "id": "copernicus-dem",
    "mission": "Copernicus DEM",
    "product": "Copernicus DEM GLO-30 (30 m), resampled to 1,600 px on the longest side",
    "collection": COLLECTION,
    "maturity": "n/a",
    "granules": [],
    "dates": [],
    "provider": "European Space Agency and Airbus, via Microsoft Planetary Computer",
    "license": (
        "Copernicus DEM licence: free use with attribution. Produced using Copernicus WorldDEM-30 "
        "(c) DLR e.V. 2010-2014 and (c) Airbus Defence and Space GmbH 2014-2018, provided under COPERNICUS "
        "by the European Union and ESA"
    ),
    "url": "https://planetarycomputer.microsoft.com/dataset/cop-dem-glo-30",
    "nasa": False,
}


def padded(bbox: list[float], pad: float = PAD) -> tuple[float, float, float, float]:
    w, s, e, n = bbox
    dx, dy = (e - w) * pad, (n - s) * pad
    return max(w - dx, -180.0), max(s - dy, -85.0), min(e + dx, 180.0), min(n + dy, 85.0)


def read_dem(bounds: tuple[float, float, float, float]) -> tuple[np.ndarray, object, list[str]]:
    """Mosaic of every GLO-30 tile over `bounds`, on a lon/lat grid. Sea and gaps are 0 m."""
    import planetary_computer
    import pystac_client
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.merge import merge

    client = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1", modifier=planetary_computer.sign_inplace
    )
    res = max(bounds[2] - bounds[0], bounds[3] - bounds[1]) / MAX_PX
    items = list(client.search(collections=[COLLECTION], bbox=list(bounds)).items())
    if not items:
        raise RuntimeError(f"no {COLLECTION} tiles over {bounds}")
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
        sources = [rasterio.open(i.assets["data"].href) for i in items]
        try:
            data, transform = merge(
                sources, bounds=bounds, res=(res, res), resampling=Resampling.bilinear, nodata=np.nan
            )
        finally:
            for s in sources:
                s.close()
    dem = np.nan_to_num(data[0].astype(np.float32), nan=0.0)
    return np.round(dem).astype(np.int16), transform, sorted(i.id for i in items)


def write_dem_cog(dst: Path, dem: np.ndarray, transform) -> None:
    """Whole metres as int16 on the GoogleMapsCompatible grid, at the zoom level just finer than the data
    (int16 and no upsampling keep the file small)."""
    import rasterio
    import rasterio.shutil
    from rasterio.io import MemoryFile

    profile = {"driver": "GTiff", "count": 1, "height": dem.shape[0], "width": dem.shape[1], "dtype": "int16"}
    dst.parent.mkdir(parents=True, exist_ok=True)
    with MemoryFile() as mem:
        with mem.open(**profile, crs="EPSG:4326", transform=transform) as ds:
            ds.write(dem[None])
        with mem.open() as ds:
            opts = {**COG_OPTIONS, "PREDICTOR": "2", "ZOOM_LEVEL_STRATEGY": "UPPER"}
            rasterio.shutil.copy(ds, str(dst), **opts)


def build_dem(slug: str, *, data_dir: Path = DATA_DIR, chapters_dir: Path = CHAPTERS_DIR, log=print) -> Path:
    manifest = read_manifest(slug, chapters_dir)
    bounds = padded(manifest["aoi"]["bbox"])
    dem, transform, tiles = read_dem(bounds)
    log(
        f"  {len(tiles)} GLO-30 tiles, {dem.shape[1]} x {dem.shape[0]} px, "
        f"{dem.min():.0f} to {dem.max():.0f} m"
    )
    path = data_dir / slug / "dem.tif"
    write_dem_cog(path, dem, transform)
    rel = path.relative_to(data_dir.parent).as_posix()
    manifest["generated"]["dem"] = {
        "cog": rel,
        "bounds": [round(b, 6) for b in bounds],
        "sourceIds": [SOURCE["id"]],
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }
    sources = [s for s in manifest["generated"]["sources"] if s["id"] != SOURCE["id"]]
    manifest["generated"]["sources"] = [*sources, {**SOURCE, "granules": tiles}]
    return write_manifest(slug, manifest, chapters_dir)
