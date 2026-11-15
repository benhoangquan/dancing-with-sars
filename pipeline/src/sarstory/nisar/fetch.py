"""`sar fetch`: read the study-area window of every granule `discover` chose, and cache it.

Each granule becomes a small `.npz` of block-averaged HH and HV under `pipeline/cache/<slug>/`, so `sar build`
runs offline and an interrupted fetch resumes where it stopped. Needs an Earthdata Login in `~/.netrc`.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict
from datetime import date
from pathlib import Path

import h5py
import numpy as np

from ..config import CACHE_DIR, load_config
from .discover import Report, discover
from .gcov import Tile, read_tile
from .gunw import Pair, read_pair
from .hdf5 import Fetch
from .search import Acquisition, ChainChoice, Granule, StackChoice, acquisitions

BLOCK_M = 60.0
RETRIES = 4


def cache_dir(slug: str, root: Path = CACHE_DIR) -> Path:
    return root / slug


def tile_path(slug: str, granule_name: str, root: Path = CACHE_DIR) -> Path:
    return cache_dir(slug, root) / f"{granule_name}.npz"


def save_tile(path: Path, tile: Tile) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, hh=tile.hh, hv=tile.hv, geo=np.array([tile.x0, tile.y0, tile.res, tile.epsg]))


def load_tile(path: Path) -> Tile:
    with np.load(path) as z:
        x0, y0, res, epsg = z["geo"]
        return Tile(z["hh"], z["hv"], float(x0), float(y0), float(res), int(epsg))


def series_acquisitions(report: Report, slug: str) -> list[Acquisition]:
    """Every dual-pol acquisition of the chosen track between the start of the first window and the end of the
    last one that covers the study area. The before and after windows use some; the series uses all."""
    sel = report.selected
    if not sel or not isinstance(sel.choice, StackChoice):
        raise RuntimeError(f"{slug}: discovery found no GCOV track; step down the data ladder")
    cfg = load_config(slug)
    first, last = (
        date.fromisoformat(report.windows["before"][0]),
        date.fromisoformat(report.windows["after"][1]),
    )
    usable = [g for g in sel.granules if g.polarizations == "HH+HV" and g.coverage > 0]
    acqs = acquisitions(usable, report.bbox)[sel.choice.stack]
    return [a for a in acqs if first <= a.day <= last and a.coverage >= cfg["discover"]["min_coverage"]]


def write_index(slug: str, report: Report, acqs: list[Acquisition], root: Path = CACHE_DIR) -> Path:
    """`acquisitions.json`: what was fetched, for `sar build`. Granule URLs are not stored."""
    sel = report.selected
    assert sel is not None and sel.choice is not None
    index = {
        "slug": slug,
        "collection": sel.short_name,
        "maturity": sel.maturity,
        "track": sel.choice.stack,
        "block_m": BLOCK_M,
        "acquisitions": [
            {
                "day": a.day.isoformat(),
                "coverage": round(a.coverage, 3),
                "granules": [
                    {**{k: v for k, v in asdict(g).items() if k in ("name", "size_mb")}, "frame": g.frame}
                    for g in a.granules
                ],
            }
            for a in acqs
        ],
    }
    path = cache_dir(slug, root) / "acquisitions.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, indent=1) + "\n", encoding="utf-8")
    return path


def _session_tools():
    import earthaccess

    auth = earthaccess.login(strategy="netrc", persist=False)
    if not auth.authenticated:
        raise RuntimeError(
            "no Earthdata Login in ~/.netrc; run earthaccess.login(strategy='interactive', persist=True)"
        )
    return earthaccess.get_fsspec_https_session(), earthaccess.get_requests_https_session()


def make_fetch(session, url: str) -> Fetch:
    def fetch(offset: int, size: int) -> bytes:
        for attempt in range(RETRIES):
            try:
                r = session.get(url, headers={"Range": f"bytes={offset}-{offset + size - 1}"}, timeout=120)
                r.raise_for_status()
                if len(r.content) == size:
                    return r.content
            except Exception:
                if attempt == RETRIES - 1:
                    raise
            time.sleep(1.5 * (attempt + 1))
        raise OSError(f"short read of {size} bytes at {offset}")

    return fetch


def fetch_granule(g: Granule, bbox, fs, session) -> Tile | None:
    with (
        fs.open(g.url, mode="rb", block_size=4 * 1024**2, cache_type="blockcache") as fobj,
        h5py.File(fobj, "r") as h5,
    ):
        return read_tile(h5, bbox, make_fetch(session, g.url), block_m=BLOCK_M)


def run(slug: str, *, report: Report | None = None, log=print) -> Path:
    """Fetch every missing granule for the chapter and write the index. Returns the cache directory."""
    report = report or discover(slug)
    if report.product == "GUNW":
        return run_gunw(slug, report, log)
    acqs = series_acquisitions(report, slug)
    fs, session = _session_tools()
    todo = [g for a in acqs for g in a.granules if not tile_path(slug, g.name).exists()]
    log(
        f"{slug}: {len(acqs)} acquisitions, {sum(len(a.granules) for a in acqs)} granules, "
        f"{len(todo)} to fetch"
    )
    for i, g in enumerate(todo, 1):
        t = time.time()
        tile = fetch_granule(g, report.bbox, fs, session)
        if tile is None:
            raise RuntimeError(f"{g.name}: the granule does not reach the study area")
        save_tile(tile_path(slug, g.name), tile)
        valid = float(np.isfinite(tile.hv).mean())
        log(
            f"  [{i}/{len(todo)}] {g.start} frame {g.frame}: {tile.hv.shape} blocks, "
            f"{valid:.0%} valid, {time.time() - t:.0f}s"
        )
    write_index(slug, report, acqs)
    return cache_dir(slug)


def save_pair(path: Path, pair: Pair) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    geo = np.array([pair.x0, pair.y0, pair.res, pair.epsg, pair.wavelength_m])
    np.savez_compressed(
        path, phase=pair.phase, coherence=pair.coherence, iono=pair.ionosphere, comp=pair.components, geo=geo
    )


def load_pair(path: Path) -> Pair:
    with np.load(path) as z:
        x0, y0, res, epsg, wl = z["geo"]
        return Pair(
            z["phase"],
            z["coherence"],
            z["iono"],
            z["comp"],
            float(x0),
            float(y0),
            float(res),
            int(epsg),
            float(wl),
        )


def run_gunw(slug: str, report: Report, log=print) -> Path:
    """Fetch the sequential interferograms of the chosen stack and write `pairs.json`."""
    sel = report.selected
    if not sel or not isinstance(sel.choice, ChainChoice):
        raise RuntimeError(f"{slug}: discovery found no GUNW chain; step down the data ladder")
    pairs = sel.choice.pairs
    fs, session = _session_tools()
    todo = [g for g in pairs if not tile_path(slug, g.name).exists()]
    log(f"{slug}: {len(pairs)} interferograms, {len(todo)} to fetch")
    for i, g in enumerate(todo, 1):
        t = time.time()
        with (
            fs.open(g.url, mode="rb", block_size=4 * 1024**2, cache_type="blockcache") as fobj,
            h5py.File(fobj, "r") as h5,
        ):
            pair = read_pair(h5, report.bbox, make_fetch(session, g.url))
        if pair is None:
            raise RuntimeError(f"{g.name}: the granule does not reach the study area")
        save_pair(tile_path(slug, g.name), pair)
        usable = float(np.isfinite(pair.phase).mean())
        shape, secs = pair.phase.shape, time.time() - t
        log(f"  [{i}/{len(todo)}] {g.start} to {g.end}: {shape}, {usable:.0%} usable, {secs:.0f}s")
    index = {
        "slug": slug,
        "collection": sel.short_name,
        "maturity": sel.maturity,
        "stack": sel.choice.stack,
        "pairs": [
            {
                "name": g.name,
                "reference": g.start.isoformat(),
                "secondary": g.end.isoformat(),
                "size_mb": g.size_mb,
            }
            for g in pairs
        ],
    }
    path = cache_dir(slug) / "pairs.json"
    path.write_text(json.dumps(index, indent=1) + "\n", encoding="utf-8")
    return cache_dir(slug)
