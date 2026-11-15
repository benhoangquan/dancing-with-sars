from datetime import date, timedelta

import numpy as np
import pytest

from sarstory.nisar.goff import OffsetPair
from sarstory.nisar.goff_analysis import SpeedPair, analyze_goff, to_speed

H, W, PIX = 120, 160, 80.0**2
D0 = date(2026, 6, 23)
ROW, COL = 60, 90


def glacier(peak):
    """A river of ice along the middle rows, fastest at (ROW, COL); everything else is still."""
    yy, xx = np.mgrid[0:H, 0:W]
    return (peak * np.exp(-(((yy - ROW) / 10.0) ** 2) / 2) * np.exp(-(((xx - COL) / 45.0) ** 2) / 2)).astype(
        np.float32
    )


def make_pairs(peaks, noise=0.3, seed=2):
    rng = np.random.default_rng(seed)
    out = []
    for i, peak in enumerate(peaks):
        ref = D0 + timedelta(days=12 * i)
        speed = glacier(peak) + np.abs(rng.normal(0, noise, (H, W))).astype(np.float32)
        out.append(SpeedPair(ref, ref + timedelta(days=12), speed))
    return out


def test_the_fastest_point_its_speed_and_the_distance_it_moved_in_one_pair():
    a = analyze_goff(make_pairs([20.0] * 6), pixel_area_m2=PIX)
    assert a.hotspot == pytest.approx((ROW, COL), abs=2)
    assert a.stats["peak_speed_m_day"] == pytest.approx(20.0, rel=0.1)
    assert a.stats["peak_offset_m"] == pytest.approx(a.stats["peak_speed_m_day"] * 12)
    assert a.stats["n_pairs"] == 6 and a.stats["pair_days"] == 12


def test_the_series_follows_a_speed_up_and_the_noise_floor_is_small_and_flat():
    a = analyze_goff(make_pairs([14.0, 16.0, 19.0, 24.0, 28.0, 30.0]), pixel_area_m2=PIX)
    values = [v for _, v in a.series]
    assert (
        values == sorted(values)
        and values[0] == pytest.approx(14.0, rel=0.15)
        and values[-1] == pytest.approx(30.0, rel=0.15)
    )
    assert len(a.reference_series) == 6 and all(v < 1.0 for _, v in a.reference_series)
    assert a.stats["noise_floor_m_day"] < 1.0
    assert a.series[0][0] == D0 + timedelta(days=6), "each point is dated at the middle of its pair"


def test_early_and_late_maps_show_the_seasonal_change():
    a = analyze_goff(make_pairs([14.0, 15.0, 16.0, 26.0, 28.0, 30.0]), pixel_area_m2=PIX)
    assert a.late[ROW, COL] > a.early[ROW, COL] * 1.5
    assert a.early[ROW, COL] == pytest.approx(15.0, rel=0.15) and a.late[ROW, COL] == pytest.approx(
        28.0, rel=0.15
    )


def test_fast_ice_area_counts_only_ground_above_the_threshold():
    a = analyze_goff(make_pairs([20.0] * 4), pixel_area_m2=PIX)
    yy, xx = np.mgrid[0:H, 0:W]
    expected = (glacier(20.0) > 10.0).sum() * PIX / 1e4
    assert a.stats["fast_ice_ha"] == pytest.approx(expected, rel=0.25)
    assert analyze_goff(make_pairs([5.0] * 4), pixel_area_m2=PIX).stats["fast_ice_ha"] == 0.0


def test_pairs_may_be_given_in_any_order_and_must_share_a_grid():
    pairs = make_pairs([14.0, 20.0, 30.0, 18.0])
    a = analyze_goff(list(reversed(pairs)), pixel_area_m2=PIX)
    assert [d for d, _ in a.series] == sorted(d for d, _ in a.series)
    odd = SpeedPair(D0, D0 + timedelta(days=12), np.zeros((5, 5), np.float32))
    with pytest.raises(ValueError, match="different grids"):
        analyze_goff(pairs + [odd], pixel_area_m2=PIX)
    with pytest.raises(ValueError, match="at least two"):
        analyze_goff(pairs[:1], pixel_area_m2=PIX)


def test_a_scene_with_nothing_usable_raises():
    p = make_pairs([20.0, 20.0])
    for x in p:
        x.speed[:] = np.nan
    with pytest.raises(ValueError, match="no pixel"):
        analyze_goff(p, pixel_area_m2=PIX)


def test_to_speed_combines_both_offsets_over_the_days_between_dates():
    along = np.full((2, 2), 30.0, np.float32)
    rng = np.full((2, 2), 40.0 * np.sin(np.radians(50)), np.float32)
    pair = OffsetPair(along, rng, np.ones((2, 2), np.float32), 0.0, 0.0, 80.0, 3413, 50.0)
    sp = to_speed(date(2026, 6, 23), date(2026, 7, 5), pair)
    assert sp.speed[0, 0] == pytest.approx(50.0 / 12, rel=1e-5)  # a 3-4-5 triangle, 50 m in 12 days
    assert sp.midpoint == date(2026, 6, 29)
    with pytest.raises(ValueError, match="not after"):
        to_speed(date(2026, 7, 5), date(2026, 6, 23), pair)
