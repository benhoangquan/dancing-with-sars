"""Read a study-area window of a NISAR L2 GOFF granule (pixel offsets) and turn it into ground speed.

Layout, checked against a real granule on 2026-11-14: `/science/LSAR/GOFF/grids/frequencyA/pixelOffsets/HH`
has `layer1`, `layer2` and `layer3` (offset tracking at three scales), each with `alongTrackOffset` and
`slantRangeOffset` in metres, `snr`, and coordinates on an 80 m polar-stereographic grid (EPSG 3413 for
Greenland). `layer1` and `layer2` carry the full glacier displacement; `layer3` is a coarse, smoothed version
that underestimates fast flow. The incidence angle sits in `metadata/radarGrid/incidenceAngle`, a cube on a
coarser grid over 20 heights above the ellipsoid.

Between two dates the ice moved by (along-track, ground-range) metres. Ground range is the slant-range offset
divided by the sine of the incidence angle, which assumes the motion is horizontal.
"""

from __future__ import annotations

from dataclasses import dataclass

import h5py
import numpy as np
from affine import Affine
from rasterio.warp import transform_bounds

from .gunw import window_native
from .hdf5 import Fetch, read_window

GRID = "science/LSAR/GOFF/grids/frequencyA/pixelOffsets/HH"
RADAR_GRID = "science/LSAR/GOFF/metadata/radarGrid"
DEFAULT_LAYER = 1
MIN_SNR = 6.0
ICE_HEIGHT_M = 500.0  # the incidence cube is cut at this height above the ellipsoid


@dataclass
class OffsetPair:
    """Displacement between two dates over the study area, native grid, row 0 at the north edge."""

    along_m: np.ndarray  # metres along the satellite track, NaN where unusable
    range_m: np.ndarray  # metres in slant range, NaN where unusable
    snr: np.ndarray
    x0: float  # west edge, projected metres
    y0: float  # north edge
    res: float
    epsg: int
    incidence_deg: float

    @property
    def transform(self) -> Affine:
        return Affine(self.res, 0, self.x0, 0, -self.res, self.y0)


def horizontal_offset_m(along_m: np.ndarray, range_m: np.ndarray, incidence_deg: float) -> np.ndarray:
    """Length in metres of the horizontal displacement, from the along-track and slant-range offsets."""
    ground_range = range_m / np.sin(np.radians(incidence_deg))
    return np.hypot(along_m, ground_range).astype(np.float32)


def speed_m_per_day(offset_m: np.ndarray, days: float) -> np.ndarray:
    return (offset_m / days).astype(np.float32)


def _incidence(h5: h5py.File, utm: tuple[float, float, float, float]) -> float:
    """Median incidence angle over the window, at the cube height closest to `ICE_HEIGHT_M`."""
    rg = h5[RADAR_GRID]
    heights = rg["heightAboveEllipsoid"][:]
    k = int(np.argmin(np.abs(heights - ICE_HEIGHT_M)))
    xs, ys = rg["xCoordinates"][:], rg["yCoordinates"][:]
    idx = window_native(xs, ys, float(xs[1] - xs[0]), float(ys[1] - ys[0]), utm)
    cube = rg["incidenceAngle"]
    if idx is None:
        return float(np.nanmedian(cube[k]))
    r0, r1, c0, c1 = idx
    return float(np.nanmedian(cube[k, r0:r1, c0:c1]))


def read_offsets(
    h5: h5py.File,
    bbox: tuple[float, float, float, float],
    fetch: Fetch,
    *,
    layer: int = DEFAULT_LAYER,
    threads: int = 8,
    min_snr: float = MIN_SNR,
) -> OffsetPair | None:
    """Offsets over `bbox` (lon/lat). Samples with a low signal-to-noise ratio become NaN. None if the
    granule does not reach the study area."""
    g = h5[f"{GRID}/layer{layer}"]
    epsg = int(g["projection"][()])
    dx, dy = float(g["xCoordinateSpacing"][()]), float(g["yCoordinateSpacing"][()])
    xs, ys = g["xCoordinates"][:], g["yCoordinates"][:]
    utm = transform_bounds("EPSG:4326", f"EPSG:{epsg}", *bbox)
    idx = window_native(xs, ys, dx, dy, utm)
    if idx is None:
        return None
    r0, r1, c0, c1 = idx
    along = read_window(g["alongTrackOffset"], r0, r1, c0, c1, fetch, threads=threads)
    rng = read_window(g["slantRangeOffset"], r0, r1, c0, c1, fetch, threads=threads)
    snr = read_window(g["snr"], r0, r1, c0, c1, fetch, threads=threads)
    bad = ~np.isfinite(along) | ~np.isfinite(rng) | ~(snr >= min_snr)
    along[bad] = np.nan
    rng[bad] = np.nan
    return OffsetPair(
        along, rng, snr, float(xs[c0] - dx / 2), float(ys[r0] - dy / 2), abs(dx), epsg, _incidence(h5, utm)
    )
