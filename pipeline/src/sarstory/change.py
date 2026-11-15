"""Backscatter change: HV drop in dB, the loss mask and area statistics."""

from __future__ import annotations

import numpy as np
from scipy import ndimage


def hv_drop_db(before_db: np.ndarray, after_db: np.ndarray) -> np.ndarray:
    """HV before minus HV after in dB. Positive means backscatter was lost."""
    return before_db - after_db


def loss_mask(
    drop_db: np.ndarray,
    before_db: np.ndarray,
    *,
    threshold_db: float,
    min_before_db: float,
    min_pixels: int,
    open_iterations: int = 1,
) -> np.ndarray:
    """Pixels whose HV fell by more than `threshold_db` from a forested start (`before_db` above
    `min_before_db`), cleaned with a binary open (`open_iterations` times, 0 to skip it for features
    only a few pixels wide) and close, with patches under `min_pixels` removed."""
    raw = np.isfinite(drop_db) & (drop_db > threshold_db) & (before_db > min_before_db)
    opened = ndimage.binary_opening(raw, iterations=open_iterations) if open_iterations > 0 else raw
    clean = ndimage.binary_closing(opened)
    labels, n = ndimage.label(clean)
    if n == 0:
        return clean
    sizes = ndimage.sum(clean, labels, index=np.arange(1, n + 1))
    keep = np.concatenate([[False], sizes >= min_pixels])
    return keep[labels]


def area_ha(mask: np.ndarray, pixel_area_m2: float) -> float:
    return float(mask.sum()) * pixel_area_m2 / 10_000.0


def largest_patches(mask: np.ndarray, count: int) -> list[tuple[int, int, int, int]]:
    """Bounding boxes (row0, col0, row1, col1; end exclusive) of the `count` largest connected patches."""
    labels, n = ndimage.label(mask)
    if n == 0:
        return []
    sizes = ndimage.sum(mask, labels, index=np.arange(1, n + 1))
    order = np.argsort(sizes)[::-1][:count]
    boxes = ndimage.find_objects(labels)
    out = []
    for i in order:
        rs, cs = boxes[int(i)]
        out.append((rs.start, cs.start, rs.stop, cs.stop))
    return out
