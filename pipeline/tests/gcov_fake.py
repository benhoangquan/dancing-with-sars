"""A small stand-in for a NISAR GCOV granule with the real layout and values that have a closed form."""

from pathlib import Path

import h5py
import numpy as np

EPSG, DX = 32720, 20.0
X_FIRST, Y_FIRST = 280090.0, 8939510.0  # pixel centers, as in the real granule (10 m off the 20 m grid)
SHAPE = (1500, 1800)


def hh_of_x(x):
    return 0.05 + 1e-6 * (x - X_FIRST)  # linear in easting


def hv_of_y(y):
    return 0.01 + 1e-7 * (Y_FIRST - y)  # linear in northing


def make_gcov(path: Path, *, shape=SHAPE, mask_stripe=None) -> dict:
    rows, cols = shape
    xs = X_FIRST + DX * np.arange(cols)
    ys = Y_FIRST - DX * np.arange(rows)
    hh = np.tile(hh_of_x(xs), (rows, 1)).astype("f4")
    hv = np.tile(hv_of_y(ys)[:, None], (1, cols)).astype("f4")
    mask = np.ones(shape, "u1")
    if mask_stripe:
        mask[:, mask_stripe[0] : mask_stripe[1]] = 255
    with h5py.File(path, "w") as f:
        fa = f.create_group("science/LSAR/GCOV/grids/frequencyA")
        kw = {"chunks": (512, 512), "compression": "gzip", "compression_opts": 1, "shuffle": True}
        fa.create_dataset("HHHH", data=hh, fillvalue=np.nan, **kw)
        fa.create_dataset("HVHV", data=hv, fillvalue=np.nan, **kw)
        fa.create_dataset("mask", data=mask, fillvalue=255, **kw)
        fa.create_dataset("xCoordinates", data=xs)
        fa.create_dataset("yCoordinates", data=ys)
        fa.create_dataset("xCoordinateSpacing", data=DX)
        fa.create_dataset("yCoordinateSpacing", data=-DX)
        proj = fa.create_dataset("projection", data=np.uint32(EPSG))
        proj.attrs["epsg_code"] = EPSG
    return {"xs": xs, "ys": ys}
