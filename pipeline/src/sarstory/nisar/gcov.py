"""Read a study-area window of a NISAR L2 GCOV granule (HDF5, UTM grid) as block-averaged linear power.

Layout, checked against a real granule on 2026-11-14: `/science/LSAR/GCOV/grids/frequencyA` holds float32
`HHHH` and `HVHV` (linear gamma-0 power, NaN fill), a `mask` (0 invalid, 255 outside the acquisition), 1-D
pixel-center `xCoordinates` and `yCoordinates`, `xCoordinateSpacing` and `yCoordinateSpacing` in metres, and
`projection` with the EPSG code (UTM).

Windows sit on a global lattice of `block_m` metre cells (multiples of `block_m` in UTM metres). Frames of one
pass and different dates therefore line up exactly and can be mosaicked or stacked without resampling.
"""

from __future__ import annotations

from dataclasses import dataclass

import h5py
import numpy as np
from affine import Affine
from rasterio.warp import transform_bounds

from .hdf5 import Fetch, read_window

GRID = "science/LSAR/GCOV/grids/frequencyA"
MIN_VALID_SHARE = 0.5  # a block needs this share of valid samples


@dataclass
class Tile:
    """Block-averaged linear power on the lattice. Row 0 is the north edge."""

    hh: np.ndarray
    hv: np.ndarray
    x0: float  # west edge, UTM metres
    y0: float  # north edge, UTM metres
    res: float  # block size, metres
    epsg: int

    @property
    def transform(self) -> Affine:
        return Affine(self.res, 0, self.x0, 0, -self.res, self.y0)


def block_mean(a: np.ndarray, k: int, min_share: float = MIN_VALID_SHARE) -> np.ndarray:
    """Mean of each k x k block ignoring NaN; NaN where fewer than `min_share` of the block is valid."""
    h, w = a.shape[0] // k, a.shape[1] // k
    blocks = a[: h * k, : w * k].reshape(h, k, w, k)
    ok = np.isfinite(blocks)
    n = ok.sum(axis=(1, 3))
    total = np.where(ok, blocks, 0.0).sum(axis=(1, 3), dtype=np.float64)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = total / n
    out[n < min_share * k * k] = np.nan
    return out.astype(np.float32)


def _aligned(edge: float, block_m: float) -> bool:
    return abs(edge / block_m - round(edge / block_m)) < 1e-6


def window_indices(
    xs: np.ndarray,
    ys: np.ndarray,
    dx: float,
    dy: float,
    utm: tuple[float, float, float, float],
    block_m: float,
) -> tuple[int, int, int, int] | None:
    """(row0, row1, col0, col1) of the lattice-aligned window covering `utm` (x0, y0, x1, y1), or None if the
    granule does not reach it. Edges of the first and last cells sit on multiples of `block_m`."""
    k = round(block_m / abs(dx))
    x0, y0, x1, y1 = utm
    west = xs - dx / 2  # west edge of each column, increasing
    north = ys - dy / 2  # north edge of each row, decreasing (dy < 0)
    lo_x, hi_x = np.floor(x0 / block_m) * block_m, np.ceil(x1 / block_m) * block_m
    lo_y, hi_y = np.floor(y0 / block_m) * block_m, np.ceil(y1 / block_m) * block_m
    cols = np.flatnonzero((west >= lo_x - 1e-6) & (west + abs(dx) <= hi_x + 1e-6))
    rows = np.flatnonzero((north <= hi_y + 1e-6) & (north - abs(dy) >= lo_y - 1e-6))
    if cols.size < k or rows.size < k:
        return None
    c0, c1, r0, r1 = int(cols[0]), int(cols[-1]) + 1, int(rows[0]), int(rows[-1]) + 1
    while c0 < c1 and not _aligned(west[c0], block_m):
        c0 += 1
    while r0 < r1 and not _aligned(north[r0], block_m):
        r0 += 1
    c1, r1 = c0 + (c1 - c0) // k * k, r0 + (r1 - r0) // k * k
    return (r0, r1, c0, c1) if c1 > c0 and r1 > r0 else None


def read_tile(
    h5: h5py.File,
    bbox: tuple[float, float, float, float],
    fetch: Fetch,
    *,
    block_m: float = 60.0,
    threads: int = 16,
) -> Tile | None:
    """HH and HV over `bbox` (lon/lat) as linear power in `block_m` cells; None if there is no overlap."""
    fa = h5[GRID]
    epsg = int(fa["projection"][()])
    dx, dy = float(fa["xCoordinateSpacing"][()]), float(fa["yCoordinateSpacing"][()])
    xs, ys = fa["xCoordinates"][:], fa["yCoordinates"][:]
    utm = transform_bounds("EPSG:4326", f"EPSG:{epsg}", *bbox)
    idx = window_indices(xs, ys, dx, dy, utm, block_m)
    if idx is None:
        return None
    r0, r1, c0, c1 = idx
    mask = read_window(fa["mask"], r0, r1, c0, c1, fetch, threads=threads)
    valid = (mask > 0) & (mask < 255)
    k = round(block_m / abs(dx))
    out = []
    for name in ("HHHH", "HVHV"):
        a = read_window(fa[name], r0, r1, c0, c1, fetch, threads=threads)
        a[~valid | ~np.isfinite(a) | (a <= 0)] = np.nan
        out.append(block_mean(a, k))
    return Tile(out[0], out[1], float(xs[c0] - dx / 2), float(ys[r0] - dy / 2), block_m, epsg)
