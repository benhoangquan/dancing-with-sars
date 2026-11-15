"""`sar landmarks`: radar readings at each authored landmark pin, from the cached NISAR stack.

A reading is the median dB of a 3 x 3 pixel window (180 m) in the same composites the chapter shows, so the
popover numbers match the map. Which dates count as before and after follows the chapter's build mode.
"""

from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path

import numpy as np
from rasterio.warp import transform as warp_points

from .config import CACHE_DIR, CHAPTERS_DIR, load_config
from .manifest import read_manifest, write_manifest
from .nisar.analysis import Stack, load_stack


def windows(cfg: dict, days: list[date]) -> list[tuple[str, str, list[int]]]:
    """(label, layer id, date indices) for each reading the chapter's mode supports."""
    if "perimeter" in cfg:
        started, mapped = (
            date.fromisoformat(cfg["perimeter"]["started"]),
            date.fromisoformat(cfg["perimeter"]["mapped"]),
        )
        return [
            ("HV before the fire", "sar_before", [i for i, d in enumerate(days) if d < started]),
            ("HV after the fire", "sar_after", [i for i, d in enumerate(days) if d > mapped]),
        ]
    if cfg.get("real", {}).get("mode") == "imagery":
        every = list(range(len(days)))
        return [("HH, 2026", "sar_2026", every), ("HV, 2026", "sar_2026", every)]
    out = []
    for key, label, layer in (("before", "HV before", "sar_before"), ("after", "HV after", "sar_after")):
        lo, hi = (date.fromisoformat(x) for x in cfg["windows"][key])
        out.append((label, layer, [i for i, d in enumerate(days) if lo <= d <= hi]))
    return out


def reading_at(stack: Stack, band: np.ndarray, idx: list[int], lon: float, lat: float) -> float | None:
    xs, ys = warp_points("EPSG:4326", f"EPSG:{stack.epsg}", [lon], [lat])
    col, row = ~stack.transform * (xs[0], ys[0])
    r, c = int(math.floor(row)), int(math.floor(col))
    h, w = band.shape[1:]
    if not (1 <= r < h - 1 and 1 <= c < w - 1) or not idx:
        return None
    with np.errstate(all="ignore"):
        window = band[idx][:, r - 1 : r + 2, c - 1 : c + 2]
        value = float(np.nanmedian(10 * np.log10(window)))
    return value if math.isfinite(value) else None


AREA_PIN = "inside_perimeter"


def perimeter_readings(cfg: dict, manifest: dict) -> dict[str, list[dict]]:
    """For a perimeter chapter the measurement is the gap between the burn and the ring of forest around
    it (median HV inside minus median HV in the ring), before and after the fire. A single 180 m patch is
    noise at this signal size, and absolute values move with rain and season, so the burn's pin shows that
    gap from the chapter's series."""
    started = date.fromisoformat(cfg["perimeter"]["started"])
    mapped = date.fromisoformat(cfg["perimeter"]["mapped"])
    series = next(s for s in manifest["generated"]["series"] if "reference" in s)
    ring = {p["t"]: p["v"] for p in series["reference"]["points"]}
    gaps = [(date.fromisoformat(p["t"]), p["v"] - ring[p["t"]]) for p in series["points"] if p["t"] in ring]
    pre = [g for d, g in gaps if d < started]
    post = [g for d, g in gaps if d > mapped]
    if not pre or not post:
        return {}
    row = {"unit": "dB", "decimals": 1}
    return {
        AREA_PIN: [
            {
                "label": "Burn minus forest, before",
                "value": round(float(np.mean(pre)), 1),
                **row,
                "layerId": "sar_before",
            },
            {
                "label": "Burn minus forest, after",
                "value": round(float(np.mean(post)), 1),
                **row,
                "layerId": "sar_after",
            },
        ]
    }


def build_landmarks(slug: str, *, chapters_dir: Path = CHAPTERS_DIR, cache_root: Path = CACHE_DIR) -> Path:
    cfg = load_config(slug)
    manifest = read_manifest(slug, chapters_dir)
    index = json.loads((cache_root / slug / "acquisitions.json").read_text())
    stack = load_stack(slug, index, cache_root)
    layers = {lyr["id"] for lyr in manifest["generated"]["layers"]}
    out: dict[str, list[dict]] = {}
    if "perimeter" in cfg:
        out = perimeter_readings(cfg, manifest)
    for lm in manifest.get("landmarks", []):
        if lm["id"] in out or "perimeter" in cfg:
            continue
        rows = []
        for label, layer_id, idx in windows(cfg, stack.days):
            band = stack.hh if label.startswith("HH") else stack.hv
            value = reading_at(stack, band, idx, *lm["lonLat"])
            if value is not None and layer_id in layers:
                rows.append(
                    {
                        "label": label,
                        "value": round(value, 1),
                        "unit": "dB",
                        "decimals": 1,
                        "layerId": layer_id,
                    }
                )
        if rows:
            out[lm["id"]] = rows
    manifest["generated"]["landmarkReadings"] = out
    return write_manifest(slug, manifest, chapters_dir)
