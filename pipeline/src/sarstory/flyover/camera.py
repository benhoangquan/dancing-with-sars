"""Camera interpolation along flyover waypoints.

The same algorithm lives in `web/src/lib/camera.ts`. Both are tested against
`schema/golden/camera_interp.json`; the spec is in `docs/data_contract.md`.

A waypoint is `{"t": seconds, "camera": {"center": [lon, lat], "zoom", "pitch", "bearing"}}`
with MapLibre semantics (pitch from vertical, bearing clockwise from north).
"""

from __future__ import annotations


def _mod(x: float, m: float) -> float:
    return ((x % m) + m) % m


def normalize_bearing(x: float) -> float:
    """Bearing in degrees mapped into [-180, 180)."""
    return _mod(x + 180.0, 360.0) - 180.0


def shortest_arc(b0: float, b1: float) -> float:
    """Signed shortest rotation from b0 to b1, in [-180, 180). Exactly 180 degrees resolves to -180."""
    return _mod(b1 - b0 + 540.0, 360.0) - 180.0


def smoothstep(u: float) -> float:
    return u * u * (3.0 - 2.0 * u)


def _lerp(a: float, b: float, s: float) -> float:
    return a + (b - a) * s


def camera_at(waypoints: list[dict], t: float) -> dict:
    """Camera at time `t` seconds. `t` is clamped to the waypoint range."""
    if len(waypoints) < 2:
        raise ValueError("camera_at needs at least two waypoints")
    first, last = waypoints[0], waypoints[-1]
    t = min(max(t, first["t"]), last["t"])
    seg = len(waypoints) - 2
    for i in range(len(waypoints) - 1):
        if waypoints[i]["t"] <= t <= waypoints[i + 1]["t"]:
            seg = i
            break
    w0, w1 = waypoints[seg], waypoints[seg + 1]
    span = w1["t"] - w0["t"]
    u = 1.0 if span <= 0 else (t - w0["t"]) / span
    s = smoothstep(u)
    c0, c1 = w0["camera"], w1["camera"]
    bearing = normalize_bearing(c0["bearing"] + shortest_arc(c0["bearing"], c1["bearing"]) * s)
    return {
        "center": [_lerp(c0["center"][0], c1["center"][0], s), _lerp(c0["center"][1], c1["center"][1], s)],
        "zoom": _lerp(c0["zoom"], c1["zoom"], s),
        "pitch": _lerp(c0["pitch"], c1["pitch"], s),
        "bearing": bearing,
    }
