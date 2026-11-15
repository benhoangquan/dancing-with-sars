"""`sar globe`: NASA Blue Marble tiles for the hero and hotspot globe, saved once as static files.

Tiles come from NASA GIBS (Blue Marble Next Generation, public domain) on the GoogleMapsCompatible grid
and are re-encoded as WebP under `web/public/globe/{z}/{x}/{y}.webp`, so the site needs no tile server at
runtime.
"""

from __future__ import annotations

import io
import time
import urllib.request
from pathlib import Path

from PIL import Image

from .config import DATA_DIR

GIBS = (
    "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_NextGeneration/default/"
    "GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg"
)
GLOBE_DIR = DATA_DIR.parent / "globe"
MAX_ZOOM = 4
CREDIT = "NASA Earth Observatory Blue Marble Next Generation, via NASA GIBS"


def tile_keys(max_zoom: int = MAX_ZOOM) -> list[tuple[int, int, int]]:
    return [(z, x, y) for z in range(max_zoom + 1) for x in range(2**z) for y in range(2**z)]


def fetch(url: str, tries: int = 4) -> bytes:
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:  # noqa: S310 (fixed https host)
                return r.read()
        except OSError:
            if attempt == tries - 1:
                raise
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


def build_globe(out: Path = GLOBE_DIR, max_zoom: int = MAX_ZOOM, get=fetch, log=print) -> int:
    written = 0
    for z, x, y in tile_keys(max_zoom):
        path = out / str(z) / str(x) / f"{y}.webp"
        if path.exists():
            continue
        img = Image.open(io.BytesIO(get(GIBS.format(z=z, x=x, y=y)))).convert("RGB")
        path.parent.mkdir(parents=True, exist_ok=True)
        img.save(path, "WEBP", quality=80, method=6)
        written += 1
    size_mb = sum(p.stat().st_size for p in out.rglob("*.webp")) / 1e6
    log(f"  {written} tiles written, z0 to z{max_zoom}, {size_mb:.1f} MB")
    return written
