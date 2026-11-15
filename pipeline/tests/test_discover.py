from dataclasses import replace
from datetime import date

import pytest

from sarstory.nisar import discover as D
from sarstory.nisar.search import (
    Granule,
    acquisitions,
    choose_gcov_stack,
    choose_gunw_stack,
    coverage,
    parse_granule,
    union_coverage,
)

BBOX = (-63.80, -10.40, -62.90, -9.70)
NAME = "NISAR_L2_PR_GCOV_023_060_A_173_2005_DHDH_A_20260618T095301_20260618T095336_P05023_N_F_J_001"


def umm(poly=((-64.0, -10.6), (-62.5, -10.6), (-62.5, -9.5), (-64.0, -9.5)), **attrs):
    base = {"STACK_ID": ["060_A_173"], "FREQUENCY_A_POLARIZATION_CONCAT": ["HH+HV"], "FULL_FRAME": ["TRUE"]}
    base.update(attrs)
    return {
        "GranuleUR": NAME,
        "TemporalExtent": {
            "RangeDateTime": {
                "BeginningDateTime": "2026-06-18T09:53:01.000Z",
                "EndingDateTime": "2026-06-18T09:53:36.000Z",
            }
        },
        "CollectionReference": {"ShortName": "NISAR_L2_GCOV_PROVISIONAL_V1", "Version": "1"},
        "AdditionalAttributes": [{"Name": k, "Values": v} for k, v in base.items()],
        "SpatialExtent": {
            "HorizontalSpatialDomain": {
                "Geometry": {
                    "GPolygons": [
                        {"Boundary": {"Points": [{"Longitude": x, "Latitude": y} for x, y in poly]}}
                    ]
                }
            }
        },
    }


def test_parse_granule_reads_the_real_record_shape():
    raw = {"umm": umm(), "size": 1638.7, "links": ["https://h.test/x.h5.md5", "https://h.test/x.h5"]}
    g = parse_granule(raw, BBOX)
    assert g is not None
    assert (g.stack, g.polarizations, g.full_frame) == ("060_A_173", "HH+HV", True)
    assert (g.start, g.end) == (date(2026, 6, 18), date(2026, 6, 18))
    assert g.collection == "NISAR_L2_GCOV_PROVISIONAL_V1" and g.size_mb == pytest.approx(1638.7)
    assert g.url == "https://h.test/x.h5" and g.coverage == pytest.approx(1.0)


def test_parse_granule_skips_names_that_are_not_nisar_l2():
    other = umm()
    other["GranuleUR"] = "S1A_IW_SLC__1SDV_20260618"
    assert parse_granule({"umm": other, "size": 1, "links": []}, BBOX) is None


def test_coverage_is_the_share_of_the_study_area_inside_the_footprint():
    assert coverage([(-64, -11), (-62, -11), (-62, -9), (-64, -9)], BBOX) == pytest.approx(1.0)
    half = [(-64, -11), (-63.35, -11), (-63.35, -9), (-64, -9)]  # covers the western half
    assert coverage(half, BBOX) == pytest.approx(0.5, abs=1e-6)
    assert coverage([(-70, 0), (-69, 0), (-69, 1), (-70, 1)], BBOX) == 0.0
    assert coverage([], BBOX) == 0.0


def footprint(west_share=0.0, east_share=1.0):
    """A footprint spanning all latitudes of the study area and part of its width, as (lon, lat) corners."""
    w, e = BBOX[0] + west_share * (BBOX[2] - BBOX[0]), BBOX[0] + east_share * (BBOX[2] - BBOX[0])
    if west_share <= 0:
        w -= 0.5
    if east_share >= 1:
        e += 0.5
    return ((w, -11.0), (e, -11.0), (e, -9.0), (w, -9.0))


def g(stack, day, *, cov=1.0, pol="HH+HV", end=None, coll="NISAR_L2_GCOV_PROVISIONAL_V1", fp=None):
    d = date.fromisoformat(day)
    fp = fp or footprint(0.0, cov)
    return Granule(
        f"n-{stack}-{day}",
        coll,
        stack,
        d,
        date.fromisoformat(end) if end else d,
        1800.0,
        "u",
        pol,
        True,
        coverage(list(fp), BBOX),
        fp,
    )


BEFORE, AFTER = ("2026-06-17", "2026-07-11"), ("2026-09-09", "2026-10-03")


def test_gcov_track_needs_both_windows_in_one_track():
    granules = [
        g("060_A_173", "2026-06-18"),
        g("060_A_173", "2026-06-30"),
        g("060_A_173", "2026-09-10"),
        g("068_D_093", "2026-06-18"),
        g("161_A_172", "2026-09-12"),
    ]  # the others have one window each
    c = choose_gcov_stack(granules, BBOX, BEFORE, AFTER)
    assert c is not None and c.stack == "060_A"
    assert [x.day.isoformat() for x in c.before] == ["2026-06-18", "2026-06-30"]
    assert [x.day.isoformat() for x in c.after] == ["2026-09-10"]


def test_two_frames_of_one_pass_together_cover_a_study_area_neither_covers_alone():
    # The Rondonia case: frames 093 and 094 of track 068 each cover part of the study area.
    west, east = footprint(0.0, 0.55), footprint(0.45, 1.0)
    granules = [
        g(f"068_D_{f}", day, fp=fp)
        for day in ("2026-06-18", "2026-09-10")
        for f, fp in (("093", west), ("094", east))
    ]
    assert max(x.coverage for x in granules) < 0.7  # no single frame is enough
    c = choose_gcov_stack(granules, BBOX, BEFORE, AFTER)
    assert c is not None and c.stack == "068_D"
    assert [x.frame for x in c.before[0].granules] == ["093", "094"]
    assert c.before[0].coverage == pytest.approx(1.0, abs=0.03)
    assert c.before[0].size_mb == pytest.approx(3600.0)


def test_union_coverage_counts_overlap_once_and_a_gap_as_uncovered():
    assert union_coverage([footprint(0.0, 0.5), footprint(0.5, 1.0)], BBOX) == pytest.approx(1.0, abs=0.03)
    assert union_coverage([footprint(0.0, 0.5), footprint(0.25, 0.75)], BBOX) == pytest.approx(0.75, abs=0.03)
    assert union_coverage([footprint(0.0, 0.3), footprint(0.6, 1.0)], BBOX) == pytest.approx(0.7, abs=0.03)
    assert union_coverage([], BBOX) == 0.0


def test_acquisitions_keep_one_granule_per_frame_for_a_day():
    first = g("161_A_173", "2026-06-25")
    other_mode = replace(first, name="n-other-mode")  # a second product mode of the same frame and day
    acqs = acquisitions([other_mode, first], BBOX)["161_A"]
    assert len(acqs) == 1 and len(acqs[0].granules) == 1
    assert acqs[0].granules[0].name == first.name  # deterministic: the first by name


def test_gcov_track_rejects_partial_coverage_and_single_pol_and_returns_none_without_a_match():
    partial = [g("060_A_173", "2026-06-18", cov=0.4), g("060_A_173", "2026-09-10", cov=0.4)]
    assert choose_gcov_stack(partial, BBOX, BEFORE, AFTER) is None
    single = [g("060_A_173", "2026-06-18", pol="HH"), g("060_A_173", "2026-09-10", pol="HH")]
    assert choose_gcov_stack(single, BBOX, BEFORE, AFTER) is None
    assert choose_gcov_stack([g("060_A_173", "2026-06-18")], BBOX, BEFORE, AFTER) is None


def test_gcov_track_prefers_more_dates_in_the_thinner_window():
    a = [g("A_D_001", "2026-06-18"), g("A_D_001", "2026-09-10")]
    b = [
        g("B_D_001", "2026-06-20"),
        g("B_D_001", "2026-07-02"),
        g("B_D_001", "2026-09-12"),
        g("B_D_001", "2026-09-24"),
    ]
    c = choose_gcov_stack(a + b, BBOX, BEFORE, AFTER)
    assert c is not None and c.stack == "B_D"


def test_gcov_track_caps_dates_per_window():
    gs = [g("A_D_001", f"2026-06-{d:02d}") for d in range(17, 28)] + [g("A_D_001", "2026-09-10")]
    c = choose_gcov_stack(gs, BBOX, ("2026-06-01", "2026-06-30"), AFTER, max_dates=3)
    assert c is not None and len(c.before) == 3


def test_gunw_chain_is_the_longest_run_of_sequential_pairs():
    pairs = [
        g("034_A_020", "2026-06-16", end="2026-06-28"),
        g("034_A_020", "2026-06-28", end="2026-07-10"),
        g("034_A_020", "2026-07-10", end="2026-07-22"),
        g("034_A_020", "2026-08-15", end="2026-08-27"),  # a gap: this pair starts a new chain
        g("042_D_070", "2026-06-17", end="2026-06-29"),
    ]
    c = choose_gunw_stack(pairs, ("2026-06-01", "2026-10-15"))
    assert c is not None and c.stack == "034_A_020" and len(c.pairs) == 3


class FakeSearch:
    def __init__(self, by_collection):
        self.by_collection, self.calls = by_collection, []

    def __call__(self, short_name, bbox, temporal):
        self.calls.append(short_name)
        return self.by_collection.get(short_name, [])


def test_discover_takes_the_best_maturity_that_has_a_valid_stack(monkeypatch):
    monkeypatch.setattr(D, "read_manifest", lambda slug: {"aoi": {"bbox": list(BBOX)}})
    prov = "NISAR_L2_GCOV_PROVISIONAL_V1"
    fake = FakeSearch(
        {
            "NISAR_L2_GCOV_V1": [
                g("060_A_173", "2026-10-23", coll="NISAR_L2_GCOV_V1")
            ],  # production data only after
            prov: [g("060_A_173", "2026-06-18"), g("060_A_173", "2026-09-10")],
        }
    )
    r = D.discover("rondonia", search_fn=fake, today=date(2026, 11, 14))
    assert fake.calls == ["NISAR_L2_GCOV_V1", prov, "NISAR_L2_GCOV_BETA_V1"]
    assert r.selected is not None and r.selected.short_name == prov and r.selected.maturity == "provisional"
    text = D.render_report(r, generated=date(2026, 11, 14))
    assert "Use **`NISAR_L2_GCOV_PROVISIONAL_V1`** (provisional), track **`060_A`**" in text
    assert "| `NISAR_L2_GCOV_V1` | validated | 1 | 1 |" in text


def test_discover_reports_stepping_down_the_ladder_when_nothing_matches(monkeypatch):
    monkeypatch.setattr(D, "read_manifest", lambda slug: {"aoi": {"bbox": list(BBOX)}})
    r = D.discover("rondonia", search_fn=FakeSearch({}), today=date(2026, 11, 14))
    assert r.selected is None
    assert "steps down the data" in D.render_report(r)


def test_discover_uses_a_chain_for_gunw(monkeypatch):
    monkeypatch.setattr(D, "read_manifest", lambda slug: {"aoi": {"bbox": [-119.95, 35.85, -119.05, 36.45]}})
    prov = "NISAR_L2_GUNW_PROVISIONAL_V1"
    pairs = [
        g("034_A_020", "2026-06-16", end="2026-06-28", coll=prov),
        g("034_A_020", "2026-06-28", end="2026-07-10", coll=prov),
    ]
    r = D.discover("san-joaquin", search_fn=FakeSearch({prov: pairs}), today=date(2026, 11, 14))
    assert r.selected is not None and len(r.selected.choice.pairs) == 2
    assert "sequential interferograms" in D.render_report(r)


def test_maturity_names():
    assert D.maturity_of("NISAR_L2_GCOV_V1") == "validated"
    assert D.maturity_of("NISAR_L2_GUNW_PROVISIONAL_V1") == "provisional"
    assert D.maturity_of("NISAR_L2_GCOV_BETA_V1") == "beta"
