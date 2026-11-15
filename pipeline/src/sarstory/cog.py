"""Cloud-Optimized GeoTIFF writer for web layers.

The browser reads layers through `@geomatico/maplibre-cog-protocol`, which accepts only EPSG:3857
files. `write_cog` takes an array in any CRS and lets GDAL's COG driver reproject it onto the
GoogleMapsCompatible grid with 256 px blocks and overviews.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import rasterio
import rasterio.shutil
from PIL import Image
from rasterio.enums import ColorInterp, Resampling
from rasterio.io import MemoryFile
from rasterio.warp import transform_bounds

from .config import DATA_DIR
from .palettes import ramp_rgba

PREVIEW_MAX_PX = 1024
COG_OPTIONS = {
    "driver": "COG",
    "TILING_SCHEME": "GoogleMapsCompatible",
    "COMPRESS": "DEFLATE",
    "OVERVIEWS": "AUTO",
    "ALIGNED_LEVELS": "2",
    "RESAMPLING": "BILINEAR",
    "NUM_THREADS": "ALL_CPUS",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_cog(dst: Path, data: np.ndarray, transform, crs) -> None:
    """Write `data` as a web COG: (4, H, W) uint8 is RGBA, (H, W) float32 is a ramp layer (NaN is no data)."""
    rgba = data.ndim == 3
    if rgba and not (data.shape[0] == 4 and data.dtype == np.uint8):
        raise ValueError(f"RGBA data must be (4, H, W) uint8, got {data.shape} {data.dtype}")
    if not rgba and data.dtype != np.float32:
        raise ValueError(f"ramp data must be float32, got {data.dtype}")
    bands = data if rgba else data[None]
    profile = {
        "driver": "GTiff",
        "count": bands.shape[0],
        "height": bands.shape[1],
        "width": bands.shape[2],
        "dtype": str(bands.dtype),
        "crs": crs,
        "transform": transform,
    }
    if not rgba:
        profile["nodata"] = float("nan")
    options = {**COG_OPTIONS, "PREDICTOR": "2" if rgba else "3"}
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with MemoryFile() as mem:
        with mem.open(**profile) as ds:
            ds.write(bands)
            if rgba:
                ds.colorinterp = (ColorInterp.red, ColorInterp.green, ColorInterp.blue, ColorInterp.alpha)
        with mem.open() as ds:
            rasterio.shutil.copy(ds, str(dst), **options)


JPEG_QUALITY = 88


def write_cog_jpeg(dst: Path, data: np.ndarray, transform, crs) -> None:
    """Imagery as a JPEG COG: (4, H, W) uint8 RGBA becomes RGB with the alpha kept as a mask band, which the
    browser reader applies as transparency. About a fifth the size of the lossless version."""
    if not (data.ndim == 3 and data.shape[0] == 4 and data.dtype == np.uint8):
        raise ValueError(f"RGBA data must be (4, H, W) uint8, got {data.shape} {data.dtype}")
    profile = {
        "driver": "GTiff",
        "count": 3,
        "height": data.shape[1],
        "width": data.shape[2],
        "dtype": "uint8",
        "crs": crs,
        "transform": transform,
    }
    options = {**COG_OPTIONS, "COMPRESS": "JPEG", "QUALITY": str(JPEG_QUALITY), "RESAMPLING": "AVERAGE"}
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK="YES"), MemoryFile() as mem:
        with mem.open(**profile) as ds:
            ds.write(data[:3])
            ds.write_mask(data[3] > 0)
        with mem.open() as ds:
            rasterio.shutil.copy(ds, str(dst), **options)


def cog_info(path: Path) -> dict:
    with rasterio.open(path) as ds:
        return {
            "crs": ds.crs.to_string(),
            "count": ds.count,
            "dtype": ds.dtypes[0],
            "width": ds.width,
            "height": ds.height,
            "block_shapes": ds.block_shapes,
            "overviews": ds.overviews(1),
            "bounds": tuple(ds.bounds),
            "bounds_lonlat": transform_bounds(ds.crs, "EPSG:4326", *ds.bounds),
            "colorinterp": [c.name for c in ds.colorinterp],
            "nodata": ds.nodata,
        }


def write_preview(cog: Path, out: Path, render: dict, max_px: int = PREVIEW_MAX_PX) -> None:
    """Image with the same extent as the COG (EPSG:3857), used as an image-source fallback and poster.
    A `.webp` path writes lossy WebP (alpha kept); anything else writes PNG."""
    with rasterio.open(cog) as ds:
        scale = min(1.0, max_px / max(ds.width, ds.height))
        h, w = max(1, round(ds.height * scale)), max(1, round(ds.width * scale))
        data = ds.read(out_shape=(ds.count, h, w), resampling=Resampling.bilinear)
        mask = ds.read_masks(1, out_shape=(h, w), resampling=Resampling.nearest) if ds.count == 3 else None
    if render["type"] == "rgba":
        arr = data if mask is None else np.concatenate([data, mask[None]])
    else:
        arr = ramp_rgba(data[0], render["scheme"], tuple(render["domain"]))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    img = Image.fromarray(np.moveaxis(arr, 0, -1), "RGBA")
    if out.suffix == ".webp":
        img.save(out, "WEBP", quality=80, method=6)
    else:
        img.save(out, optimize=True)


def write_layer(
    slug: str,
    layer_id: str,
    *,
    kind: str,
    label: str,
    date: str,
    data: np.ndarray,
    transform,
    crs,
    render: dict,
    source_ids: list[str],
    status: str,
    stretch: dict | None = None,
    data_dir: Path = DATA_DIR,
) -> dict:
    """Write `<slug>/<layer_id>.tif` and its preview under `data_dir`; return the schema `Layer` entry.
    Imagery (optical and radar composites) is stored as a JPEG COG with a mask and a WebP preview; layers
    that carry values or exact colors stay lossless."""
    out = data_dir / slug
    jpeg = kind in {"optical", "sar-composite"} and render["type"] == "rgba"
    cog, png = out / f"{layer_id}.tif", out / f"{layer_id}.{'webp' if jpeg else 'png'}"
    (write_cog_jpeg if jpeg else write_cog)(cog, data, transform, crs)
    write_preview(cog, png, render)
    info = cog_info(cog)
    rel = lambda p: p.relative_to(data_dir.parent).as_posix()  # noqa: E731
    entry = {
        "id": layer_id,
        "kind": kind,
        "label": label,
        "date": date,
        "cog": rel(cog),
        "render": render,
    }
    if stretch:
        entry["stretch"] = {k: list(v) for k, v in stretch.items()}
    entry.update(
        {
            "preview": rel(png),
            "bounds": [round(v, 6) for v in info["bounds_lonlat"]],
            "sourceIds": source_ids,
            "status": status,
            "bytes": cog.stat().st_size,
            "sha256": sha256_file(cog),
        }
    )
    return entry


def recompress_layers(slug: str, chapters_dir: Path, data_dir: Path = DATA_DIR) -> int:
    """Rewrite a chapter's lossless imagery layers as JPEG COGs with WebP previews, updating the manifest.
    Returns the bytes saved."""
    from .manifest import read_manifest, write_manifest

    manifest = read_manifest(slug, chapters_dir)
    saved = 0
    for layer in manifest["generated"]["layers"]:
        if layer["kind"] not in {"optical", "sar-composite"} or layer["render"]["type"] != "rgba":
            continue
        cog = data_dir.parent / layer["cog"]
        with rasterio.open(cog) as ds:
            if ds.compression and ds.compression.name == "jpeg":
                continue
            data, transform, crs = ds.read(), ds.transform, ds.crs
        before = cog.stat().st_size
        write_cog_jpeg(cog, data, transform, crs)
        preview = data_dir.parent / layer["preview"]
        webp = preview.with_suffix(".webp")
        write_preview(cog, webp, layer["render"])
        if preview != webp:
            preview.unlink(missing_ok=True)
        saved += before - cog.stat().st_size
        layer.update(
            {
                "preview": webp.relative_to(data_dir.parent).as_posix(),
                "bytes": cog.stat().st_size,
                "sha256": sha256_file(cog),
            }
        )
    write_manifest(slug, manifest, chapters_dir)
    return saved
