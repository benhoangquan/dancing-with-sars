from pathlib import Path

import h5py
import numpy as np
import pytest

from sarstory.nisar.hdf5 import decode_chunk, read_window

SHAPE, CHUNKS = (1300, 1700), (512, 512)  # edge chunks are partial, as in a real granule


def file_fetch(path: Path):
    data = path.read_bytes()
    return lambda offset, size: data[offset : offset + size]


@pytest.fixture(scope="module")
def sample(tmp_path_factory):
    rng = np.random.default_rng(7)
    path = tmp_path_factory.mktemp("h5") / "sample.h5"
    arrays = {
        "float_shuffle_gzip": rng.random(SHAPE, dtype=np.float32),
        "uint8_gzip": rng.integers(0, 255, SHAPE, dtype=np.uint8),
        "float_plain_gzip": rng.random(SHAPE, dtype=np.float32),
        "float_fletcher": rng.random(SHAPE, dtype=np.float32),
    }
    arrays["float_shuffle_gzip"][100:140, 200:260] = np.nan
    with h5py.File(path, "w") as f:
        f.create_dataset(
            "float_shuffle_gzip",
            data=arrays["float_shuffle_gzip"],
            chunks=CHUNKS,
            compression="gzip",
            compression_opts=1,
            shuffle=True,
        )
        f.create_dataset("uint8_gzip", data=arrays["uint8_gzip"], chunks=CHUNKS, compression="gzip")
        f.create_dataset(
            "float_plain_gzip",
            data=arrays["float_plain_gzip"],
            chunks=CHUNKS,
            compression="gzip",
            shuffle=False,
        )
        f.create_dataset(
            "float_fletcher",
            data=arrays["float_fletcher"],
            chunks=CHUNKS,
            compression="gzip",
            shuffle=True,
            fletcher32=True,
        )
        f.create_dataset(
            "unwritten", shape=SHAPE, dtype="f4", chunks=CHUNKS, fillvalue=np.nan, compression="gzip"
        )
        f["unwritten"][0:512, 0:512] = 1.0  # only one chunk is ever written
    return path, arrays


WINDOWS = [
    (0, 1300, 0, 1700),
    (130, 900, 70, 1400),
    (513, 1024, 512, 1024),
    (1290, 1300, 1690, 1700),
    (511, 513, 511, 513),
]


@pytest.mark.parametrize("name", ["float_shuffle_gzip", "uint8_gzip", "float_plain_gzip", "float_fletcher"])
@pytest.mark.parametrize("window", WINDOWS)
def test_windows_match_what_h5py_returns(sample, name, window):
    path, arrays = sample
    r0, r1, c0, c1 = window
    with h5py.File(path, "r") as f:
        got = read_window(f[name], r0, r1, c0, c1, file_fetch(path), threads=4)
        assert np.array_equal(got, f[name][r0:r1, c0:c1], equal_nan=True)
    assert np.array_equal(got, arrays[name][r0:r1, c0:c1], equal_nan=True)


def test_unwritten_chunks_come_back_as_the_fill_value(sample):
    path, _ = sample
    with h5py.File(path, "r") as f:
        got = read_window(f["unwritten"], 400, 700, 400, 700, file_fetch(path), threads=2)
    assert (got[:112, :112] == 1.0).all() and np.isnan(got[200:, 200:]).all()


def test_only_the_needed_chunks_are_fetched(sample):
    path, _ = sample
    calls = []
    data = path.read_bytes()

    def counting(offset, size):
        calls.append((offset, size))
        return data[offset : offset + size]

    with h5py.File(path, "r") as f:
        read_window(f["float_shuffle_gzip"], 600, 700, 600, 700, counting, threads=2)
    assert len(calls) == 1, "a window inside one chunk needs exactly one request"


def test_rejects_unsupported_layouts(sample, tmp_path):
    path, _ = sample
    with h5py.File(tmp_path / "x.h5", "w") as f:
        f.create_dataset("contiguous", data=np.zeros((4, 4)))
        f.create_dataset("lzf", data=np.zeros((600, 600), "f4"), chunks=(256, 256), compression="lzf")
    with h5py.File(tmp_path / "x.h5", "r") as f:
        with pytest.raises(ValueError, match="chunked"):
            read_window(f["contiguous"], 0, 2, 0, 2, lambda o, s: b"")
        with pytest.raises(NotImplementedError, match="lzf"):
            decode_chunk(b"", f["lzf"])
