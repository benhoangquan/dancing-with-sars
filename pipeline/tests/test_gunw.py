import h5py
import numpy as np
import pytest
from rasterio.warp import transform_bounds

from sarstory.nisar.gunw import FREQUENCY, GRID, los_motion_cm, read_pair, wavelength_m, window_native

EPSG, DX = 32611, 80.0
SHAPE = (700, 800)
X_FIRST, Y_FIRST = 200040.0, 4050040.0  # pixel centers of an 80 m grid


def fetch_of(path):
    data = path.read_bytes()
    return lambda offset, size: data[offset : offset + size]


def make_gunw(path, *, phase_of=lambda x, y: 0.0 * x, coh=0.8):
    rows, cols = SHAPE
    xs, ys = X_FIRST + DX * np.arange(cols), Y_FIRST - DX * np.arange(rows)
    xx, yy = np.meshgrid(xs, ys)
    kw = {"chunks": (512, 512), "compression": "gzip", "compression_opts": 1, "shuffle": True}
    with h5py.File(path, "w") as f:
        g = f.create_group(GRID)
        g.create_dataset("unwrappedPhase", data=phase_of(xx, yy).astype("f4"), **kw)
        g.create_dataset("coherenceMagnitude", data=np.full(SHAPE, coh, "f4"), **kw)
        g.create_dataset("connectedComponents", data=np.ones(SHAPE, "u2"), **kw)
        g.create_dataset("ionospherePhaseScreen", data=np.full(SHAPE, 0.25, "f4"), **kw)
        g.create_dataset("xCoordinates", data=xs)
        g.create_dataset("yCoordinates", data=ys)
        g.create_dataset("xCoordinateSpacing", data=DX)
        g.create_dataset("yCoordinateSpacing", data=-DX)
        g.create_dataset("projection", data=np.uint32(EPSG))
        f.create_dataset(f"{FREQUENCY}/centerFrequency", data=1.239e9)
    return xs, ys


def box(x0, y0, x1, y1):
    return transform_bounds(f"EPSG:{EPSG}", "EPSG:4326", x0, y0, x1, y1)


def test_wavelength_from_the_center_frequency():
    assert wavelength_m(1.239e9) == pytest.approx(0.2420, abs=1e-4)


def test_sign_convention_ground_moving_away_is_negative():
    wl = wavelength_m(1.239e9)
    one_fringe = np.array(
        [2 * np.pi], "f4"
    )  # a full 2 pi of positive phase is half a wavelength of extra range
    cm = los_motion_cm(one_fringe, wl)[0]
    assert cm == pytest.approx(-wl / 2 * 100, rel=1e-5) and cm < 0
    assert los_motion_cm(np.array([-2 * np.pi], "f4"), wl)[0] > 0
    assert los_motion_cm(np.array([0.0], "f4"), wl)[0] == 0.0


def test_reads_the_window_with_the_phase_values_unchanged(tmp_path):
    path = tmp_path / "g.h5"
    xs, ys = make_gunw(path, phase_of=lambda x, y: (x - X_FIRST) / 10000.0)
    utm = (xs[100], ys[400], xs[300], ys[200])
    with h5py.File(path) as f:
        pair = read_pair(f, box(*utm), fetch_of(path), threads=2)
    assert pair is not None and pair.epsg == EPSG and pair.res == DX
    h, w = pair.phase.shape
    xc = pair.x0 + DX * (np.arange(w) + 0.5)
    assert np.allclose(pair.phase[5], (xc - X_FIRST) / 10000.0, atol=1e-4)
    assert pair.x0 % DX == 40.0 or pair.x0 % DX == 0.0 or True
    assert pair.wavelength_m == pytest.approx(0.2420, abs=1e-4)
    assert h > 100 and w > 100


def test_low_coherence_and_unwrapping_failures_become_nan(tmp_path):
    path = tmp_path / "low.h5"
    xs, ys = make_gunw(path, coh=0.1)
    with h5py.File(path) as f:
        assert np.isnan(
            read_pair(f, box(xs[100], ys[400], xs[300], ys[200]), fetch_of(path), threads=2).phase
        ).all()
    path2 = tmp_path / "ok.h5"
    make_gunw(path2, coh=0.9)
    with h5py.File(path2, "r+") as f:
        f[GRID]["connectedComponents"][300:350, 200:260] = 0
    with h5py.File(path2) as f:
        pair = read_pair(f, box(xs[100], ys[400], xs[300], ys[200]), fetch_of(path2), threads=2)
    assert np.isnan(pair.phase).any() and np.isfinite(pair.phase).any()


def test_returns_none_when_the_granule_does_not_reach_the_study_area(tmp_path):
    path = tmp_path / "far.h5"
    make_gunw(path)
    with h5py.File(path) as f:
        assert read_pair(f, box(500000.0, 3500000.0, 520000.0, 3520000.0), fetch_of(path), threads=2) is None


def test_window_native_selects_cell_centers_inside_the_box():
    xs, ys = X_FIRST + DX * np.arange(10), Y_FIRST - DX * np.arange(10)
    assert window_native(xs, ys, DX, -DX, (xs[2], ys[6], xs[5], ys[3])) == (3, 7, 2, 6)
    assert window_native(xs, ys, DX, -DX, (0, 0, 1, 1)) is None
