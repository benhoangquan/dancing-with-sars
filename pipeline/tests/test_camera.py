import json
from pathlib import Path

import pytest

from sarstory.flyover.camera import camera_at, normalize_bearing, shortest_arc

GOLDEN = json.loads(
    (Path(__file__).resolve().parents[2] / "schema" / "golden" / "camera_interp.json").read_text()
)


def cases():
    out = []
    for name, s in GOLDEN["sets"].items():
        for c in s["cases"]:
            out.append(pytest.param(s["waypoints"], c["t"], c["camera"], id=f"{name}@{c['t']}"))
    return out


@pytest.mark.parametrize(("waypoints", "t", "expected"), cases())
def test_golden_vectors(waypoints, t, expected):
    got = camera_at(waypoints, t)
    tol = GOLDEN["tolerance"]
    for k in ("zoom", "pitch", "bearing"):
        assert got[k] == pytest.approx(expected[k], abs=tol), k
    assert got["center"] == pytest.approx(expected["center"], abs=tol)


def test_segment_midpoint_is_the_mean_for_linear_fields():
    wps = [
        {"t": 0, "camera": {"center": [0, 0], "zoom": 8, "pitch": 0, "bearing": 0}},
        {"t": 10, "camera": {"center": [2, 4], "zoom": 10, "pitch": 60, "bearing": 40}},
    ]
    mid = camera_at(wps, 5)  # smoothstep(0.5) == 0.5
    assert mid == {"center": [1.0, 2.0], "zoom": 9.0, "pitch": 30.0, "bearing": 20.0}


def test_clamps_outside_the_range_and_hits_waypoints_exactly():
    wps = GOLDEN["sets"]["basic"]["waypoints"]
    assert camera_at(wps, -50) == camera_at(wps, 0) == wps[0]["camera"]
    assert camera_at(wps, 999) == wps[-1]["camera"]
    assert camera_at(wps, wps[1]["t"])["zoom"] == pytest.approx(wps[1]["camera"]["zoom"])


def test_bearing_helpers():
    assert normalize_bearing(180) == -180
    assert normalize_bearing(-180) == -180
    assert normalize_bearing(540) == -180
    assert normalize_bearing(359) == -1
    assert shortest_arc(170, -170) == 20
    assert shortest_arc(-170, 170) == -20
    assert shortest_arc(0, 180) == -180


def test_needs_two_waypoints():
    with pytest.raises(ValueError):
        camera_at([{"t": 0, "camera": {"center": [0, 0], "zoom": 1, "pitch": 0, "bearing": 0}}], 0)
