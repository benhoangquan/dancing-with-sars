import json
import shutil

import pytest
from conftest import authored_path, fixture_slugs

from sarstory import fixture
from sarstory.config import CHAPTERS_DIR
from sarstory.invariants import check_invariants
from sarstory.manifest import read_manifest, validate, verify_assets


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    """Every chapter built into a temporary tree so the repo's own files stay untouched."""
    root = tmp_path_factory.mktemp("fx")
    chapters = root / "public" / "chapters"
    chapters.mkdir(parents=True)
    for s in fixture_slugs():
        shutil.copy(authored_path(s), chapters / f"{s}.json")
        fixture.build_fixture(s, data_dir=root / "public" / "data", chapters_dir=chapters, force=True)
    return root


@pytest.mark.parametrize("slug", fixture_slugs())
def test_built_manifest_is_valid_and_assets_match(built, slug):
    obj = read_manifest(slug, built / "public" / "chapters")
    assert validate(obj) == []
    errs, warns = check_invariants(obj)
    assert errs == [] and warns == []
    assert verify_assets(obj, built / "public") == []
    assert {lyr["status"] for lyr in obj["generated"]["layers"]} == {"illustrative"}


def stat(obj, key):
    return obj["generated"]["stats"][key]["value"]


def last(obj, series_id):
    s = next(x for x in obj["generated"]["series"] if x["id"] == series_id)
    return s["points"][-1]["v"]


def test_stats_are_physically_plausible_and_match_series_ends(built):
    chapters = built / "public" / "chapters"
    ron, sj = (read_manifest(s, chapters) for s in ("rondonia", "san-joaquin"))
    assert 1_000 < stat(ron, "cleared_ha") < 50_000
    assert stat(ron, "hv_before_db") > stat(ron, "hv_after_db")
    assert stat(ron, "hv_drop_db") == pytest.approx(
        stat(ron, "hv_before_db") - stat(ron, "hv_after_db"), abs=0.11
    )
    assert last(ron, "hv_cleared") == pytest.approx(stat(ron, "hv_after_db"), abs=0.01)
    assert 8 < stat(sj, "max_subsidence_cm") < 15
    assert last(sj, "displacement_hotspot") == pytest.approx(-stat(sj, "max_subsidence_cm"), abs=0.15)
    assert stat(sj, "n_pairs") == len(sj["generated"]["series"][0]["points"]) - 1


def test_fixture_is_deterministic(built, tmp_path):
    chapters = tmp_path / "public" / "chapters"
    chapters.mkdir(parents=True)
    shutil.copy(CHAPTERS_DIR / "rondonia.json", chapters / "rondonia.json")
    fixture.build_fixture(
        "rondonia", data_dir=tmp_path / "public" / "data", chapters_dir=chapters, force=True
    )
    a = read_manifest("rondonia", built / "public" / "chapters")["generated"]["layers"]
    b = read_manifest("rondonia", chapters)["generated"]["layers"]
    assert [(x["id"], x["sha256"]) for x in a] == [(x["id"], x["sha256"]) for x in b]


def test_refuses_to_overwrite_real_data_without_force(built, tmp_path):
    chapters = tmp_path / "public" / "chapters"
    chapters.mkdir(parents=True)
    obj = json.loads((built / "public" / "chapters" / "rondonia.json").read_text())
    obj["generated"]["layers"][0]["status"] = "real"
    (chapters / "rondonia.json").write_text(json.dumps(obj))
    with pytest.raises(RuntimeError, match="--force"):
        fixture.build_fixture("rondonia", data_dir=tmp_path / "public" / "data", chapters_dir=chapters)


def test_cycle_dates_and_grid():
    assert fixture.cycle_dates("2026-06-17", 3) == ["2026-06-17", "2026-06-29", "2026-07-11"]
    g = fixture.make_grid([-63.80, -10.40, -62.90, -9.70], 640)
    assert max(g.width, g.height) == 640
    assert g.pixel_area_m2 == pytest.approx(g.pixel_area_ha * 10_000)
    assert g.lonlat(0, 0) == [-63.8, -9.7] and g.lonlat(g.height, g.width) == [-62.9, -10.4]
