"""The science of `sar build` for GOFF chapters, on arrays only: ice speed from sequential offset pairs.

Each pair gives the horizontal distance the surface moved between two dates, so dividing by the days between
them gives a speed. The median over all pairs is the typical speed, the first and last pairs show the change
over the season, and the speed at the fastest point over time is the series. Ground that is not moving gives
the noise floor.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np

from .goff import OffsetPair, horizontal_offset_m, speed_m_per_day
from .gunw_analysis import smooth_nan

FAST_ICE_M_PER_DAY = 10.0  # ice faster than this counts as fast-flowing
STABLE_M_PER_DAY = 1.0  # ground slower than this is treated as not moving, to measure the noise floor


@dataclass
class SpeedPair:
    reference: date
    secondary: date
    speed: np.ndarray  # metres per day, NaN where unusable

    @property
    def midpoint(self) -> date:
        return self.reference + timedelta(days=(self.secondary - self.reference).days // 2)


def to_speed(reference: date, secondary: date, offsets: OffsetPair) -> SpeedPair:
    """A pair's offsets as a speed map in metres per day."""
    days = (secondary - reference).days
    if days <= 0:
        raise ValueError(f"secondary {secondary} is not after reference {reference}")
    off = horizontal_offset_m(offsets.along_m, offsets.range_m, offsets.incidence_deg)
    return SpeedPair(reference, secondary, speed_m_per_day(off, days))


def _nanmedian(stack: list[np.ndarray]) -> np.ndarray:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        return np.nanmedian(np.stack(stack), axis=0).astype(np.float32)


@dataclass
class GoffAnalysis:
    median: np.ndarray
    early: np.ndarray
    late: np.ndarray
    hotspot: tuple[int, int]
    series: list[tuple[date, float]]
    reference_series: list[tuple[date, float]]
    stats: dict[str, float]


def analyze_goff(
    pairs: list[SpeedPair],
    *,
    pixel_area_m2: float,
    season_pairs: int = 3,
    fast_m_per_day: float = FAST_ICE_M_PER_DAY,
    stable_m_per_day: float = STABLE_M_PER_DAY,
) -> GoffAnalysis:
    """Typical speed, early and late maps, the fastest point and its history, and the noise floor."""
    if len(pairs) < 2:
        raise ValueError("need at least two offset pairs")
    shapes = {p.speed.shape for p in pairs}
    if len(shapes) != 1:
        raise ValueError(f"pairs are on different grids: {sorted(shapes)}")
    ordered = sorted(pairs, key=lambda p: p.reference)
    median = _nanmedian([p.speed for p in ordered])
    k = max(1, min(season_pairs, len(ordered) // 2))
    early, late = _nanmedian([p.speed for p in ordered[:k]]), _nanmedian([p.speed for p in ordered[-k:]])
    smooth = smooth_nan(median)
    if not np.isfinite(smooth).any():
        raise ValueError("no pixel has a usable speed")
    r, c = np.unravel_index(np.nanargmax(smooth), smooth.shape)
    window = (slice(max(r - 1, 0), r + 2), slice(max(c - 1, 0), c + 2))
    stable = np.isfinite(smooth) & (smooth < stable_m_per_day)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        series = [(p.midpoint, float(np.nanmean(p.speed[window]))) for p in ordered]
        ref = [(p.midpoint, float(np.nanmean(p.speed[stable]))) for p in ordered] if stable.any() else []
    series = [(d, v) for d, v in series if np.isfinite(v)]
    ref = [(d, v) for d, v in ref if np.isfinite(v)]
    days = float(np.median([(p.secondary - p.reference).days for p in ordered]))
    peak = float(smooth[r, c])
    stats = {
        "peak_speed_m_day": peak,
        "peak_offset_m": peak * days,
        "fast_ice_ha": float(np.nansum(smooth > fast_m_per_day)) * pixel_area_m2 / 10_000.0,
        "noise_floor_m_day": float(np.median([v for _, v in ref])) if ref else float("nan"),
        "n_pairs": float(len(ordered)),
        "pair_days": days,
    }
    return GoffAnalysis(median, early, late, (int(r), int(c)), series, ref if len(ref) >= 2 else [], stats)
