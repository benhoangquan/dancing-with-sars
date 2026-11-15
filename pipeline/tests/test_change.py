import numpy as np
import pytest

from sarstory.change import area_ha, hv_drop_db, largest_patches, loss_mask
from sarstory.composite import sar_composite, to_db
from sarstory.palettes import BREWER, hex_to_rgb, ramp_rgba


def test_to_db():
    assert to_db(np.array([1.0]))[0] == pytest.approx(0.0)
    assert to_db(np.array([0.1]))[0] == pytest.approx(-10.0)
    assert np.isfinite(to_db(np.array([0.0, -1.0]))).all()
    assert np.isnan(to_db(np.array([np.nan]))[0])


def test_area_ha_takes_square_meters():
    mask = np.zeros((20, 20), bool)
    mask[:10, :10] = True  # 100 pixels of 400 m2 each is 4 ha
    assert area_ha(mask, 400.0) == pytest.approx(4.0)


def test_hv_drop_sign_means_loss():
    assert hv_drop_db(np.array([-12.0]), np.array([-18.0]))[0] == 6.0


def scene():
    before = np.full((40, 40), -12.0)
    after = before.copy()
    after[10:20, 10:20] -= 6.0  # 100 px patch loses 6 dB
    after[30:32, 30:32] -= 6.0  # 4 px patch loses 6 dB
    return before, after


def test_loss_mask_keeps_patches_over_min_pixels_and_drops_small_ones():
    before, after = scene()
    m = loss_mask(
        hv_drop_db(before, after), before, threshold_db=3, min_before_db=-16, min_pixels=20, open_iterations=0
    )
    assert m[10:20, 10:20].all() and not m[30:32, 30:32].any() and m.sum() == 100


def test_loss_mask_needs_forested_start():
    before, after = scene()
    m = loss_mask(
        hv_drop_db(before, after),
        before - 10,
        threshold_db=3,
        min_before_db=-16,
        min_pixels=1,
        open_iterations=0,
    )
    assert not m.any()


def test_loss_mask_ignores_nan_and_small_drops():
    before, after = scene()
    drop = hv_drop_db(before, after)
    drop[10:20, 10:20] = np.nan
    assert not loss_mask(drop, before, threshold_db=3, min_before_db=-16, min_pixels=1, open_iterations=0)[
        10:20, 10:20
    ].any()
    assert not loss_mask(
        np.full((5, 5), 2.0), np.full((5, 5), -12.0), threshold_db=3, min_before_db=-16, min_pixels=1
    ).any()


def test_largest_patches_orders_by_size():
    m = np.zeros((30, 30), bool)
    m[2:5, 2:5] = True
    m[10:20, 10:25] = True
    assert largest_patches(m, 2) == [(10, 10, 20, 25), (2, 2, 5, 5)]
    assert largest_patches(np.zeros((4, 4), bool), 1) == []


def test_sar_composite_scales_and_masks_nan():
    hh = np.array([[-10.0, np.nan]])
    hv = np.array([[-18.0, -18.0]])
    out = sar_composite(hh, hv)  # defaults: HH -20..0, HV -28..-8, ratio 0..15
    assert out.shape == (4, 1, 2) and out.dtype == np.uint8
    assert out[:, 0, 0].tolist() == [128, 128, 136, 255]  # ratio 8 dB -> 8/15
    assert out[:, 0, 1].tolist() == [0, 0, 0, 0]


def test_palettes():
    assert hex_to_rgb("#ff8000") == (255, 128, 0)
    rgba = ramp_rgba(np.array([[2.0, 10.0, np.nan, 99.0]]), "BrewerYlOrRd9", (2, 10))
    assert rgba[:3, 0, 0].tolist() == list(hex_to_rgb(BREWER["BrewerYlOrRd9"][0]))
    assert rgba[:3, 0, 1].tolist() == list(hex_to_rgb(BREWER["BrewerYlOrRd9"][-1]))
    assert rgba[:3, 0, 3].tolist() == rgba[:3, 0, 1].tolist(), (
        "values above the domain clip to the last color"
    )
    assert rgba[3, 0].tolist() == [255, 255, 0, 255]
