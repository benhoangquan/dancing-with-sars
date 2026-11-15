"""Synthetic spatial patterns for the `illustrative` fixture layers.

Each function returns arrays on an (H, W) grid with row 0 at the north edge. None of this is a
measurement: it shows the pattern a chapter is about so the site works before real data is built.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage


def smooth(rng: np.random.Generator, shape: tuple[int, int], sigma: float, std: float = 1.0) -> np.ndarray:
    """Gaussian-filtered noise rescaled to the requested standard deviation."""
    a = ndimage.gaussian_filter(rng.standard_normal(shape), sigma, mode="reflect")
    return a / (a.std() or 1.0) * std


def drop_small(mask: np.ndarray, min_pixels: int) -> np.ndarray:
    """Remove connected patches smaller than `min_pixels`."""
    labels, n = ndimage.label(mask)
    if n == 0:
        return mask
    sizes = ndimage.sum(mask, labels, index=np.arange(1, n + 1))
    return np.concatenate([[False], sizes >= min_pixels])[labels]


def _mark(mask: np.ndarray, rows: np.ndarray, cols: np.ndarray) -> None:
    h, w = mask.shape
    r, c = np.rint(rows).astype(int), np.rint(cols).astype(int)
    ok = (r >= 0) & (r < h) & (c >= 0) & (c < w)
    mask[r[ok], c[ok]] = True


def _line(mask: np.ndarray, p0: tuple[float, float], p1: tuple[float, float]) -> None:
    n = int(max(abs(p1[0] - p0[0]), abs(p1[1] - p0[1]))) * 2 + 2
    _mark(mask, np.linspace(p0[0], p1[0], n), np.linspace(p0[1], p1[1], n))


def _rgb(base: np.ndarray, tex: np.ndarray) -> np.ndarray:
    """(H, W, 3) float colors plus (H, W) texture -> (4, H, W) uint8 RGBA."""
    rgb = np.clip(base + tex[..., None], 0, 255)
    out = np.empty((4, *tex.shape), np.uint8)
    out[:3] = np.moveaxis(np.rint(rgb), -1, 0).astype(np.uint8)
    out[3] = 255
    return out


def fishbone(rng: np.random.Generator, shape: tuple[int, int]) -> dict:
    """Forest with a sinuous main road and perpendicular branch roads. The older branches are already
    cleared in the before scene; the rest are cleared by the after scene."""
    h, w = shape
    t = np.linspace(0.0, 1.0, 600)
    rows = 0.08 * h + t * 0.84 * h
    cols = 0.12 * w + t * 0.76 * w + 0.03 * w * np.sin(t * 9) + 0.015 * w * np.sin(t * 23 + 1)
    drow, dcol = np.gradient(rows), np.gradient(cols)
    norm = np.hypot(drow, dcol)
    nrow, ncol = -dcol / norm, drow / norm  # unit normal to the road

    main = np.zeros(shape, bool)
    _mark(main, rows, cols)
    old_branches = np.zeros(shape, bool)
    new_branches = np.zeros(shape, bool)
    for k, tt in enumerate(np.arange(0.07, 0.94, 0.08)):
        i = int(tt * (len(t) - 1))
        for side in (-1, 1):
            length = rng.uniform(0.07, 0.17) * w
            jitter = rng.uniform(-0.18, 0.18)
            ang = np.array(
                [
                    nrow[i] * np.cos(jitter) - ncol[i] * np.sin(jitter),
                    nrow[i] * np.sin(jitter) + ncol[i] * np.cos(jitter),
                ]
            )
            end = (rows[i] + side * ang[0] * length, cols[i] + side * ang[1] * length)
            _line(old_branches if k < 4 else new_branches, (rows[i], cols[i]), end)

    grow = ndimage.binary_dilation
    cleared_before = grow(main, iterations=1) | grow(old_branches, iterations=1)
    new_only = grow(new_branches, iterations=1)
    # Lots near the road ends of the newest branches, so the after scene has block clearings too.
    lots = np.zeros(shape, bool)
    for _ in range(14):
        r, c = rng.integers(0, h - 12), rng.integers(0, w - 14)
        if new_only[max(0, r - 6) : r + 6, max(0, c - 7) : c + 7].any():
            lots[r : r + rng.integers(4, 9), c : c + rng.integers(5, 12)] = True
    cleared_after = cleared_before | new_only | lots
    new_mask = cleared_after & ~cleared_before

    forest_hv = -13.6 + smooth(rng, shape, 40, 0.5) + smooth(rng, shape, 2.5, 0.7)
    forest_hh = -7.6 + 0.6 * (forest_hv + 13.6) + smooth(rng, shape, 2.0, 0.5)
    bare_hv = -20.5 + smooth(rng, shape, 2.0, 0.8)
    bare_hh = -11.0 + smooth(rng, shape, 2.0, 0.8)

    def scene(cleared: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        m = ndimage.gaussian_filter(cleared.astype(float), 0.8)
        hv = forest_hv * (1 - m) + bare_hv * m + rng.normal(0, 0.35, shape)
        hh = forest_hh * (1 - m) + bare_hh * m + rng.normal(0, 0.35, shape)
        tex = smooth(rng, shape, 1.5, 6.0)
        forest_c, bare_c = np.array([28.0, 66.0, 34.0]), np.array([176.0, 150.0, 110.0])
        base = forest_c * (1 - m[..., None]) + bare_c * m[..., None]
        return hh, hv, _rgb(base, tex)

    hh_b, hv_b, rgb_b = scene(cleared_before)
    hh_a, hv_a, rgb_a = scene(cleared_after)
    ref = np.zeros(shape, bool)
    ref[int(0.78 * h) : int(0.96 * h), int(0.04 * w) : int(0.20 * w)] = True
    mid = int(0.5 * (len(t) - 1))
    return {
        "hh_b": hh_b,
        "hv_b": hv_b,
        "rgb_b": rgb_b,
        "hh_a": hh_a,
        "hv_a": hv_a,
        "rgb_a": rgb_a,
        "new_mask": new_mask,
        "ref_mask": ref & ~cleared_after,
        "road_pin": (rows[mid], cols[mid]),
    }


def burn(rng: np.random.Generator, shape: tuple[int, int]) -> dict:
    """Hilly forest with a lake and a wind-elongated burn scar. Smoke covers part of the optical scene."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    elev = smooth(rng, shape, 30, 1.0) + 0.5 * smooth(rng, shape, 10, 1.0)
    gx = np.gradient(elev, axis=1)
    terr = np.clip(gx / (gx.std() or 1.0), -2, 2) / 2.0  # slope-facing effect, -1 to 1

    lake = np.abs(xx - (0.35 * w + 0.03 * w * np.sin(yy / h * 7))) < 0.04 * w
    forest_hv = -12.8 + 1.2 * terr + smooth(rng, shape, 3, 0.6)
    forest_hh = -7.0 + 0.8 * terr + smooth(rng, shape, 2.5, 0.5)

    blobs = [(0.45, 0.62, 0.10, 0.045), (0.32, 0.66, 0.06, 0.035), (0.58, 0.60, 0.06, 0.030)]
    field = sum(
        np.exp(-(((yy - cy * h) / (sy * h)) ** 2 + ((xx - cx * w) / (sx * w)) ** 2))
        for cy, cx, sy, sx in blobs
    )
    field = field + 0.12 * smooth(rng, shape, 6, 1.0)
    scar = drop_small((field > 0.45) & ~lake, 300)
    drop = np.clip(5.2 + smooth(rng, shape, 8, 1.2), 2.5, None) * ndimage.gaussian_filter(
        scar.astype(float), 1.0
    )

    def sar(after: bool) -> tuple[np.ndarray, np.ndarray]:
        hv = forest_hv - (drop if after else 0.0) + rng.normal(0, 0.35, shape)
        hh = forest_hh - (0.5 * drop if after else 0.0) + rng.normal(0, 0.35, shape)
        return np.where(lake, -22.0, hh), np.where(lake, -27.0, hv)

    hh_b, hv_b = sar(False)
    hh_a, hv_a = sar(True)

    shade = 0.78 + 0.22 * terr
    forest_c, water_c = np.array([30.0, 72.0, 36.0]), np.array([35.0, 70.0, 110.0])
    base_b = np.where(lake[..., None], water_c, forest_c * shade[..., None])
    rgb_b = _rgb(base_b, smooth(rng, shape, 1.5, 5.0))

    # Smoke: haze that hides the ground in patches, with hot spots on the scar edge.
    haze = np.clip(0.55 + 0.35 * smooth(rng, shape, 35, 1.0), 0.0, 0.95)
    edge = scar & ~ndimage.binary_erosion(scar)
    hot = ndimage.gaussian_filter((edge & (rng.random(shape) < 0.04)).astype(float), 2.5)
    hot = np.clip(hot / (hot.max() or 1.0), 0, 1)
    base_s = base_b * (1 - haze[..., None]) + np.array([196.0, 190.0, 184.0]) * haze[..., None]
    base_s = base_s * (1 - hot[..., None]) + np.array([255.0, 140.0, 40.0]) * hot[..., None]
    rgb_s = _rgb(base_s, smooth(rng, shape, 2.0, 3.0))
    return {
        "hh_b": hh_b,
        "hv_b": hv_b,
        "rgb_b": rgb_b,
        "hh_a": hh_a,
        "hv_a": hv_a,
        "rgb_s": rgb_s,
        "scar": scar,
        "lake": lake,
        "smoke_pct": float((haze > 0.5).mean() * 100.0),
    }


def bowl(rng: np.random.Generator, shape: tuple[int, int]) -> dict:
    """Farmland with subsidence bowls (LOS displacement in cm, negative is sinking) and coherence."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(float)

    def gauss(cx: float, cy: float, sx: float, sy: float, amp: float) -> np.ndarray:
        return amp * np.exp(-0.5 * (((xx - cx * w) / (sx * w)) ** 2 + ((yy - cy * h) / (sy * h)) ** 2))

    disp = (
        gauss(0.42, 0.55, 0.13, 0.17, -11.5)
        + gauss(0.72, 0.28, 0.07, 0.09, -5.5)
        + gauss(0.20, 0.25, 0.05, 0.06, -3.0)
    )
    disp = disp + smooth(rng, shape, 60, 0.3) + (xx / w - 0.5) * 0.3 + smooth(rng, shape, 3, 0.12)

    # Field blocks from jittered grid lines.
    xs = np.unique(np.concatenate([[0, w], np.cumsum(rng.integers(26, 70, 20))]))
    ys = np.unique(np.concatenate([[0, h], np.cumsum(rng.integers(22, 60, 20))]))
    field_id = (
        np.searchsorted(xs, np.arange(w), side="right")[None, :] * 100
        + np.searchsorted(ys, np.arange(h), side="right")[:, None]
    )
    ids = np.unique(field_id)
    palette = np.array(
        [[92, 128, 56], [170, 155, 92], [118, 96, 64], [60, 100, 48], [196, 176, 110], [84, 70, 50]], float
    )
    pick = {i: rng.integers(0, len(palette)) for i in ids}
    offset = {i: rng.normal(0, 2.0) for i in ids}
    color = np.array([palette[pick[i]] for i in field_id.ravel()]).reshape(h, w, 3)
    field_off = np.array([offset[i] for i in field_id.ravel()]).reshape(h, w)

    canal = np.abs((yy / h) - (0.92 - 0.30 * (xx / w))) < 0.012
    urban = ((xx - 0.80 * w) ** 2 / (0.05 * w) ** 2 + (yy - 0.78 * h) ** 2 / (0.06 * h) ** 2) < 1
    color = np.where(canal[..., None], [92.0, 110.0, 120.0], color)
    color = np.where(urban[..., None], [150.0, 148.0, 144.0], color)
    rgb_a = _rgb(color, smooth(rng, shape, 1.5, 6.0))

    hh = -10.0 + field_off + smooth(rng, shape, 1.5, 0.8) + rng.normal(0, 0.4, shape)
    hv = -17.5 + 0.6 * field_off + smooth(rng, shape, 1.5, 0.6) + rng.normal(0, 0.4, shape)
    hh = np.where(canal, -22.0, np.where(urban, -4.0, hh))
    hv = np.where(canal, -28.0, np.where(urban, -12.0, hv))

    gy, gx = np.gradient(disp)
    coh = 0.82 + smooth(rng, shape, 4, 0.05) - 0.5 * np.clip(np.hypot(gy, gx), 0, 0.5)
    coh = np.where(canal, 0.2, np.where(urban, 0.35, coh))
    coh = np.clip(coh, 0.0, 1.0).astype(np.float32)
    disp = np.where(coh < 0.35, np.nan, disp).astype(np.float32)
    deepest = np.unravel_index(np.nanargmin(disp), disp.shape)
    return {"disp": disp, "coh": coh, "hh": hh, "hv": hv, "rgb_a": rgb_a, "deepest": deepest}
