from datetime import date, timedelta

import numpy as np
import pytest
from affine import Affine

from sarstory.nisar.analysis import Stack, analyze, mean_db, median_db, mosaic_stack
from sarstory.nisar.gcov import Tile

DAYS = [date(2026, 6, 25) + timedelta(days=12 * i) for i in range(9)]  # Jun 25 .. Sep 29
BEFORE, AFTER = ("2026-06-17", "2026-07-11"), ("2026-09-09", "2026-10-03")
H, W, RES = 60, 80, 60.0
FOREST_HV = 10 ** (-13.5 / 10)
PATCH = (slice(20, 40), slice(30, 55))  # 500 blocks of 60 m, 180 ha: the clearing


def db_to_lin(db):
    return 10 ** (np.asarray(db) / 10)


def synthetic_stack(drop_db=6.0, noise=0.0, seed=1):
    rng = np.random.default_rng(seed)
    hv = np.full((len(DAYS), H, W), FOREST_HV, np.float32)
    hh = np.full_like(hv, db_to_lin(-8.0))
    for i, day in enumerate(DAYS):
        if day >= date(2026, 8, 1):  # clearing happens between the windows
            hv[i][PATCH] = db_to_lin(-13.5 - drop_db)
            hh[i][PATCH] = db_to_lin(-8.0 - drop_db / 2)
    if noise:
        hv = hv * np.exp(rng.normal(0, noise, hv.shape)).astype(np.float32)
    return Stack(list(DAYS), hh, hv, Affine(RES, 0, 400020.0, 0, -RES, 8900040.0), 32720, RES)


def run(stack, **over):
    kw = dict(before=BEFORE, after=AFTER, max_dates=8, drop_threshold_db=3.0, min_before_db=-16.0, mmu_ha=1.0)
    return analyze(stack, **{**kw, **over})


def test_the_mask_is_the_cleared_patch_and_the_stats_follow():
    a = run(synthetic_stack())
    inside = np.zeros((H, W), bool)
    inside[PATCH] = True
    assert not (a.mask & ~inside).any(), "nothing outside the clearing is flagged"
    # The binary open rounds the four corners of a rectangle; everything else is kept.
    assert a.mask[PATCH].sum() >= 496
    assert a.stats["area_ha"] == pytest.approx(a.mask.sum() * RES**2 / 10_000)
    assert a.stats["area_ha"] == pytest.approx(180.0, rel=0.02)
    assert a.stats["hv_before_db"] == pytest.approx(-13.5, abs=0.01)
    assert a.stats["hv_after_db"] == pytest.approx(-19.5, abs=0.01)
    assert a.stats["hv_drop_db"] == pytest.approx(6.0, abs=0.01)


def test_series_falls_after_the_clearing_while_the_reference_stays_flat():
    a = run(synthetic_stack())
    values = dict(a.series)
    assert values[DAYS[0]] == pytest.approx(-13.5, abs=0.01) and values[DAYS[-1]] == pytest.approx(
        -19.5, abs=0.01
    )
    assert a.stats["n_dates"] == len(DAYS)
    assert a.reference.sum() > 100 and not (a.reference & a.mask).any()
    assert all(abs(v + 13.5) < 0.01 for _, v in a.reference_series)


def test_area_series_is_zero_before_the_loss_then_the_patch_and_never_falls():
    a = run(synthetic_stack())
    areas = dict(a.area_series)
    assert areas[DAYS[0]] == 0.0 and areas[DAYS[1]] == 0.0
    assert areas[DAYS[-1]] == pytest.approx(a.stats["area_ha"], rel=0.02)
    values = [v for _, v in a.area_series]
    assert values == sorted(values)


def test_windows_pick_the_right_dates_and_respect_max_dates():
    a = run(synthetic_stack(), max_dates=1)
    assert a.before_days == [DAYS[0]] and a.after_days == [DAYS[-1]] or len(a.after_days) == 1
    a = run(synthetic_stack())
    assert a.before_days == DAYS[:2] and a.after_days == [d for d in DAYS if d >= date(2026, 9, 9)]


def test_a_drop_below_the_threshold_gives_an_empty_mask():
    a = run(synthetic_stack(drop_db=2.0))
    assert not a.mask.any() and a.stats["area_ha"] == 0.0 and np.isnan(a.stats["hv_drop_db"])


def test_ground_that_was_never_forest_is_not_counted_as_loss():
    stack = synthetic_stack()
    stack.hv[:, :, :10] = db_to_lin(-21.0)  # bare ground from the start
    stack.hv[5:, :20, :10] = db_to_lin(-30.0)  # and it gets darker later
    a = run(stack)
    assert not a.mask[:, :10].any()


def test_speckle_noise_does_not_turn_into_clearing():
    a = run(synthetic_stack(noise=0.25), min_before_db=-18.0)
    assert a.mask[PATCH].mean() > 0.9
    outside = a.mask.copy()
    outside[PATCH] = False
    assert outside.sum() < 0.01 * H * W


def test_missing_windows_raise_a_clear_error():
    with pytest.raises(ValueError, match="both windows"):
        run(synthetic_stack(), after=("2027-01-01", "2027-02-01"))


def test_mean_and_median_in_db():
    assert mean_db(np.array([0.1, 0.1, np.nan])) == pytest.approx(-10.0)
    assert np.isnan(mean_db(np.array([np.nan])))
    arr = np.array([[[0.1]], [[0.01]], [[1.0]]], np.float32)
    assert median_db(arr)[0, 0] == pytest.approx(-10.0)
    assert np.isnan(median_db(np.full((2, 1, 1), np.nan, np.float32))[0, 0])


def tile(x0, y0, value, shape=(10, 10)):
    a = np.full(shape, value, np.float32)
    return Tile(a, a.copy(), x0, y0, RES, 32720)


def test_frames_of_one_acquisition_are_mosaicked_onto_a_shared_lattice():
    north = tile(400020.0, 8900040.0, 1.0)
    south = tile(400020.0, 8900040.0 - 10 * RES, 2.0)
    other_day = tile(400020.0, 8900040.0, 3.0)
    s = mosaic_stack({DAYS[0]: [north, south], DAYS[1]: [other_day]})
    assert s.hh.shape == (2, 20, 10)
    assert (s.hh[0, :10] == 1.0).all() and (s.hh[0, 10:] == 2.0).all()
    assert (s.hh[1, :10] == 3.0).all() and np.isnan(s.hh[1, 10:]).all()
    assert s.transform.c == 400020.0 and s.transform.f == 8900040.0


def test_overlapping_frames_fill_gaps_without_overwriting_valid_data():
    a = tile(400020.0, 8900040.0, 1.0)
    b = tile(400020.0, 8900040.0, 9.0)
    a.hh[0, 0] = np.nan
    s = mosaic_stack({DAYS[0]: [a, b]})
    assert s.hh[0, 0, 0] == 9.0 and s.hh[0, 5, 5] == 1.0


def test_tiles_off_the_lattice_are_rejected():
    with pytest.raises(ValueError, match="lattice"):
        mosaic_stack({DAYS[0]: [tile(400020.0, 8900040.0, 1.0), tile(400050.0, 8900040.0, 1.0)]})
