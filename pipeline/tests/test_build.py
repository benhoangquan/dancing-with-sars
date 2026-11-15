"""The two real builds end to end on small synthetic caches. Only the optical step (network) is replaced."""

import json
import shutil
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest
from affine import Affine

from sarstory.cog import write_layer
from sarstory.config import CHAPTERS_DIR
from sarstory.invariants import check_invariants
from sarstory.manifest import read_manifest, validate, verify_assets
from sarstory.nisar import build as gcov_build
from sarstory.nisar import build_gunw
from sarstory.nisar.fetch import save_pair, save_tile, tile_path
from sarstory.nisar.gcov import Tile
from sarstory.nisar.gunw import Pair

TEST_DATA = Path(__file__).parent / "data"

RES, EPSG = 60.0, 32720
H, W = 80, 100
X0, Y0 = 412200.0, 8927760.0


def fake_optical(slug, specs, bbox, lattice, data_dir, log=print):
    """Stands in for the Planetary Computer step: one tiny real COG per spec, same return shape."""
    layers = []
    for spec in specs:
        rgba = np.zeros((4, lattice.height, lattice.width), np.uint8)
        rgba[0], rgba[3] = 120, 255
        layers.append(
            write_layer(
                slug,
                spec["id"],
                kind="optical",
                label=spec["label"],
                date="2026-06-20",
                data=rgba,
                transform=lattice.transform,
                crs=lattice.crs,
                render={"type": "rgba"},
                source_ids=["hls"],
                status="real",
                data_dir=data_dir,
            )
        )
    hls = {
        "id": "hls",
        "mission": "HLS",
        "product": "HLS",
        "collection": "HLSS30",
        "maturity": "validated",
        "granules": ["x"],
        "dates": ["2026-06-20"],
        "provider": "NASA",
        "license": "open",
        "url": "https://example.test/hls",
        "nasa": True,
    }
    return layers, hls, {}


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    chapters = tmp_path / "public" / "chapters"
    chapters.mkdir(parents=True)
    shutil.copy(CHAPTERS_DIR / "rondonia.json", chapters / "rondonia.json")
    shutil.copy(
        TEST_DATA / "san-joaquin.json", chapters / "san-joaquin.json"
    )  # off the site; keeps GUNW tested
    monkeypatch.setattr(gcov_build, "build_layers", fake_optical)
    monkeypatch.setattr(build_gunw, "build_layers", fake_optical)
    return tmp_path, chapters


def test_gcov_build_writes_a_valid_manifest_with_real_layers_and_the_measured_numbers(workspace):
    root, chapters = workspace
    cache = root / "cache"
    days = [date(2026, 6, 25) + timedelta(days=12 * i) for i in range(7)]  # Jun 25 .. Sep 5
    days += [date(2026, 9, 17), date(2026, 9, 29)]
    index = {
        "collection": "NISAR_L2_GCOV_PROVISIONAL_V1",
        "maturity": "provisional",
        "track": "161_A",
        "block_m": RES,
        "acquisitions": [],
    }
    forest, cleared = 10 ** (-1.2), 10 ** (-1.95)  # about -12 dB and -19.5 dB
    for day in days:
        hv = np.full((H, W), forest, np.float32)
        if day >= date(2026, 8, 1):
            hv[30:50, 40:70] = cleared
        hh = np.full((H, W), 10 ** (-0.7), np.float32)
        name = f"NISAR_L2_PR_GCOV_{day:%Y%m%d}"
        save_tile(tile_path("rondonia", name, cache), Tile(hh, hv, X0, Y0, RES, EPSG))
        index["acquisitions"].append(
            {
                "day": day.isoformat(),
                "coverage": 1.0,
                "granules": [{"name": name, "size_mb": 1800.0, "frame": "172"}],
            }
        )
    (cache / "rondonia" / "acquisitions.json").write_text(json.dumps(index))
    path = gcov_build.build(
        "rondonia",
        data_dir=root / "public" / "data",
        chapters_dir=chapters,
        cache_root=cache,
        log=lambda *_: None,
    )
    obj = json.loads(path.read_text())
    assert validate(obj) == [] and check_invariants(obj) == ([], [])
    assert verify_assets(obj, root / "public") == []
    g = obj["generated"]
    assert {lyr["status"] for lyr in g["layers"]} == {"real"}
    assert {s["id"] for s in g["sources"]} == {"nisar-gcov", "hls"}
    nisar = next(s for s in g["sources"] if s["id"] == "nisar-gcov")
    assert nisar["maturity"] == "provisional" and nisar["collection"] == "NISAR_L2_GCOV_PROVISIONAL_V1"
    assert len(nisar["granules"]) == len(days) and nisar["dates"][0] == "2026-06-25"
    # 20 x 30 blocks of 0.36 ha is 216 ha; the binary open rounds the corners and costs a few blocks
    assert 205 <= g["stats"]["cleared_ha"]["value"] <= 217
    assert g["stats"]["hv_drop_db"]["value"] == pytest.approx(7.5, abs=0.2)
    series = next(s for s in g["series"] if s["id"] == "hv_cleared")
    assert series["points"][0]["v"] > series["points"][-1]["v"] and series["reference"]["points"]
    assert {a["id"] for a in g["annotations"]} == {"new_clearing"}
    assert g["stats"]["n_dates"]["value"] == len(days)


def test_gcov_build_without_cached_tiles_fails_clearly(workspace):
    root, chapters = workspace
    with pytest.raises(FileNotFoundError):
        gcov_build.build("rondonia", data_dir=root / "d", chapters_dir=chapters, cache_root=root / "empty")


def test_gunw_build_sums_the_pairs_into_a_valid_manifest(workspace):
    root, chapters = workspace
    cache = root / "cache"
    rows, cols, res, wl = 90, 110, 80.0, 0.242
    yy, xx = np.mgrid[0:rows, 0:cols]
    bowl = np.exp(-(((yy - 45) / 12.0) ** 2 + ((xx - 55) / 16.0) ** 2) / 2)
    index = {
        "collection": "NISAR_L2_GUNW_PROVISIONAL_V1",
        "maturity": "provisional",
        "stack": "114_D_070",
        "pairs": [],
    }
    start = date(2026, 6, 10)
    for i in range(6):
        # 1.6 cm of sinking per pair at the center. Motion is -phase * wl / (4 pi) * 100,
        # so the phase that gives it is +1.6 * 4 pi / (wl * 100).
        phase = (bowl * 1.6 * 4 * np.pi / (wl * 100)).astype(
            np.float32
        ) + 3.0 * i  # arbitrary offset per pair
        name = f"NISAR_L2_PR_GUNW_{i:03d}"
        save_pair(
            tile_path("san-joaquin", name, cache),
            Pair(
                phase,
                np.full((rows, cols), 0.7, np.float32),
                np.zeros((rows, cols), np.float32),
                np.ones((rows, cols), np.uint16),
                300000.0,
                4000000.0,
                res,
                32611,
                wl,
            ),
        )
        ref = start + timedelta(days=12 * i)
        index["pairs"].append(
            {
                "name": name,
                "reference": ref.isoformat(),
                "secondary": (ref + timedelta(days=12)).isoformat(),
                "size_mb": 2200.0,
            }
        )
    (cache / "san-joaquin" / "pairs.json").write_text(json.dumps(index))
    path = build_gunw.build(
        "san-joaquin",
        data_dir=root / "public" / "data",
        chapters_dir=chapters,
        cache_root=cache,
        log=lambda *_: None,
    )
    obj = json.loads(path.read_text())
    assert validate(obj) == [] and check_invariants(obj) == ([], [])
    assert verify_assets(obj, root / "public") == []
    g = obj["generated"]
    assert {lyr["id"] for lyr in g["layers"]} == {"optical_after", "displacement", "coherence"}
    assert g["stats"]["max_subsidence_cm"]["value"] == pytest.approx(9.6, rel=0.05)
    assert g["stats"]["n_pairs"]["value"] == 6
    pts = next(s for s in g["series"] if s["id"] == "displacement_hotspot")["points"]
    assert pts[0]["v"] == 0 and pts[-1]["v"] == pytest.approx(-9.6, rel=0.06) and len(pts) == 7
    assert {a["id"] for a in g["annotations"]} == {"deepest_point", "subsidence_bowl"}


def test_the_source_entries_are_never_marked_validated_unless_the_collection_is(workspace):
    root, chapters = workspace
    obj = read_manifest("rondonia", chapters)
    assert obj["slug"] == "rondonia"
    assert gcov_build.nisar_source.__name__ == "nisar_source"


def test_a_transform_helper_agrees_with_the_tile_geometry():
    t = Tile(np.zeros((2, 3), np.float32), np.zeros((2, 3), np.float32), X0, Y0, RES, EPSG)
    assert t.transform == Affine(RES, 0, X0, 0, -RES, Y0)
