import h5py
import numpy as np
import pytest
from gcov_fake import DX, EPSG, SHAPE, hh_of_x, hv_of_y, make_gcov
from rasterio.warp import transform_bounds

from sarstory.nisar.gcov import GRID, block_mean, read_tile, window_indices


def fetch_of(path):
    data = path.read_bytes()
    return lambda offset, size: data[offset : offset + size]


def lonlat_box(x0, y0, x1, y1):
    return transform_bounds(f"EPSG:{EPSG}", "EPSG:4326", x0, y0, x1, y1)


@pytest.fixture(scope="module")
def granule(tmp_path_factory):
    path = tmp_path_factory.mktemp("g") / "g.h5"
    make_gcov(path)
    return path


def test_grid_path_and_datasets_match_the_real_product(granule):
    with h5py.File(granule) as f:
        fa = f[GRID]
        for name in (
            "HHHH",
            "HVHV",
            "mask",
            "xCoordinates",
            "yCoordinates",
            "xCoordinateSpacing",
            "yCoordinateSpacing",
            "projection",
        ):
            assert name in fa
        assert fa["projection"].attrs["epsg_code"] == EPSG


def test_tile_sits_on_the_lattice_covers_the_request_and_has_the_closed_form_values(granule):
    utm = (290000.0, 8915000.0, 310000.0, 8935000.0)  # inside the 36 x 30 km fake granule
    with h5py.File(granule) as f:
        tile = read_tile(f, lonlat_box(*utm), fetch_of(granule), threads=4)
    assert tile is not None and tile.epsg == EPSG and tile.res == 60.0
    assert tile.x0 % 60 == 0 and tile.y0 % 60 == 0
    h, w = tile.hh.shape
    assert (
        tile.x0 <= utm[0] and tile.x0 + w * 60 >= utm[2] and tile.y0 >= utm[3] and tile.y0 - h * 60 <= utm[1]
    )
    xc = tile.x0 + 60 * (np.arange(w) + 0.5)  # block centers
    yc = tile.y0 - 60 * (np.arange(h) + 0.5)
    assert np.allclose(tile.hh, np.tile(hh_of_x(xc), (h, 1)), rtol=1e-5)
    assert np.allclose(tile.hv, np.tile(hv_of_y(yc)[:, None], (1, w)), rtol=1e-5)


def test_masked_samples_become_nan_and_blocks_need_half_valid_samples(tmp_path):
    path = tmp_path / "m.h5"
    make_gcov(path, mask_stripe=(600, 900))  # columns 600..899 are outside the acquisition
    x_stripe = 280090.0 + DX * 600 - DX / 2
    utm = (x_stripe - 6000, 8915000.0, x_stripe + 9000, 8935000.0)
    with h5py.File(path) as f:
        tile = read_tile(f, lonlat_box(*utm), fetch_of(path), threads=4)
    xc = tile.x0 + 60 * (np.arange(tile.hh.shape[1]) + 0.5)
    inside = (xc > x_stripe + 30) & (xc < x_stripe + 300 * DX / 1 - 90)
    outside = (xc < x_stripe - 60) | (xc > x_stripe + 300 * DX + 60)
    assert np.isnan(tile.hh[:, inside]).all() and np.isfinite(tile.hh[:, outside]).all()


def test_returns_none_when_the_granule_does_not_reach_the_study_area(granule):
    far = lonlat_box(100000.0, 8000000.0, 130000.0, 8030000.0)
    with h5py.File(granule) as f:
        assert read_tile(f, far, fetch_of(granule), threads=2) is None


def test_a_granule_whose_first_edge_is_off_the_lattice_starts_at_the_first_aligned_block():
    # West edges 280100, 280120, 280140: only 280140 is a multiple of 60 m, two columns in.
    # North edges 8939500, 8939480, 8939460: only 8939460 is, two rows in.
    # Edges are multiples of 20 m, as in real GCOV.
    xs = 280110.0 + DX * np.arange(600)
    ys = 8939490.0 - DX * np.arange(600)
    idx = window_indices(xs, ys, DX, -DX, (xs[0] - 4000, ys[-1] - 100, xs[-1] + 4000, ys[0] + 100), 60.0)
    assert idx is not None
    r0, r1, c0, c1 = idx
    assert c0 == 2 and (xs[c0] - DX / 2) % 60 == 0
    assert r0 == 2 and (ys[r0] + DX / 2) % 60 == 0
    assert (c1 - c0) % 3 == 0 and (r1 - r0) % 3 == 0 and c1 <= 600 and r1 <= 600


def test_a_grid_that_cannot_line_up_with_the_lattice_gives_no_window():
    xs = 280110.0 + DX * np.arange(600)
    ys = 8939500.0 - DX * np.arange(600)  # north edges 10 m off a multiple of 20: never on a 60 m lattice
    assert window_indices(xs, ys, DX, -DX, (xs[0], ys[-1], xs[-1], ys[0]), 60.0) is None


def test_block_mean_ignores_nan_and_drops_mostly_empty_blocks():
    a = np.full((6, 6), 2.0, "f4")
    a[0:3, 0:3] = np.nan  # an empty block
    a[3:6, 3:6] = np.nan
    a[3, 3:6] = 6.0  # 3 of 9 valid: below the half threshold
    a[0, 3] = np.nan  # 8 of 9 valid, rest 2.0
    out = block_mean(a, 3)
    assert np.isnan(out[0, 0]) and np.isnan(out[1, 1])
    assert out[0, 1] == pytest.approx(2.0) and out[1, 0] == pytest.approx(2.0)
    assert block_mean(np.ones((4, 4), "f4"), 3).shape == (1, 1)


def test_fake_granule_shape_is_what_the_helpers_assume():
    assert SHAPE == (1500, 1800) and DX == 20.0
