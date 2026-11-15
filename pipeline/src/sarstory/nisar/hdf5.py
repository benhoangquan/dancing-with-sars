"""Read a window of a chunked HDF5 dataset by fetching only the byte ranges of the chunks under it.

NISAR granules are 1.6 to 7 GB HDF5 files with 512 x 512 gzip chunks. h5py over HTTPS asks for chunks one
at a time (31 to 129 s for a study-area window). Here the chunk index is read through h5py, then every
needed chunk is fetched in parallel as a plain byte range and decoded (gunzip, then unshuffle). On a real
granule this took 5 to 7 s and matched h5py bit for bit.
"""

from __future__ import annotations

import zlib
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

import h5py
import numpy as np

Fetch = Callable[[int, int], bytes]  # (byte offset, size) -> bytes


def decode_chunk(raw: bytes, ds: h5py.Dataset) -> np.ndarray:
    """One stored chunk to an array of the dataset's chunk shape. Handles gzip, shuffle and fletcher32."""
    if ds.compression not in (None, "gzip"):
        raise NotImplementedError(f"{ds.name}: compression {ds.compression!r} is not supported")
    if ds.fletcher32:
        raw = raw[:-4]  # trailing checksum
    data = zlib.decompress(raw) if ds.compression == "gzip" else raw
    if ds.shuffle:
        item = ds.dtype.itemsize
        data = np.frombuffer(data, np.uint8).reshape(item, -1).T.tobytes()
    return np.frombuffer(data, ds.dtype).reshape(ds.chunks)


def read_window(
    ds: h5py.Dataset, r0: int, r1: int, c0: int, c1: int, fetch: Fetch, *, threads: int = 16
) -> np.ndarray:
    """Rows r0:r1 and columns c0:c1 of a 2-D chunked dataset. Unwritten chunks come back as the fill value."""
    if ds.ndim != 2 or ds.chunks is None:
        raise ValueError(f"{ds.name}: need a chunked 2-D dataset")
    cr, cc = ds.chunks
    fill = ds.fillvalue if ds.fillvalue is not None else 0
    out = np.full((r1 - r0, c1 - c0), fill, ds.dtype)
    coords = [(r, c) for r in range(r0 // cr * cr, r1, cr) for c in range(c0 // cc * cc, c1, cc)]
    infos = {xy: ds.id.get_chunk_info_by_coord(xy) for xy in coords}

    def work(xy: tuple[int, int]) -> tuple[tuple[int, int], np.ndarray | None]:
        info = infos[xy]
        if info.byte_offset is None or not info.size:
            return xy, None
        return xy, decode_chunk(fetch(info.byte_offset, info.size), ds)

    with ThreadPoolExecutor(threads) as pool:
        for (r, c), chunk in pool.map(work, coords):
            if chunk is None:
                continue
            rs, re = max(r, r0), min(r + cr, r1)
            cs, ce = max(c, c0), min(c + cc, c1)
            out[rs - r0 : re - r0, cs - c0 : ce - c0] = chunk[rs - r : re - r, cs - c : ce - c]
    return out
