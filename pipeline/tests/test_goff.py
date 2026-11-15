import h5py
import numpy as np
import pytest
from rasterio.warp import transform_bounds

from sarstory.nisar.goff import GRID, RADAR_GRID, horizontal_offset_m, read_offsets, speed_m_per_day

EPSG, DX, SHAPE = 3413, 80.0, (700, 750)
X_FIRST, Y_FIRST = -300040.0, -2200040.0


def fetch_of(path):
    data = path.read_bytes()
    return lambda offset, size: data[offset : offset + size]


def make_goff(path, *, along=12.0, rng=5.0, snr=20.0, incidence=38.0):
    rows, cols = SHAPE
    xs, ys = X_FIRST + DX * np.arange(cols), Y_FIRST - DX * np.arange(rows)
    kw = {"chunks": (512, 512), "compression": "gzip", "compression_opts": 1, "shuffle": True}
    with h5py.File(path, "w") as f:
        for layer in (1, 2, 3):
            g = f.create_group(f"{GRID}/layer{layer}")
            g.create_dataset(
                "alongTrackOffset", data=np.full(SHAPE, along * (1 if layer < 3 else 0.2), "f4"), **kw
            )
            g.create_dataset("slantRangeOffset", data=np.full(SHAPE, rng, "f4"), **kw)
            g.create_dataset("snr", data=np.full(SHAPE, snr, "f4"), **kw)
            g.create_dataset("xCoordinates", data=xs)
            g.create_dataset("yCoordinates", data=ys)
            g.create_dataset("xCoordinateSpacing", data=DX)
            g.create_dataset("yCoordinateSpacing", data=-DX)
            g.create_dataset("projection", data=np.uint32(EPSG))
        rg = f.create_group(RADAR_GRID)
        rg.create_dataset("heightAboveEllipsoid", data=np.array([-100.0, 500.0, 1000.0]))
        rg.create_dataset("xCoordinates", data=np.linspace(xs[0], xs[-1], 20))
        rg.create_dataset("yCoordinates", data=np.linspace(ys[0], ys[-1], 20))
        cube = np.zeros((3, 20, 20), "f4")
        cube[0], cube[1], cube[2] = incidence - 5, incidence, incidence + 5
        rg.create_dataset("incidenceAngle", data=cube)
    return xs, ys


def box(x0, y0, x1, y1):
    return transform_bounds(f"EPSG:{EPSG}", "EPSG:4326", x0, y0, x1, y1)


def test_horizontal_offset_converts_slant_range_with_the_incidence_angle():
    # a pure range offset of 10 m slant at 30 degrees incidence is 20 m on the ground
    out = horizontal_offset_m(np.array([0.0], "f4"), np.array([10.0], "f4"), 30.0)
    assert out[0] == pytest.approx(20.0, rel=1e-5)
    assert horizontal_offset_m(np.array([30.0], "f4"), np.array([0.0], "f4"), 38.0)[0] == pytest.approx(30.0)
    assert horizontal_offset_m(np.array([30.0], "f4"), np.array([40.0 * np.sin(np.radians(50))], "f4"), 50.0)[
        0
    ] == pytest.approx(50.0, rel=1e-5)


def test_speed_is_offset_over_days():
    assert speed_m_per_day(np.array([120.0], "f4"), 12.0)[0] == pytest.approx(10.0)


def test_reads_the_window_incidence_and_requested_layer(tmp_path):
    path = tmp_path / "g.h5"
    xs, ys = make_goff(path, along=12.0, rng=5.0, incidence=38.0)
    utm = (xs[100], ys[500], xs[400], ys[200])
    with h5py.File(path) as f:
        pair = read_offsets(f, box(*utm), fetch_of(path), threads=2)
        coarse = read_offsets(f, box(*utm), fetch_of(path), layer=3, threads=2)
    assert pair is not None and pair.epsg == EPSG and pair.res == DX
    assert np.allclose(pair.along_m[np.isfinite(pair.along_m)], 12.0) and np.allclose(
        pair.range_m[np.isfinite(pair.range_m)], 5.0
    )
    assert pair.incidence_deg == pytest.approx(38.0), "the cube is cut at the height nearest 500 m"
    assert np.nanmedian(coarse.along_m) == pytest.approx(2.4), "layer 3 is a different, coarser layer"


def test_low_snr_samples_are_dropped(tmp_path):
    path = tmp_path / "low.h5"
    xs, ys = make_goff(path, snr=2.0)
    with h5py.File(path) as f:
        pair = read_offsets(f, box(xs[100], ys[500], xs[400], ys[200]), fetch_of(path), threads=2)
    assert np.isnan(pair.along_m).all() and np.isnan(pair.range_m).all()


def test_returns_none_when_the_granule_does_not_reach_the_study_area(tmp_path):
    path = tmp_path / "far.h5"
    make_goff(path)
    with h5py.File(path) as f:
        assert (
            read_offsets(f, box(500000.0, -1000000.0, 520000.0, -980000.0), fetch_of(path), threads=2) is None
        )
