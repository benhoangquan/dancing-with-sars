"""The science of `sar build` for GCOV chapters, on arrays only: stack the dates, composite, find the loss.

Input is a `Stack`: linear HH and HV power for each acquisition date on one UTM lattice. Output is the median
composites of the before and after windows (in dB), the HV drop between them, the loss mask, a series of HV
over time inside the mask, and a stable-forest reference series.
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, field
from datetime import date

import numpy as np
from affine import Affine

from ..change import area_ha, hv_drop_db, loss_mask
from ..composite import to_db
from .fetch import load_tile, tile_path

REFERENCE_MAX_CHANGE_DB = 1.0  # stable forest: HV moved less than this between the windows
MIN_REFERENCE_PIXELS = 100


@dataclass
class Stack:
    days: list[date]
    hh: np.ndarray  # (n, H, W) linear power, NaN where there is no valid data
    hv: np.ndarray
    transform: Affine
    epsg: int
    res: float
    granules: dict[date, list[str]] = field(default_factory=dict)


def mosaic_stack(tiles_by_day: dict[date, list]) -> Stack:
    """Place every tile on the union lattice. Adjacent frames of one acquisition fill each other's gaps."""
    every = [t for ts in tiles_by_day.values() for t in ts]
    res, epsg = every[0].res, every[0].epsg
    if any(t.res != res or t.epsg != epsg for t in every):
        raise ValueError("tiles differ in resolution or projection")
    x0 = min(t.x0 for t in every)
    y0 = max(t.y0 for t in every)
    x1 = max(t.x0 + t.hh.shape[1] * res for t in every)
    y1 = min(t.y0 - t.hh.shape[0] * res for t in every)
    width, height = round((x1 - x0) / res), round((y0 - y1) / res)
    days = sorted(tiles_by_day)
    hh = np.full((len(days), height, width), np.nan, np.float32)
    hv = np.full_like(hh, np.nan)
    for i, day in enumerate(days):
        for t in tiles_by_day[day]:
            c, r = (t.x0 - x0) / res, (y0 - t.y0) / res
            if abs(c - round(c)) > 1e-6 or abs(r - round(r)) > 1e-6:
                raise ValueError("a tile is off the lattice")
            c, r = round(c), round(r)
            h, w = t.hh.shape
            for dst, src in ((hh, t.hh), (hv, t.hv)):
                region = dst[i, r : r + h, c : c + w]
                np.copyto(region, src, where=np.isnan(region))
    return Stack(days, hh, hv, Affine(res, 0, x0, 0, -res, y0), epsg, res)


def load_stack(slug: str, index: dict, root=None) -> Stack:
    """The cached tiles listed in `acquisitions.json`, mosaicked."""
    kwargs = {} if root is None else {"root": root}
    tiles = {
        date.fromisoformat(a["day"]): [load_tile(tile_path(slug, g["name"], **kwargs)) for g in a["granules"]]
        for a in index["acquisitions"]
    }
    stack = mosaic_stack(tiles)
    stack.granules = {
        date.fromisoformat(a["day"]): [g["name"] for g in a["granules"]] for a in index["acquisitions"]
    }
    return stack


def median_db(arr: np.ndarray) -> np.ndarray:
    """Per-pixel median over dates in linear power, then dB. NaN where no date has data."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        return to_db(np.nanmedian(arr, axis=0)).astype(np.float32)


def mean_db(values: np.ndarray) -> float:
    """dB of the mean linear power; NaN if there are no valid values."""
    ok = values[np.isfinite(values)]
    return float(10 * math.log10(ok.mean())) if ok.size else float("nan")


@dataclass
class Analysis:
    before_days: list[date]
    after_days: list[date]
    before_hh: np.ndarray
    before_hv: np.ndarray
    after_hh: np.ndarray
    after_hv: np.ndarray
    drop: np.ndarray
    mask: np.ndarray
    reference: np.ndarray
    series: list[tuple[date, float]]
    reference_series: list[tuple[date, float]]
    area_series: list[tuple[date, float]]  # cumulative hectares of loss, date by date
    stats: dict[str, float]


def _in_window(days: list[date], window: tuple[str, str], max_dates: int) -> list[int]:
    lo, hi = date.fromisoformat(window[0]), date.fromisoformat(window[1])
    return [i for i, d in enumerate(days) if lo <= d <= hi][:max_dates]


def analyze(
    stack: Stack,
    *,
    before: tuple[str, str],
    after: tuple[str, str],
    max_dates: int,
    drop_threshold_db: float,
    min_before_db: float,
    mmu_ha: float,
) -> Analysis:
    """Composite each window, find where HV fell past the threshold from a forested start, and measure it."""
    ib, ia = _in_window(stack.days, before, max_dates), _in_window(stack.days, after, max_dates)
    if not ib or not ia:
        raise ValueError(f"need dates in both windows, have before={len(ib)} after={len(ia)}")
    bhh, bhv = median_db(stack.hh[ib]), median_db(stack.hv[ib])
    ahh, ahv = median_db(stack.hh[ia]), median_db(stack.hv[ia])
    drop = hv_drop_db(bhv, ahv)
    pixel_m2 = stack.res**2
    mask = loss_mask(
        drop,
        bhv,
        threshold_db=drop_threshold_db,
        min_before_db=min_before_db,
        min_pixels=max(1, math.ceil(mmu_ha * 10_000 / pixel_m2)),
    )
    ref = np.isfinite(drop) & (np.abs(drop) < REFERENCE_MAX_CHANGE_DB) & (bhv > min_before_db) & ~mask
    if ref.sum() < MIN_REFERENCE_PIXELS:
        ref = np.zeros_like(ref)
    series, ref_series = [], []
    for i, day in enumerate(stack.days):
        v = mean_db(stack.hv[i][mask])
        if math.isfinite(v):
            series.append((day, v))
            r = mean_db(stack.hv[i][ref]) if ref.any() else float("nan")
            if math.isfinite(r):
                ref_series.append((day, r))
    area_series, running = [], 0.0
    for i, day in enumerate(stack.days):
        hv_i = to_db(stack.hv[i])
        m_i = loss_mask(
            hv_drop_db(bhv, hv_i),
            bhv,
            threshold_db=drop_threshold_db,
            min_before_db=min_before_db,
            min_pixels=max(1, math.ceil(mmu_ha * 10_000 / pixel_m2)),
        )
        running = max(running, area_ha(m_i, pixel_m2))  # loss does not reverse, so the curve never falls
        area_series.append((day, running))
    stats = {
        "area_ha": area_ha(mask, pixel_m2),
        "hv_before_db": float(np.nanmean(bhv[mask])) if mask.any() else float("nan"),
        "hv_after_db": float(np.nanmean(ahv[mask])) if mask.any() else float("nan"),
        "n_dates": float(len(series)),
    }
    stats["hv_drop_db"] = stats["hv_before_db"] - stats["hv_after_db"]
    return Analysis(
        [stack.days[i] for i in ib],
        [stack.days[i] for i in ia],
        bhh,
        bhv,
        ahh,
        ahv,
        drop,
        mask,
        ref,
        series,
        ref_series,
        area_series,
        stats,
    )
