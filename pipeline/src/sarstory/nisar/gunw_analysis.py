"""The science of `sar build` for GUNW chapters, on arrays only: sum sequential interferograms into motion.

Each unwrapped phase has an arbitrary offset, so every pair is first referenced to a stable level. The pairs
are sequential (each reference date is the previous secondary date), so their line-of-sight motions add up to
the motion since the first reference date. Negative is away from the satellite, which is sinking for the
vertical motion that dominates here.
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from datetime import date

import numpy as np
from scipy import ndimage

SMOOTH_SIGMA_PX = 2.0
STABLE_CM = 0.5  # the reference series averages ground that moved less than this by the end
AREA_THRESHOLD_CM = 5.0


@dataclass
class PairMotion:
    reference: date
    secondary: date
    motion_cm: np.ndarray  # (H, W), NaN where unusable, positive toward the satellite
    coherence: np.ndarray


def reference_to_median(motion_cm: np.ndarray, box: tuple[slice, slice] | None = None) -> np.ndarray:
    """Subtract the median of a stable area (a box, or the whole scene if the moving area is a minority)."""
    patch = motion_cm if box is None else motion_cm[box]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        offset = np.nanmedian(patch)
    return motion_cm - (0.0 if not math.isfinite(offset) else offset)


def dominant_component(components: np.ndarray) -> np.ndarray:
    """True on the pixels of the largest nonzero label. Each unwrapped component carries its own arbitrary
    multiple of 2 pi, so mixing components makes steps of one fringe that look like motion."""
    labels = components[components > 0]
    if not labels.size:
        return np.zeros(components.shape, bool)
    values, counts = np.unique(labels, return_counts=True)
    return components == values[np.argmax(counts)]


def remove_plane(motion_cm: np.ndarray, iterations: int = 4, clip: float = 3.0) -> np.ndarray:
    """Subtract the best-fit plane (atmosphere and orbit leave long ramps), refitting without the pixels that
    stand out so a real bowl does not pull the plane toward itself. NaN stays NaN."""
    ok = np.isfinite(motion_cm)
    if ok.sum() < 100:
        return motion_cm
    yy, xx = np.mgrid[0 : motion_cm.shape[0], 0 : motion_cm.shape[1]]
    design = np.column_stack([np.ones(ok.sum()), xx[ok], yy[ok]])
    values, use = motion_cm[ok], np.ones(ok.sum(), bool)
    for _ in range(iterations):
        coef, *_ = np.linalg.lstsq(design[use], values[use], rcond=None)
        resid = values - design @ coef
        sigma = 1.4826 * np.median(np.abs(resid[use] - np.median(resid[use])))
        use = np.abs(resid - np.median(resid[use])) < clip * max(sigma, 1e-6)
        if use.sum() < 100:
            break
    plane = coef[0] + coef[1] * xx + coef[2] * yy
    return (motion_cm - plane).astype(np.float32)


def smooth_nan(a: np.ndarray, sigma: float = SMOOTH_SIGMA_PX) -> np.ndarray:
    """Gaussian smoothing that ignores NaN (normalized convolution); NaN where nothing valid is near."""
    ok = np.isfinite(a)
    num = ndimage.gaussian_filter(np.where(ok, a, 0.0), sigma)
    den = ndimage.gaussian_filter(ok.astype(float), sigma)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = num / den
    out[den < 0.25] = np.nan
    return out.astype(np.float32)


@dataclass
class GunwAnalysis:
    dates: list[date]  # first reference date, then each secondary date
    final_cm: np.ndarray  # cumulative motion at the last date, NaN where any pair was unusable
    coherence: np.ndarray  # mean coherence over the pairs
    hotspot: tuple[int, int]  # row, column of the deepest smoothed point
    hotspot_series: list[tuple[date, float]]
    reference_series: list[tuple[date, float]]
    stats: dict[str, float]


def analyze_gunw(
    pairs: list[PairMotion], *, pixel_area_m2: float, reference_box: tuple[slice, slice] | None = None
) -> GunwAnalysis:
    """Cumulative motion, its deepest point and the area past the threshold, from sequential pairs."""
    if not pairs:
        raise ValueError("no interferograms")
    for a, b in zip(pairs, pairs[1:], strict=False):
        if abs((b.reference - a.secondary).days) > 1:
            raise ValueError(f"pairs are not sequential: {a.secondary} then {b.reference}")
    referenced = [reference_to_median(p.motion_cm, reference_box) for p in pairs]
    cumulative = np.cumsum(np.stack(referenced), axis=0)  # NaN propagates: a pixel needs every pair so far
    final = cumulative[-1]
    smooth = smooth_nan(final)
    if not np.isfinite(smooth).any():
        raise ValueError("no pixel is usable in every interferogram")
    r, c = np.unravel_index(np.nanargmin(smooth), smooth.shape)
    window = (slice(max(r - 1, 0), r + 2), slice(max(c - 1, 0), c + 2))
    dates = [pairs[0].reference] + [p.secondary for p in pairs]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        series = [(dates[0], 0.0)] + [
            (d, float(np.nanmean(cum[window]))) for d, cum in zip(dates[1:], cumulative, strict=True)
        ]
        stable = np.isfinite(smooth) & (np.abs(smooth) < STABLE_CM)
        ref = [(dates[0], 0.0)] + (
            [(d, float(np.nanmean(cum[stable]))) for d, cum in zip(dates[1:], cumulative, strict=True)]
            if stable.any()
            else []
        )
    if len(ref) < 2:
        ref = []
    deepest = float(smooth[r, c])
    months = (dates[-1] - dates[0]).days / 30.44
    stats = {
        "max_subsidence_cm": -deepest,
        "area_over_5cm_ha": float(np.nansum(smooth < -AREA_THRESHOLD_CM)) * pixel_area_m2 / 10_000.0,
        "rate_cm_per_month": -deepest / months if months > 0 else float("nan"),
        "n_pairs": float(len(pairs)),
    }
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        coherence = np.nanmean(np.stack([p.coherence for p in pairs]), axis=0).astype(np.float32)
    return GunwAnalysis(dates, final.astype(np.float32), coherence, (int(r), int(c)), series, ref, stats)
