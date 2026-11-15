"""`sar fixture`: write `illustrative` layers, series, stats and a flyover into a chapter manifest.

The authored half of the manifest (title, beats, legend, action) is read as is. Everything under
`generated` is replaced. Fixture data is synthetic: every layer has status `illustrative` and cites
the `synthetic` source, and the site labels it as such.
"""

from __future__ import annotations

import math
import os
import shutil
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np
from rasterio.transform import Affine, from_bounds

from . import __version__
from .change import area_ha, hv_drop_db, largest_patches, loss_mask
from .cog import write_layer
from .composite import DEFAULT_STRETCH, sar_composite
from .config import CHAPTERS_DIR, DATA_DIR, load_config
from .fixture_patterns import bowl, burn, fishbone
from .manifest import read_manifest, write_manifest

CADENCE_DAYS = 12  # NISAR repeat cycle
SYNTHETIC_ID = "synthetic"
SYNTHETIC_SOURCE = {
    "id": SYNTHETIC_ID,
    "mission": "Synthetic",
    "product": "Synthetic pattern (illustrative)",
    "collection": "none",
    "maturity": "n/a",
    "granules": [],
    "dates": [],
    "provider": "this project",
    "license": "CC0-1.0",
    "url": "https://nisar-docs.asf.alaska.edu/gcov/",
    "nasa": False,
}
HV_DROP_RENDER = {"type": "ramp", "scheme": "BrewerYlOrRd9", "domain": [2, 10], "unit": "dB"}
DISPLACEMENT_RENDER = {"type": "ramp", "scheme": "SarDivergingDark", "domain": [-15, 15], "unit": "cm"}
COHERENCE_RENDER = {"type": "ramp", "scheme": "BrewerGreys9", "domain": [0, 1], "unit": "ratio"}
RGBA = {"type": "rgba"}
NOTE = "Synthetic pattern, not a measurement."


@dataclass(frozen=True)
class Grid:
    bbox: tuple[float, float, float, float]
    width: int
    height: int
    transform: Affine
    pixel_area_ha: float

    @property
    def shape(self) -> tuple[int, int]:
        return (self.height, self.width)

    @property
    def pixel_area_m2(self) -> float:
        return self.pixel_area_ha * 10_000.0

    def lonlat(self, row: float, col: float) -> list[float]:
        """Longitude and latitude of a pixel-grid position (row 0 is the north edge)."""
        w, s, e, n = self.bbox
        return [round(w + col / self.width * (e - w), 6), round(n - row / self.height * (n - s), 6)]


def make_grid(bbox: list[float], max_px: int = 640) -> Grid:
    """Square-pixel grid in a lon/lat frame over `bbox`, with the longer side `max_px` pixels."""
    west, south, east, north = bbox
    dx = (east - west) * 111_320.0 * math.cos(math.radians((south + north) / 2))
    dy = (north - south) * 110_574.0
    if dx >= dy:
        width, height = max_px, max(1, round(max_px * dy / dx))
    else:
        width, height = max(1, round(max_px * dx / dy)), max_px
    return Grid(
        (west, south, east, north),
        width,
        height,
        from_bounds(west, south, east, north, width, height),
        (dx / width) * (dy / height) / 10_000.0,
    )


def cycle_dates(start: str, count: int) -> list[str]:
    d0 = date.fromisoformat(start)
    return [(d0 + timedelta(days=CADENCE_DAYS * i)).isoformat() for i in range(count)]


def _window(pair: list[str]) -> str:
    return f"{pair[0]}/{pair[1]}"


def _stat(value: float, unit: str, decimals: int, label: str, method: str) -> dict:
    return {
        "value": round(float(value), decimals),
        "unit": unit,
        "decimals": decimals,
        "label": label,
        "method": f"{method} {NOTE}",
    }


def _points(dates: list[str], values) -> list[dict]:
    return [{"t": t, "v": round(float(v), 2)} for t, v in zip(dates, values, strict=True)]


def _ramp01(n: int, centre: float, width: float) -> np.ndarray:
    """Logistic 0..1 curve over `n` dates, rescaled so the first value is 0 and the last is 1."""
    s = 1.0 / (1.0 + np.exp(-(np.arange(n) - centre * (n - 1)) / width))
    return (s - s[0]) / (s[-1] - s[0])


def _rect(grid: Grid, box: tuple[int, int, int, int]) -> dict:
    r0, c0, r1, c1 = box
    ring = [
        grid.lonlat(r0, c0),
        grid.lonlat(r0, c1),
        grid.lonlat(r1, c1),
        grid.lonlat(r1, c0),
        grid.lonlat(r0, c0),
    ]
    return {"type": "Polygon", "coordinates": [ring]}


def _pin(grid: Grid, row: float, col: float) -> dict:
    return {"type": "Point", "coordinates": grid.lonlat(row + 0.5, col + 0.5)}


class Writer:
    """Writes layer files for one chapter and collects their manifest entries."""

    def __init__(self, slug: str, grid: Grid, data_dir: Path):
        self.slug, self.grid, self.data_dir, self.layers = slug, grid, data_dir, []

    def add(
        self,
        layer_id: str,
        kind: str,
        label: str,
        date_text: str,
        data: np.ndarray,
        render: dict,
        stretch: dict | None = None,
    ) -> None:
        self.layers.append(
            write_layer(
                self.slug,
                layer_id,
                kind=kind,
                label=label,
                date=date_text,
                data=data,
                transform=self.grid.transform,
                crs="EPSG:4326",
                render=render,
                source_ids=[SYNTHETIC_ID],
                status="illustrative",
                stretch=stretch,
                data_dir=self.data_dir,
            )
        )


def _fishbone(slug: str, cfg: dict, grid: Grid, rng: np.random.Generator, w: Writer) -> dict:
    p, win = cfg["processing"], cfg["windows"]
    a = fishbone(rng, grid.shape)
    stretch = {k: tuple(p.get(f"stretch_{k.lower()}", DEFAULT_STRETCH[k])) for k in DEFAULT_STRETCH}
    drop = hv_drop_db(a["hv_b"], a["hv_a"])
    mask = loss_mask(
        drop,
        a["hv_b"],
        threshold_db=p["drop_threshold_db"],
        min_before_db=p["min_before_db"],
        min_pixels=max(1, math.ceil(p["mmu_ha"] / grid.pixel_area_ha)),
        open_iterations=0,
    )
    before, after = _window(win["before"]), _window(win["after"])
    w.add("optical_before", "optical", "Optical, before", before, a["rgb_b"], RGBA)
    w.add("optical_after", "optical", "Optical, after", after, a["rgb_a"], RGBA)
    w.add(
        "sar_before",
        "sar-composite",
        "Radar composite, before",
        before,
        sar_composite(a["hh_b"], a["hv_b"], stretch),
        RGBA,
        stretch,
    )
    w.add(
        "sar_after",
        "sar-composite",
        "Radar composite, after",
        after,
        sar_composite(a["hh_a"], a["hv_a"], stretch),
        RGBA,
        stretch,
    )
    w.add(
        "hv_change",
        "change",
        "Radar HV drop",
        f"{win['before'][0]}/{win['after'][1]}",
        np.where(mask, drop, np.nan).astype(np.float32),
        HV_DROP_RENDER,
    )

    hv_before, hv_after = float(a["hv_b"][mask].mean()), float(a["hv_a"][mask].mean())
    dates = cycle_dates(cfg["series"]["start"], cfg["series"]["count"])
    n = len(dates)
    s = _ramp01(n, 0.55, 1.3)
    noise = rng.normal(0, 0.25, n) * np.sin(np.linspace(0, np.pi, n))  # zero at both ends
    ref = float((a["hv_b"][a["ref_mask"]].mean() + a["hv_a"][a["ref_mask"]].mean()) / 2)
    series = [
        {
            "id": "hv_cleared",
            "label": "HV backscatter in cleared pixels",
            "unit": "dB",
            "kind": "hv-backscatter",
            "points": _points(
                dates, np.round(hv_before, 1) + (np.round(hv_after, 1) - np.round(hv_before, 1)) * s + noise
            ),
            "reference": {"label": "Intact forest", "points": _points(dates, ref + rng.normal(0, 0.2, n))},
            "sourceIds": [SYNTHETIC_ID],
            "status": "illustrative",
        }
    ]
    stats = {
        "cleared_ha": _stat(
            area_ha(mask, grid.pixel_area_m2),
            "ha",
            0,
            "Forest cleared",
            "Area of pixels whose HV fell by more than the threshold.",
        ),
        "hv_drop_db": _stat(
            hv_before - hv_after,
            "dB",
            1,
            "HV drop in cleared pixels",
            "Mean HV before minus after inside the mask.",
        ),
        "hv_before_db": _stat(hv_before, "dB", 1, "HV before", "Mean HV inside the mask, before window."),
        "hv_after_db": _stat(hv_after, "dB", 1, "HV after", "Mean HV inside the mask, after window."),
        "n_dates": _stat(n, "count", 0, "Radar dates", "Acquisition dates in the series."),
    }
    patch = largest_patches(mask, 1)
    annotations = [
        {"id": "main_road", "label": "Main road", "kind": "pin", "geometry": _pin(grid, *a["road_pin"])}
    ]
    if patch:
        annotations.append(
            {"id": "new_clearing", "label": "New clearing", "kind": "area", "geometry": _rect(grid, patch[0])}
        )
    return {"series": series, "stats": stats, "annotations": annotations}


def _burn(slug: str, cfg: dict, grid: Grid, rng: np.random.Generator, w: Writer) -> dict:
    p, win = cfg["processing"], cfg["windows"]
    a = burn(rng, grid.shape)
    stretch = {k: tuple(p.get(f"stretch_{k.lower()}", DEFAULT_STRETCH[k])) for k in DEFAULT_STRETCH}
    drop = hv_drop_db(a["hv_b"], a["hv_a"])
    mask = loss_mask(
        drop,
        a["hv_b"],
        threshold_db=p["drop_threshold_db"],
        min_before_db=p["min_before_db"],
        min_pixels=max(1, math.ceil(p["mmu_ha"] / grid.pixel_area_ha)),
        open_iterations=1,
    )
    before, after = _window(win["before"]), _window(win["after"])
    w.add("optical_before", "optical", "Optical, before", before, a["rgb_b"], RGBA)
    w.add("optical_smoke", "optical", "Optical, smoke", win["smoke_scene"], a["rgb_s"], RGBA)
    w.add(
        "sar_before",
        "sar-composite",
        "Radar composite, before",
        before,
        sar_composite(a["hh_b"], a["hv_b"], stretch),
        RGBA,
        stretch,
    )
    w.add(
        "sar_after",
        "sar-composite",
        "Radar composite, after",
        after,
        sar_composite(a["hh_a"], a["hv_a"], stretch),
        RGBA,
        stretch,
    )
    w.add(
        "hv_change",
        "change",
        "Radar HV drop",
        f"{win['before'][0]}/{win['after'][1]}",
        np.where(mask, drop, np.nan).astype(np.float32),
        HV_DROP_RENDER,
    )

    burned = area_ha(mask, grid.pixel_area_m2)
    dates = cycle_dates(cfg["series"]["start"], cfg["series"]["count"])
    n = len(dates)
    frac = np.interp(
        np.linspace(0, 1, n), [0, 0.39, 0.444, 0.556, 0.667, 0.778, 1.0], [0, 0, 0.12, 0.55, 0.9, 1.0, 1.0]
    )
    values = np.round(burned * frac)
    values[-1] = round(burned)
    series = [
        {
            "id": "burned_area",
            "label": "Burned area, cumulative",
            "unit": "ha",
            "kind": "affected-area",
            "points": _points(dates, values),
            "sourceIds": [SYNTHETIC_ID],
            "status": "illustrative",
        }
    ]
    stats = {
        "burned_ha": _stat(
            burned, "ha", 0, "Burned area", "Area of pixels whose HV fell by more than the threshold."
        ),
        "hv_drop_db": _stat(
            drop[mask].mean(),
            "dB",
            1,
            "HV drop in the burn scar",
            "Mean HV before minus after inside the mask.",
        ),
        "smoke_cloud_pct": _stat(
            a["smoke_pct"], "%", 0, "Optical scene under smoke", "Share of pixels with haze above one half."
        ),
        "n_dates": _stat(n, "count", 0, "Radar dates", "Acquisition dates in the series."),
    }
    patch = largest_patches(mask, 1)
    lake_row = grid.height // 2
    lake_col = int(np.flatnonzero(a["lake"][lake_row])[0]) if a["lake"][lake_row].any() else grid.width // 3
    annotations = [
        {
            "id": "water_dark",
            "label": "Water: dark in radar",
            "kind": "pin",
            "geometry": _pin(grid, lake_row, lake_col),
        }
    ]
    if patch:
        annotations.append(
            {"id": "burn_scar", "label": "Burn scar", "kind": "area", "geometry": _rect(grid, patch[0])}
        )
    return {"series": series, "stats": stats, "annotations": annotations}


def _bowl(slug: str, cfg: dict, grid: Grid, rng: np.random.Generator, w: Writer) -> dict:
    p = cfg["processing"]
    a = bowl(rng, grid.shape)
    stretch = {k: tuple(p.get(f"stretch_{k.lower()}", DEFAULT_STRETCH[k])) for k in DEFAULT_STRETCH}
    dates = cycle_dates(cfg["series"]["start"], cfg["series"]["count"])
    n = len(dates)
    span = f"{dates[0]}/{dates[-1]}"
    w.add("optical_after", "optical", "Optical", cfg["windows"]["optical"], a["rgb_a"], RGBA)
    w.add(
        "sar_after",
        "sar-composite",
        "Radar composite",
        span,
        sar_composite(a["hh"], a["hv"], stretch),
        RGBA,
        stretch,
    )
    w.add(
        "displacement",
        "displacement",
        "Ground motion along the radar line of sight",
        span,
        a["disp"],
        DISPLACEMENT_RENDER,
    )
    w.add("coherence", "coherence", "Radar coherence", span, a["coh"], COHERENCE_RENDER)

    disp = a["disp"]
    deepest = float(-np.nanmin(disp))
    months = (date.fromisoformat(dates[-1]) - date.fromisoformat(dates[0])).days / 30.44
    s = np.linspace(0, 1, n) ** 0.9
    wobble = rng.normal(0, 0.08, n) * np.sin(np.linspace(0, np.pi, n))
    series = [
        {
            "id": "displacement_hotspot",
            "label": "Ground motion at the deepest point",
            "unit": "cm",
            "kind": "displacement",
            "points": _points(dates, -round(deepest, 1) * s + wobble),
            "reference": {"label": "Stable reference area", "points": _points(dates, rng.normal(0, 0.12, n))},
            "sourceIds": [SYNTHETIC_ID],
            "status": "illustrative",
        }
    ]
    stats = {
        "max_subsidence_cm": _stat(
            deepest, "cm", 1, "Deepest sinking", "Largest downward displacement in the interferogram."
        ),
        "area_over_5cm_ha": _stat(
            np.nansum(disp < -5) * grid.pixel_area_ha,
            "ha",
            0,
            "Area sinking over 5 cm",
            "Area of pixels below -5 cm.",
        ),
        "rate_cm_per_month": _stat(
            deepest / months,
            "cm/month",
            1,
            "Sinking rate at the deepest point",
            "Deepest sinking divided by the span in months.",
        ),
        "n_pairs": _stat(n - 1, "count", 0, "Interferograms", "Sequential date pairs in the series."),
    }
    over5 = np.nan_to_num(disp, nan=0.0) < -5
    patch = largest_patches(over5, 1)
    row, col = a["deepest"]
    annotations = [
        {"id": "deepest_point", "label": "Deepest point", "kind": "pin", "geometry": _pin(grid, row, col)}
    ]
    if patch:
        annotations.append(
            {
                "id": "subsidence_bowl",
                "label": "Sinking over 5 cm",
                "kind": "area",
                "geometry": _rect(grid, patch[0]),
            }
        )
    return {"series": series, "stats": stats, "annotations": annotations}


BUILDERS = {"fishbone": _fishbone, "burn": _burn, "bowl": _bowl}


def flyover_from_config(cfg: dict) -> dict:
    fl = cfg["flyover"]
    waypoints = [
        {
            "t": wp["t"],
            "camera": {
                "center": list(wp["center"]),
                "zoom": wp["zoom"],
                "pitch": wp["pitch"],
                "bearing": wp["bearing"],
            },
        }
        for wp in fl["waypoints"]
    ]
    return {"duration": fl["duration"], "exaggeration": fl["exaggeration"], "waypoints": waypoints}


def _now() -> str:
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    moment = datetime.fromtimestamp(int(epoch), UTC) if epoch else datetime.now(UTC)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def build_fixture(
    slug: str, *, data_dir: Path = DATA_DIR, chapters_dir: Path = CHAPTERS_DIR, force: bool = False
) -> Path:
    """Replace `generated` in the slug's manifest with illustrative data and write its layer files."""
    manifest = read_manifest(slug, chapters_dir)
    real = [
        lyr["id"]
        for lyr in manifest.get("generated", {}).get("layers", [])
        if lyr.get("status") != "illustrative"
    ]
    if real and not force:
        raise RuntimeError(f"{slug}: layers {real} hold real or fallback data; pass --force to replace them")
    cfg = load_config(slug)
    fx = cfg["fixture"]
    grid = make_grid(manifest["aoi"]["bbox"], fx.get("max_px", 640))
    shutil.rmtree(data_dir / slug, ignore_errors=True)
    writer = Writer(slug, grid, data_dir)
    parts = BUILDERS[fx["pattern"]](slug, cfg, grid, np.random.default_rng(fx["seed"]), writer)
    manifest["generated"] = {
        "pipelineVersion": f"{__version__}+fixture",
        "builtAt": _now(),
        "layers": writer.layers,
        "series": parts["series"],
        "stats": parts["stats"],
        "flyover": flyover_from_config(cfg),
        "annotations": parts["annotations"],
        "sources": [SYNTHETIC_SOURCE],
    }
    return write_manifest(slug, manifest, chapters_dir)
