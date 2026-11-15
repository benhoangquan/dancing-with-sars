"""SAR false-color composite: R = HH, G = HV, B = HH/HV (HH minus HV in dB), on fixed stretches."""

from __future__ import annotations

import numpy as np

DEFAULT_STRETCH = {"HH": (-20.0, 0.0), "HV": (-28.0, -8.0), "ratio": (0.0, 15.0)}
MIN_LINEAR = 1e-6  # about -60 dB; keeps log10 finite for zero or negative speckle


def to_db(linear: np.ndarray) -> np.ndarray:
    """Linear gamma-0 power to dB. NaN stays NaN."""
    return 10.0 * np.log10(np.clip(linear, MIN_LINEAR, None))


def _scale(db: np.ndarray, lo_hi: tuple[float, float]) -> np.ndarray:
    lo, hi = lo_hi
    return np.rint(np.clip((db - lo) / (hi - lo), 0.0, 1.0) * 255.0)


def sar_composite(hh_db: np.ndarray, hv_db: np.ndarray, stretch: dict | None = None) -> np.ndarray:
    """(H, W) HH and HV in dB -> (4, H, W) uint8 RGBA. Alpha is 0 where either input is not finite.
    Use the same stretch for the before and after composites so they stay comparable."""
    s = {**DEFAULT_STRETCH, **(stretch or {})}
    valid = np.isfinite(hh_db) & np.isfinite(hv_db)
    out = np.zeros((4, *hh_db.shape), np.uint8)
    out[0] = np.where(valid, _scale(hh_db, s["HH"]), 0).astype(np.uint8)
    out[1] = np.where(valid, _scale(hv_db, s["HV"]), 0).astype(np.uint8)
    out[2] = np.where(valid, _scale(hh_db - hv_db, s["ratio"]), 0).astype(np.uint8)
    out[3] = np.where(valid, 255, 0).astype(np.uint8)
    return out
