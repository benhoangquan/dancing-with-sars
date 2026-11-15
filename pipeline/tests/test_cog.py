import json

import numpy as np
import pytest
import rasterio
from PIL import Image
from rasterio.transform import from_bounds

from sarstory.cog import cog_info, sha256_file, write_cog, write_layer
from sarstory.manifest import schema

BBOX = (-63.80, -10.40, -62.90, -9.70)
W, H = 320, 250
TR = from_bounds(*BBOX, W, H)


def test_rgba_cog_is_web_ready(tmp_path):
    data = np.zeros((4, H, W), np.uint8)
    data[0], data[1], data[2], data[3] = 200, 100, 50, 255
    data[3, :40] = 0  # transparent strip along the north edge
    out = tmp_path / "rgba.tif"
    write_cog(out, data, TR, "EPSG:4326")
    info = cog_info(out)
    assert info["crs"] == "EPSG:3857"
    assert info["count"] == 4 and info["dtype"] == "uint8"
    assert info["colorinterp"][-1] == "alpha"
    assert set(info["block_shapes"]) == {(256, 256)}
    assert info["overviews"], "COG needs overviews"
    with rasterio.open(out) as ds:
        px = ds.read()
    opaque = px[3] == 255
    assert opaque.any() and (~opaque).any(), "alpha must carry both covered and uncovered pixels"
    for band, value in enumerate((200, 100, 50)):
        assert np.unique(px[band][opaque]).tolist() == [value]


def test_float_cog_keeps_values_and_nan(tmp_path):
    data = np.full((H, W), 3.5, np.float32)
    data[:40] = np.nan
    out = tmp_path / "ramp.tif"
    write_cog(out, data, TR, "EPSG:4326")
    info = cog_info(out)
    assert info["crs"] == "EPSG:3857" and info["dtype"] == "float32" and np.isnan(info["nodata"])
    assert set(info["block_shapes"]) == {(256, 256)} and info["overviews"]
    with rasterio.open(out) as ds:
        px = ds.read(1)
    finite = px[np.isfinite(px)]
    assert finite.size and np.allclose(finite, 3.5, atol=1e-5)
    assert np.isnan(px).any()


def test_bounds_cover_the_input_bbox(tmp_path):
    data = np.full((H, W), 1.0, np.float32)
    out = tmp_path / "b.tif"
    write_cog(out, data, TR, "EPSG:4326")
    west, south, east, north = cog_info(out)["bounds_lonlat"]
    assert west <= BBOX[0] and south <= BBOX[1] and east >= BBOX[2] and north >= BBOX[3]


def test_rejects_wrong_dtype_or_shape(tmp_path):
    with pytest.raises(ValueError):
        write_cog(tmp_path / "a.tif", np.zeros((3, H, W), np.uint8), TR, "EPSG:4326")
    with pytest.raises(ValueError):
        write_cog(tmp_path / "b.tif", np.zeros((H, W), np.float64), TR, "EPSG:4326")


def test_write_layer_entry_matches_files_and_schema(tmp_path):
    public = tmp_path / "public"
    data = np.zeros((4, H, W), np.uint8)
    data[0] = 255
    data[3] = 255
    entry = write_layer(
        "demo",
        "sar_after",
        kind="sar-composite",
        label="Radar composite",
        date="2026-09-09/2026-10-03",
        data=data,
        transform=TR,
        crs="EPSG:4326",
        render={"type": "rgba"},
        source_ids=["synthetic"],
        status="illustrative",
        stretch={"HH": (-20, 0), "HV": (-28, -8), "ratio": (0, 15)},
        data_dir=public / "data",
    )
    cog, png = public / entry["cog"], public / entry["preview"]
    assert entry["cog"] == "data/demo/sar_after.tif" and entry["preview"] == "data/demo/sar_after.png"
    assert cog.stat().st_size == entry["bytes"] and sha256_file(cog) == entry["sha256"]
    img = Image.open(png)
    assert img.mode == "RGBA" and max(img.size) <= 1024
    layer_schema = {"$schema": schema()["$schema"], "$defs": schema()["$defs"], "$ref": "#/$defs/Layer"}
    from jsonschema import Draft202012Validator

    assert list(Draft202012Validator(layer_schema).iter_errors(json.loads(json.dumps(entry)))) == []


def test_ramp_preview_is_colored_with_transparent_nodata(tmp_path):
    public = tmp_path / "public"
    data = np.full((H, W), 6.0, np.float32)
    data[:60] = np.nan
    entry = write_layer(
        "demo",
        "hv_change",
        kind="change",
        label="HV drop",
        date="2026-06-17/2026-10-03",
        data=data,
        transform=TR,
        crs="EPSG:4326",
        render={"type": "ramp", "scheme": "BrewerYlOrRd9", "domain": [2, 10], "unit": "dB"},
        source_ids=["synthetic"],
        status="illustrative",
        data_dir=public / "data",
    )
    arr = np.asarray(Image.open(public / entry["preview"]))
    alpha = arr[..., 3]
    assert (alpha == 0).any() and (alpha == 255).any()
    colored = arr[alpha == 255][:, :3]
    assert len(np.unique(colored, axis=0)) <= 3, "a constant value must map to one color"
