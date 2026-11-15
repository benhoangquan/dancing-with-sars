"""The science of `sar build` for chapters measured inside a mapped perimeter, on arrays only.

A fire that leaves trunks standing lowers L-band HV by less than a dB, which is below the noise of one 60 m
pixel. Averaged over a whole mapped perimeter it is measurable. The test is a difference in differences: the
median HV inside the perimeter minus the median HV of a ring of forest around it, after the fire minus before.
Regional changes (rain, season) move both and cancel. A placebo test moves the same shape across the scene to
show how large the difference gets where nothing burned.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from datetime import date

import numpy as np
from scipy import ndimage

RING_INNER_PX = 8  # leave a gap so edge pixels and mapping error do not leak into the ring
RING_OUTER_PX = 40
PLACEBO_N = 300


def _median(values: np.ndarray) -> float:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        return float(np.nanmedian(values)) if values.size else float("nan")


def ring(inside: np.ndarray, inner: int = RING_INNER_PX, outer: int = RING_OUTER_PX) -> np.ndarray:
    """Pixels between `inner` and `outer` pixels from the perimeter."""
    return ndimage.binary_dilation(inside, iterations=outer) & ~ndimage.binary_dilation(
        inside, iterations=inner
    )


def gaps(hv_db: np.ndarray, inside: np.ndarray, around: np.ndarray) -> np.ndarray:
    """Per date: median HV inside minus median HV in the ring, dB."""
    return np.array([_median(d[inside]) - _median(d[around]) for d in hv_db])


def diff_in_diff(gap: np.ndarray, pre: list[int], post: list[int]) -> float:
    """Mean gap after minus mean gap before. Negative means HV fell inside relative to the ring."""
    return float(np.mean(gap[post]) - np.mean(gap[pre]))


def placebo(
    hv_db: np.ndarray,
    inside: np.ndarray,
    pre: list[int],
    post: list[int],
    *,
    min_before_db: float,
    n: int = PLACEBO_N,
    seed: int = 0,
    max_tries: int = 20_000,
) -> np.ndarray:
    """The same statistic for the perimeter's shape moved to places that were forest before and did not burn
    (no overlap with the real perimeter or its ring)."""
    _, h, w = hv_db.shape
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        before = np.nanmedian(hv_db[pre], axis=0)
    rows, cols = np.nonzero(inside)
    keep_out = ndimage.binary_dilation(inside, iterations=RING_OUTER_PX)
    rng = np.random.default_rng(seed)
    out: list[float] = []
    for _ in range(max_tries):
        if len(out) >= n:
            break
        dr, dc = int(rng.integers(-h, h)), int(rng.integers(-w, w))
        r2, c2 = rows + dr, cols + dc
        ok = (r2 >= 0) & (r2 < h) & (c2 >= 0) & (c2 < w)
        if ok.mean() < 0.99:
            continue
        shifted = np.zeros_like(inside)
        shifted[r2[ok], c2[ok]] = True
        if (shifted & keep_out).any() or not _median(before[shifted]) > min_before_db:
            continue
        around = ring(shifted) & ~keep_out
        value = diff_in_diff(gaps(hv_db, shifted, around), pre, post)
        if np.isfinite(value):
            out.append(value)
    return np.array(out)


def placebo_blocks(
    hv_db: np.ndarray,
    inside: np.ndarray,
    pre: list[int],
    post: list[int],
    *,
    min_before_db: float,
    n: int = PLACEBO_N,
    seed: int = 0,
    max_tries: int = 20_000,
) -> np.ndarray:
    """For perimeters too large for shifted copies to fit: squares one sixth of the perimeter's area, placed
    on forest outside the perimeter and its ring, each compared with its own ring."""
    _, h, w = hv_db.shape
    side = max(8, int(np.sqrt(inside.sum() / 6)))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        before = np.nanmedian(hv_db[pre], axis=0)
    keep_out = ndimage.binary_dilation(inside, iterations=RING_OUTER_PX)
    rng = np.random.default_rng(seed)
    out: list[float] = []
    for _ in range(max_tries):
        if len(out) >= n:
            break
        r, c = int(rng.integers(0, h - side)), int(rng.integers(0, w - side))
        block = np.zeros_like(inside)
        block[r : r + side, c : c + side] = True
        if (block & keep_out).any() or not _median(before[block]) > min_before_db:
            continue
        around = ring(block) & ~keep_out
        if around.sum() < 200:
            continue
        value = diff_in_diff(gaps(hv_db, block, around), pre, post)
        if np.isfinite(value):
            out.append(value)
    return np.array(out)


@dataclass
class PerimeterAnalysis:
    pre_days: list[date]
    post_days: list[date]
    inside_series: list[tuple[date, float]]
    ring_series: list[tuple[date, float]]
    drop_db: float  # positive: HV fell inside relative to the ring
    placebo: np.ndarray
    stats: dict[str, float]
    placebo_kind: str = "shifted copies of the perimeter"


def analyze_perimeter(
    days: list[date],
    hv_db: np.ndarray,
    inside: np.ndarray,
    *,
    started: date,
    mapped: date,
    min_before_db: float,
    pixel_area_m2: float,
    placebo_n: int = PLACEBO_N,
) -> PerimeterAnalysis:
    """Before is every date before the fire started; after is every date after the perimeter was mapped.
    Dates while it burned are in the series but not in the comparison."""
    if inside.sum() < 50:
        raise ValueError("the perimeter covers fewer than 50 pixels of the radar grid")
    pre = [i for i, d in enumerate(days) if d < started]
    post = [i for i, d in enumerate(days) if d > mapped]
    if len(pre) < 2 or len(post) < 2:
        raise ValueError(
            f"need two dates before {started} and two after {mapped}, have {len(pre)} and {len(post)}"
        )
    around = ring(inside)
    gap = gaps(hv_db, inside, around)
    did = diff_in_diff(gap, pre, post)
    null = placebo(hv_db, inside, pre, post, min_before_db=min_before_db, n=placebo_n)
    kind = "shifted copies of the perimeter"
    if len(null) < 30:
        null = placebo_blocks(hv_db, inside, pre, post, min_before_db=min_before_db, n=placebo_n)
        kind = "squares of one sixth the perimeter's area"
    if len(null) < 30:
        raise ValueError(f"only {len(null)} placebo positions fit in the scene")
    inside_series = [(d, _median(hv_db[i][inside])) for i, d in enumerate(days)]
    ring_series = [(d, _median(hv_db[i][around])) for i, d in enumerate(days)]
    stats = {
        "drop_db": -did,
        "placebo_mean_db": float(null.mean()),
        "placebo_sd_db": float(null.std()),
        "placebo_n": float(len(null)),
        "placebo_share_as_low": float(np.mean(null <= did)),
        "inside_ha": float(inside.sum()) * pixel_area_m2 / 10_000.0,
        "n_dates": float(len(days)),
    }
    return PerimeterAnalysis(
        [days[i] for i in pre], [days[i] for i in post], inside_series, ring_series, -did, null, stats, kind
    )
