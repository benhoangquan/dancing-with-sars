"""ColorBrewer ramps used by the web layers, so Python previews match the browser's `#color:` ramps."""

from __future__ import annotations

import numpy as np

BREWER = {
    "BrewerYlOrRd9": [
        "#ffffcc",
        "#ffeda0",
        "#fed976",
        "#feb24c",
        "#fd8d3c",
        "#fc4e2a",
        "#e31a1c",
        "#bd0026",
        "#800026",
    ],
    "BrewerRdBu11": [
        "#67001f",
        "#b2182b",
        "#d6604d",
        "#f4a582",
        "#fddbc7",
        "#f7f7f7",
        "#d1e5f0",
        "#92c5de",
        "#4393c3",
        "#2166ac",
        "#053061",
    ],
    "BrewerGreys9": [
        "#ffffff",
        "#f0f0f0",
        "#d9d9d9",
        "#bdbdbd",
        "#969696",
        "#737373",
        "#525252",
        "#252525",
        "#000000",
    ],
}


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    c = color.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def ramp_rgba(values: np.ndarray, scheme: str, domain: tuple[float, float]) -> np.ndarray:
    """(H, W) float array -> (4, H, W) uint8 RGBA. NaN is transparent; values clip to the domain ends."""
    stops = np.array([hex_to_rgb(c) for c in BREWER[scheme]], dtype=np.float64)
    lo, hi = domain
    t = np.clip((values - lo) / (hi - lo), 0.0, 1.0)
    pos = t * (len(stops) - 1)
    i0 = np.floor(np.nan_to_num(pos)).astype(int).clip(0, len(stops) - 2)
    frac = (np.nan_to_num(pos) - i0)[..., None]
    rgb = stops[i0] * (1 - frac) + stops[i0 + 1] * frac
    out = np.empty((4, *values.shape), np.uint8)
    out[:3] = np.moveaxis(np.rint(rgb), -1, 0).astype(np.uint8)
    out[3] = np.where(np.isfinite(values), 255, 0).astype(np.uint8)
    return out
