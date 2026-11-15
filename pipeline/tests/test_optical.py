import numpy as np
import pytest
from affine import Affine

from sarstory import optical as O


def test_fmask_flags_cloud_adjacent_shadow_and_snow_but_not_water_or_aerosol():
    clear = np.array(
        [0b00000000, 0b01000000, 0b10000000, 0b00100000, 0b00000001], np.uint8
    )  # clear, aerosol bits, water
    bad = np.array(
        [0b00000010, 0b00000100, 0b00001000, 0b00010000], np.uint8
    )  # cloud, adjacent, shadow, snow
    assert O.clear_mask(clear[:4]).all()
    assert not O.clear_mask(bad).any()
    assert O.clear_mask(np.array([0b00100000], np.uint8))[0], "water (bit 5) is usable"


def test_blocked_share_counts_only_pixels_that_have_data():
    fmask = np.array(
        [[0, 2], [4, 255]], np.uint8
    )  # clear, cloud, adjacent... 4 is bit 2 (adjacent); 255 has no data
    valid = np.array([[True, True], [True, False]])
    assert O.blocked_share(fmask, valid) == pytest.approx(2 / 3)
    assert np.isnan(O.blocked_share(fmask, np.zeros((2, 2), bool)))


def test_reflectance_scaling_and_nodata():
    raw = np.array([[500, 2500, O.NODATA]], np.int16)
    out = O.to_reflectance(raw)
    assert out[0, 0] == pytest.approx(0.05) and out[0, 1] == pytest.approx(0.25) and np.isnan(out[0, 2])


def test_median_composite_ignores_nan_and_keeps_gaps_where_no_scene_has_data():
    a = np.full((3, 2, 2), 0.10, np.float32)
    b = np.full((3, 2, 2), 0.30, np.float32)
    c = np.full((3, 2, 2), 0.20, np.float32)
    b[:, 0, 0] = np.nan
    c[:, 0, 0] = np.nan
    a[:, 1, 1] = np.nan
    b[:, 1, 1] = np.nan
    c[:, 1, 1] = np.nan
    out = O.median_composite([a, b, c])
    assert out[0, 0, 0] == pytest.approx(0.10)  # one scene left
    assert out[0, 0, 1] == pytest.approx(0.20)  # median of three
    assert np.isnan(out[:, 1, 1]).all()


def test_stretch_is_fixed_monotone_and_transparent_where_missing():
    rgb = np.zeros((3, 1, 4), np.float32)
    rgb[:, 0, 0] = 0.0
    rgb[:, 0, 1] = 0.05
    rgb[:, 0, 2] = O.WHITE_POINT
    rgb[:, 0, 3] = np.nan
    out = O.stretch_rgba(rgb)
    assert out.dtype == np.uint8 and out.shape == (4, 1, 4)
    assert out[:3, 0, 0].tolist() == [0, 0, 0] and out[:3, 0, 2].tolist() == [255, 255, 255]
    assert out[0, 0, 0] < out[0, 0, 1] < out[0, 0, 2]
    assert out[3, 0].tolist() == [255, 255, 255, 0]
    assert O.stretch_rgba(rgb * 2)[0, 0, 2] == 255, "bright values clip, they do not wrap"


def test_lattice_exposes_its_crs():
    lat = O.Lattice(Affine(60, 0, 0, 0, -60, 0), 10, 10, 32720)
    assert lat.crs == "EPSG:32720"
