"""Read a study-area window of a NISAR L2 GUNW granule (unwrapped interferogram, HH) and turn it into motion.

Layout, checked against a real granule on 2026-11-14: `/science/LSAR/GUNW/grids/frequencyA` holds
`unwrappedInterferogram/HH/{unwrappedPhase, coherenceMagnitude, connectedComponents}` on an 80 m UTM grid
with 1-D pixel-center `xCoordinates` and `yCoordinates`, and `centerFrequency` (Hz) one level up.

Sign: the phase of reference times the conjugate of secondary is 4 pi (R_secondary - R_reference) over the
wavelength, so a positive phase means the ground moved away from the satellite. Motion toward the satellite is
positive in `los_motion_cm`, so sinking ground (which lengthens the path) is negative.
"""

from __future__ import annotations

from dataclasses import dataclass

import h5py
import numpy as np
from affine import Affine
from rasterio.warp import transform_bounds

from .hdf5 import Fetch, read_window

FREQUENCY = "science/LSAR/GUNW/grids/frequencyA"
GRID = f"{FREQUENCY}/unwrappedInterferogram/HH"
LIGHT_M_S = 299_792_458.0
MIN_COHERENCE = 0.3


@dataclass
class Pair:
    """One interferogram over the study area, native grid, row 0 at the north edge."""

    phase: np.ndarray  # radians, NaN where unusable
    coherence: np.ndarray
    ionosphere: np.ndarray  # radians, the product's ionospheric phase screen (NaN where absent)
    components: np.ndarray  # connected-component labels from unwrapping; 0 is unusable
    x0: float  # west edge, UTM metres
    y0: float  # north edge
    res: float
    epsg: int
    wavelength_m: float

    @property
    def transform(self) -> Affine:
        return Affine(self.res, 0, self.x0, 0, -self.res, self.y0)


def wavelength_m(center_frequency_hz: float) -> float:
    return LIGHT_M_S / center_frequency_hz


def los_motion_cm(phase: np.ndarray, wavelength: float) -> np.ndarray:
    """Line-of-sight motion in centimetres from unwrapped phase; negative is away from the satellite."""
    return (-phase * wavelength / (4 * np.pi) * 100.0).astype(np.float32)


def window_native(xs, ys, dx: float, dy: float, utm: tuple[float, float, float, float]):
    """(row0, row1, col0, col1) of the cells whose centers fall inside `utm` (x0, y0, x1, y1), or None."""
    x0, y0, x1, y1 = utm
    cols = np.flatnonzero((xs >= x0) & (xs <= x1))
    rows = np.flatnonzero((ys >= y0) & (ys <= y1))
    if not cols.size or not rows.size:
        return None
    return int(rows[0]), int(rows[-1]) + 1, int(cols[0]), int(cols[-1]) + 1


def read_pair(
    h5: h5py.File,
    bbox: tuple[float, float, float, float],
    fetch: Fetch,
    *,
    threads: int = 8,
    min_coherence: float = MIN_COHERENCE,
) -> Pair | None:
    """Unwrapped phase and coherence over `bbox` (lon/lat). Samples with no unwrapped component or low
    coherence become NaN. None if the granule does not reach the study area."""
    g = h5[GRID]
    epsg = int(g["projection"][()])
    dx, dy = float(g["xCoordinateSpacing"][()]), float(g["yCoordinateSpacing"][()])
    xs, ys = g["xCoordinates"][:], g["yCoordinates"][:]
    idx = window_native(xs, ys, dx, dy, transform_bounds("EPSG:4326", f"EPSG:{epsg}", *bbox))
    if idx is None:
        return None
    r0, r1, c0, c1 = idx
    phase = read_window(g["unwrappedPhase"], r0, r1, c0, c1, fetch, threads=threads)
    coh = read_window(g["coherenceMagnitude"], r0, r1, c0, c1, fetch, threads=threads)
    comp = read_window(g["connectedComponents"], r0, r1, c0, c1, fetch, threads=threads)
    iono = read_window(g["ionospherePhaseScreen"], r0, r1, c0, c1, fetch, threads=threads)
    bad = (comp == 0) | ~np.isfinite(phase) | ~(coh >= min_coherence)
    phase[bad] = np.nan
    comp = np.where(bad, 0, comp).astype(np.uint16)
    wl = wavelength_m(float(h5[f"{FREQUENCY}/centerFrequency"][()]))
    return Pair(
        phase.astype(np.float32),
        coh,
        iono.astype(np.float32),
        comp,
        float(xs[c0] - dx / 2),
        float(ys[r0] - dy / 2),
        abs(dx),
        epsg,
        wl,
    )
