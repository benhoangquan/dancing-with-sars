"""Find NISAR granules over a study area in NASA's CMR (public, no login) and pick one acquisition stack.

A before/after comparison is only valid between scenes with the same viewing geometry, so granules are
grouped by track and direction (the `STACK_ID` without its frame). One pass is cut into consecutive frames,
and a study area can span two of them, so an acquisition is every frame of one pass on one day, and its
coverage is the union of those footprints. Granule metadata is parsed from the UMM record;
`from_earthaccess` adapts an earthaccess result to a plain dict so the rest is testable offline.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

BBox = tuple[float, float, float, float]
NAME = re.compile(
    r"NISAR_L2_(?P<pipeline>[A-Z]{2})_(?P<product>[A-Z]+)_(?P<cycle>\d{3})_(?P<track>\d{3})_(?P<dir>[AD])_"
    r"(?P<frame>\d{3})_"
)


@dataclass(frozen=True)
class Granule:
    name: str
    collection: str
    stack: str  # "060_A_173": track, direction, frame
    start: date  # acquisition date; for GUNW the reference date
    end: date  # for GUNW the secondary date
    size_mb: float
    url: str
    polarizations: str  # frequency A, for example "HH+HV"
    full_frame: bool
    coverage: float  # share of the study area inside this granule's footprint, 0 to 1
    footprint: tuple[tuple[float, float], ...] = ()  # (lon, lat) corners

    @property
    def track_dir(self) -> str:
        """Track and direction, for example 068_D: the viewing geometry shared by all frames of a track."""
        return self.stack.rsplit("_", 1)[0]

    @property
    def frame(self) -> str:
        return self.stack.rsplit("_", 1)[-1]


def from_earthaccess(g) -> dict:
    """Plain-dict form of an earthaccess `DataGranule`, which is all `parse_granule` needs."""
    return {"umm": g["umm"], "size": float(g.size), "links": list(g.data_links())}


def _attrs(umm: dict) -> dict[str, list[str]]:
    return {a["Name"]: a["Values"] for a in umm.get("AdditionalAttributes", [])}


def _day(iso: str) -> date:
    return date.fromisoformat(iso[:10])


def polygon_of(umm: dict) -> list[tuple[float, float]]:
    """Footprint of the granule as (lon, lat) points; empty if the record has none."""
    try:
        pts = umm["SpatialExtent"]["HorizontalSpatialDomain"]["Geometry"]["GPolygons"][0]["Boundary"][
            "Points"
        ]
    except (KeyError, IndexError):
        return []
    return [(p["Longitude"], p["Latitude"]) for p in pts]


def _area(poly: list[tuple[float, float]]) -> float:
    return (
        abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1], strict=True))) / 2
    )


def _clip(poly: list[tuple[float, float]], bbox: BBox) -> list[tuple[float, float]]:
    """Sutherland-Hodgman clip of a polygon against an axis-aligned box."""
    w, s, e, n = bbox
    edges = [
        (lambda p: p[0] >= w, lambda a, b: (w, a[1] + (b[1] - a[1]) * (w - a[0]) / (b[0] - a[0]))),
        (lambda p: p[0] <= e, lambda a, b: (e, a[1] + (b[1] - a[1]) * (e - a[0]) / (b[0] - a[0]))),
        (lambda p: p[1] >= s, lambda a, b: (a[0] + (b[0] - a[0]) * (s - a[1]) / (b[1] - a[1]), s)),
        (lambda p: p[1] <= n, lambda a, b: (a[0] + (b[0] - a[0]) * (n - a[1]) / (b[1] - a[1]), n)),
    ]
    for inside, cross in edges:
        out: list[tuple[float, float]] = []
        for i, cur in enumerate(poly):
            prev = poly[i - 1]
            if inside(cur):
                if not inside(prev):
                    out.append(cross(prev, cur))
                out.append(cur)
            elif inside(prev):
                out.append(cross(prev, cur))
        poly = out
        if not poly:
            return []
    return poly


def coverage(poly: list[tuple[float, float]], bbox: BBox) -> float:
    """Share of `bbox` covered by the footprint, in degrees (fine for a study area this small)."""
    w, s, e, n = bbox
    clipped = _clip(poly, bbox) if len(poly) >= 3 else []
    return _area(clipped) / ((e - w) * (n - s)) if clipped else 0.0


def _inside(poly: tuple[tuple[float, float], ...], x: float, y: float) -> bool:
    """Ray casting point-in-polygon."""
    hit = False
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1], strict=True):
        if (y0 > y) != (y1 > y) and x < x0 + (x1 - x0) * (y - y0) / (y1 - y0):
            hit = not hit
    return hit


def union_coverage(footprints: list[tuple[tuple[float, float], ...]], bbox: BBox, n: int = 40) -> float:
    """Share of `bbox` covered by any of the footprints, sampled on an n by n grid of cell centers."""
    w, s, e, nn = bbox
    polys = [f for f in footprints if len(f) >= 3]
    if not polys:
        return 0.0
    covered = 0
    for i in range(n):
        y = s + (i + 0.5) * (nn - s) / n
        for j in range(n):
            x = w + (j + 0.5) * (e - w) / n
            covered += any(_inside(p, x, y) for p in polys)
    return covered / (n * n)


def parse_granule(raw: dict, bbox: BBox) -> Granule | None:
    """A `Granule` from a UMM record, or None if it is not a NISAR L2 product name."""
    umm = raw["umm"]
    name = umm["GranuleUR"]
    if not NAME.search(name):
        return None
    a = _attrs(umm)
    t = umm["TemporalExtent"]["RangeDateTime"]
    urls = [u for u in raw.get("links", []) if u.endswith(".h5")]
    return Granule(
        name=name,
        collection=umm["CollectionReference"].get("ShortName", ""),
        stack=a.get("STACK_ID", ["?"])[0],
        start=_day(t["BeginningDateTime"]),
        end=_day(t["EndingDateTime"]),
        size_mb=float(raw.get("size", 0.0)),
        url=urls[0] if urls else "",
        polarizations=a.get("FREQUENCY_A_POLARIZATION_CONCAT", [""])[0],
        full_frame=a.get("FULL_FRAME", ["FALSE"])[0] == "TRUE",
        coverage=coverage(polygon_of(umm), bbox),
        footprint=tuple(polygon_of(umm)),
    )


def search(short_name: str, bbox: BBox, temporal: tuple[str, str], count: int = 500) -> list[Granule]:
    """Granules of one collection that intersect `bbox` in the date range. Needs network, not a login."""
    import earthaccess

    found = earthaccess.search_data(short_name=short_name, bounding_box=bbox, temporal=temporal, count=count)
    return [g for raw in map(from_earthaccess, found) if (g := parse_granule(raw, bbox))]


@dataclass(frozen=True)
class Acquisition:
    """Every frame of one pass on one day, one granule per frame."""

    day: date
    granules: tuple[Granule, ...]
    coverage: float  # union of the frame footprints over the study area

    @property
    def size_mb(self) -> float:
        return sum(g.size_mb for g in self.granules)


@dataclass
class StackChoice:
    stack: str  # track and direction, for example "068_D"
    collection: str
    before: list[Acquisition]
    after: list[Acquisition]
    coverage: float  # worst acquisition


def _in(g: Granule, window: tuple[str, str]) -> bool:
    """The acquisition falls inside the window."""
    return date.fromisoformat(window[0]) <= g.start <= date.fromisoformat(window[1])


def _overlaps(g: Granule, window: tuple[str, str]) -> bool:
    """An interferogram's date span touches the window, even if its reference date is a day or two earlier."""
    return g.start <= date.fromisoformat(window[1]) and g.end >= date.fromisoformat(window[0])


def acquisitions(granules: list[Granule], bbox: BBox) -> dict[str, list[Acquisition]]:
    """Group granules by track and direction, then by day; the frames of one pass form one acquisition."""
    cells: dict[tuple[str, date], dict[str, Granule]] = defaultdict(dict)
    for g in sorted(granules, key=lambda g: g.name):
        cells[(g.track_dir, g.start)].setdefault(g.frame, g)  # one granule per frame, the first by name
    out: dict[str, list[Acquisition]] = defaultdict(list)
    for (track_dir, day), frames in sorted(cells.items()):
        gs = tuple(frames.values())
        out[track_dir].append(Acquisition(day, gs, union_coverage([g.footprint for g in gs], bbox)))
    return out


def choose_gcov_stack(
    granules: list[Granule],
    bbox: BBox,
    before: tuple[str, str],
    after: tuple[str, str],
    *,
    min_coverage: float = 0.9,
    polarizations: str = "HH+HV",
    max_dates: int = 8,
) -> StackChoice | None:
    """The track with dual-pol acquisitions covering the study area in both windows, most dates first."""
    usable = [g for g in granules if g.polarizations == polarizations and g.coverage > 0]
    best: StackChoice | None = None
    for track_dir, acqs in acquisitions(usable, bbox).items():
        good = [a for a in acqs if a.coverage >= min_coverage]
        b = [a for a in good if date.fromisoformat(before[0]) <= a.day <= date.fromisoformat(before[1])]
        a_ = [a for a in good if date.fromisoformat(after[0]) <= a.day <= date.fromisoformat(after[1])]
        if not b or not a_:
            continue
        chosen = b[:max_dates] + a_[:max_dates]
        cand = StackChoice(
            track_dir,
            chosen[0].granules[0].collection,
            b[:max_dates],
            a_[:max_dates],
            min(x.coverage for x in chosen),
        )
        key = lambda c: (min(len(c.before), len(c.after)), c.coverage)  # noqa: E731
        if best is None or key(cand) > key(best):
            best = cand
    return best


@dataclass
class ChainChoice:
    stack: str
    collection: str
    pairs: list[Granule]  # consecutive: each pair's reference date is the previous pair's secondary date
    coverage: float


def choose_gunw_stack(
    granules: list[Granule], window: tuple[str, str], *, min_coverage: float = 0.9
) -> ChainChoice | None:
    """The stack with the longest unbroken chain of sequential interferograms overlapping `window`."""
    by_stack: dict[str, list[Granule]] = defaultdict(list)
    for g in granules:
        if g.coverage >= min_coverage and _overlaps(g, window):
            by_stack[g.stack].append(g)
    best: ChainChoice | None = None
    for stack, gs in by_stack.items():
        gs.sort(key=lambda g: g.start)
        chain: list[Granule] = []
        longest: list[Granule] = []
        for g in gs:
            if chain and abs((g.start - chain[-1].end).days) <= 1:
                chain.append(g)
            else:
                chain = [g]
            if len(chain) > len(longest):
                longest = list(chain)
        cand = ChainChoice(stack, gs[0].collection, longest, min(g.coverage for g in longest))
        if best is None or (len(cand.pairs), cand.coverage) > (len(best.pairs), best.coverage):
            best = cand
    return best
