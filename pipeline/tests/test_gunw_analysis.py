from datetime import date, timedelta

import numpy as np
import pytest

from sarstory.nisar.gunw_analysis import PairMotion, analyze_gunw, reference_to_median, smooth_nan

H, W, PIX = 120, 140, 80.0**2
D0 = date(2026, 6, 10)
ROW, COL = 60, 70


def bowl(depth):
    yy, xx = np.mgrid[0:H, 0:W]
    return (-depth * np.exp(-(((yy - ROW) / 14.0) ** 2 + ((xx - COL) / 18.0) ** 2) / 2)).astype(np.float32)


def make_pairs(n=6, per_pair_cm=1.5, offsets=None, nan_patch=None):
    pairs = []
    for i in range(n):
        m = bowl(per_pair_cm) + (0.0 if offsets is None else offsets[i])
        if nan_patch is not None:
            m = m.copy()
            m[nan_patch] = np.nan
        ref = D0 + timedelta(days=12 * i)
        pairs.append(PairMotion(ref, ref + timedelta(days=12), m, np.full((H, W), 0.7, np.float32)))
    return pairs


def test_cumulative_motion_finds_the_bowl_its_depth_rate_and_area():
    a = analyze_gunw(make_pairs(), pixel_area_m2=PIX)
    assert a.hotspot == pytest.approx((ROW, COL), abs=2)
    assert a.stats["max_subsidence_cm"] == pytest.approx(
        6 * 1.5, rel=0.03
    )  # six pairs of 1.5 cm at the center
    months = (a.dates[-1] - a.dates[0]).days / 30.44
    assert a.stats["rate_cm_per_month"] == pytest.approx(a.stats["max_subsidence_cm"] / months)
    assert a.stats["n_pairs"] == 6
    yy, xx = np.mgrid[0:H, 0:W]
    expected_px = ((9.0 * np.exp(-(((yy - ROW) / 14.0) ** 2 + ((xx - COL) / 18.0) ** 2) / 2)) > 5.0).sum()
    assert a.stats["area_over_5cm_ha"] == pytest.approx(expected_px * PIX / 1e4, rel=0.15)


def test_series_starts_at_zero_and_sinks_steadily_while_the_reference_stays_flat():
    a = analyze_gunw(make_pairs(), pixel_area_m2=PIX)
    values = [v for _, v in a.hotspot_series]
    assert values[0] == 0.0 and values == sorted(values, reverse=True)
    assert values[-1] == pytest.approx(-9.0, rel=0.05)
    assert a.dates[0] == D0 and a.dates[-1] == D0 + timedelta(days=72)
    assert len(a.reference_series) == 7 and all(abs(v) < 0.6 for _, v in a.reference_series)


def test_each_pair_is_referenced_so_an_arbitrary_phase_offset_cancels():
    offsets = [3.0, -7.0, 12.5, 0.0, -2.0, 5.0]  # every unwrapped phase has its own constant
    a = analyze_gunw(make_pairs(offsets=offsets), pixel_area_m2=PIX)
    assert a.stats["max_subsidence_cm"] == pytest.approx(9.0, rel=0.05)


def test_a_pixel_unusable_in_any_pair_is_excluded_from_the_final_map():
    a = analyze_gunw(make_pairs(nan_patch=(slice(0, 20), slice(0, 20))), pixel_area_m2=PIX)
    assert np.isnan(a.final_cm[:20, :20]).all() and np.isfinite(a.final_cm[60, 70])


def test_pairs_must_be_sequential_and_non_empty():
    pairs = make_pairs(3)
    pairs[1] = PairMotion(
        pairs[1].reference + timedelta(days=30),
        pairs[1].secondary + timedelta(days=30),
        pairs[1].motion_cm,
        pairs[1].coherence,
    )
    with pytest.raises(ValueError, match="sequential"):
        analyze_gunw(pairs, pixel_area_m2=PIX)
    with pytest.raises(ValueError, match="no interferograms"):
        analyze_gunw([], pixel_area_m2=PIX)


def test_a_scene_with_nothing_usable_raises_instead_of_inventing_a_hotspot():
    p = make_pairs(2, nan_patch=(slice(None), slice(None)))
    with pytest.raises(ValueError, match="no pixel is usable"):
        analyze_gunw(p, pixel_area_m2=PIX)


def test_helpers():
    m = np.array([[1.0, 2.0], [3.0, np.nan]], np.float32)
    assert np.nanmedian(reference_to_median(m)) == 0.0
    box = (slice(0, 1), slice(0, 2))
    assert reference_to_median(m, box)[0, 0] == pytest.approx(-0.5)
    s = smooth_nan(np.array([[1.0, np.nan], [np.nan, np.nan]], np.float32), sigma=0.5)
    assert s[0, 0] == pytest.approx(1.0)


def test_only_the_dominant_connected_component_is_kept():
    from sarstory.nisar.gunw_analysis import dominant_component

    comp = np.zeros((10, 10), np.uint16)
    comp[:, :7] = 1
    comp[:, 7:9] = 2  # a smaller component with its own arbitrary phase offset
    keep = dominant_component(comp)
    assert keep[:, :7].all() and not keep[:, 7:].any()
    assert not dominant_component(np.zeros((4, 4), np.uint16)).any()


def test_removing_a_plane_recovers_a_bowl_buried_in_a_ramp_without_flattening_it():
    from sarstory.nisar.gunw_analysis import remove_plane

    yy, xx = np.mgrid[0:H, 0:W]
    ramp = 0.08 * xx - 0.05 * yy + 12.0  # centimetres of atmospheric ramp across the scene
    truth = bowl(6.0)
    out = remove_plane(truth + ramp.astype(np.float32))
    assert np.abs(out - truth - np.median(out - truth)).max() < 0.7, "the ramp is gone"
    assert out[ROW, COL] - np.median(out) == pytest.approx(truth[ROW, COL], abs=1.0), "the bowl survives"


def test_remove_plane_leaves_nan_and_tiny_inputs_alone():
    from sarstory.nisar.gunw_analysis import remove_plane

    m = np.full((20, 20), np.nan, np.float32)
    m[0, 0] = 1.0
    assert np.isnan(remove_plane(m)[5, 5]) and remove_plane(m)[0, 0] == 1.0
    big = np.ones((30, 30), np.float32)
    big[3:6, 3:6] = np.nan
    assert np.isnan(remove_plane(big)[4, 4]) and np.isfinite(remove_plane(big)[10, 10])
