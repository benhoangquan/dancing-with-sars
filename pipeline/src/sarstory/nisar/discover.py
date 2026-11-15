"""`sar discover`: which NISAR data exists over a chapter's study area, and which stack to process.

This is the gate for the data ladder. It reads only the public CMR catalog (no Earthdata login) and writes
a report to `pipeline/reports/<slug>-availability.md`. If no collection has a stack with data in every
window, the chapter steps down the ladder (fallback mission, then illustrative data).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from ..config import REPORTS_DIR, load_config
from ..manifest import read_manifest
from .search import (
    BBox,
    ChainChoice,
    Granule,
    StackChoice,
    acquisitions,
    choose_gcov_stack,
    choose_gunw_stack,
    search,
)

CADENCE_DAYS = 12
SearchFn = Callable[[str, BBox, tuple[str, str]], list[Granule]]


def maturity_of(short_name: str) -> str:
    """Maturity from the collection name. The plain `_V1` release is the validated one. The others are
    checked first, because every name ends in `V1`."""
    if "PROVISIONAL" in short_name:
        return "provisional"
    if "BETA" in short_name:
        return "beta"
    return "validated" if short_name.endswith("_V1") else "n/a"


@dataclass
class CollectionResult:
    short_name: str
    maturity: str
    granules: list[Granule]
    product: str = "GCOV"
    choice: StackChoice | ChainChoice | None = None

    @property
    def stacks(self) -> dict[str, list[Granule]]:
        """Granules by track and direction (GCOV, frames mosaicked) or per frame (GUNW)."""
        out: dict[str, list[Granule]] = {}
        for g in self.granules:
            out.setdefault(g.track_dir if self.product == "GCOV" else g.stack, []).append(g)
        return out


@dataclass
class Report:
    slug: str
    product: str
    bbox: BBox
    windows: dict[str, tuple[str, str]]
    min_coverage: float
    results: list[CollectionResult] = field(default_factory=list)

    @property
    def selected(self) -> CollectionResult | None:
        return next((r for r in self.results if r.choice), None)


def series_window(cfg: dict) -> tuple[str, str]:
    start = date.fromisoformat(cfg["series"]["start"])
    return start.isoformat(), (start + timedelta(days=CADENCE_DAYS * cfg["series"]["count"])).isoformat()


def discover(slug: str, *, search_fn: SearchFn = search, today: date | None = None) -> Report:
    """Search every configured collection, best maturity first, and choose a stack in each."""
    cfg = load_config(slug)
    # A location still being assessed has no manifest yet; its box then lives in its config.
    bbox = tuple(cfg["bbox"]) if "bbox" in cfg else tuple(read_manifest(slug)["aoi"]["bbox"])
    min_cov = cfg.get("discover", {}).get("min_coverage", 0.9)
    if cfg["product"] == "GCOV":
        win = {"before": tuple(cfg["windows"]["before"]), "after": tuple(cfg["windows"]["after"])}
    else:
        win = {"series": series_window(cfg)}
    report = Report(slug, cfg["product"], bbox, win, min_cov)
    until = (today or date.today()).isoformat()
    for short_name in cfg["collections"]:
        granules = search_fn(short_name, bbox, ("2025-10-01", until))
        res = CollectionResult(short_name, maturity_of(short_name), granules, cfg["product"])
        if cfg["product"] == "GCOV":
            res.choice = choose_gcov_stack(
                granules,
                bbox,
                win["before"],
                win["after"],
                min_coverage=min_cov,
                max_dates=cfg["processing"].get("max_dates", 8),
            )
        else:
            res.choice = choose_gunw_stack(granules, win["series"], min_coverage=min_cov)
        report.results.append(res)
    return report


def _span(gs: list[Granule]) -> str:
    return f"{min(g.start for g in gs)} to {max(g.start for g in gs)}"


def render_report(r: Report, generated: date | None = None) -> str:
    """Markdown for the committed availability report."""
    w, s, e, n = r.bbox
    lines = [
        f"# NISAR availability: {r.slug}",
        "",
        f"Generated {generated or date.today()} from the public CMR catalog (no login). "
        f"Product: {r.product}.",
        f"Study area `[{w}, {s}, {e}, {n}]`. An acquisition counts only if the frames of one pass "
        f"together cover at least {r.min_coverage:.0%} of it.",
        "",
        "| Window | Dates |",
        "|---|---|",
        *[f"| {name} | {a} to {b} |" for name, (a, b) in r.windows.items()],
        "",
        "## Collections searched, best maturity first",
        "",
        "| Collection | Maturity | Granules | Tracks | Dates covered | Track with data in every window |",
        "|---|---|---|---|---|---|",
    ]
    for res in r.results:
        gs = res.granules
        choice = f"`{res.choice.stack}`" if res.choice else "none"
        lines.append(
            f"| `{res.short_name}` | {res.maturity} | {len(gs)} | {len(res.stacks)} | "
            f"{_span(gs) if gs else 'none'} | {choice} |"
        )
    sel = r.selected
    lines += ["", "## Decision", ""]
    if not sel:
        lines += [
            "**No collection has a single track with data in every window.** "
            "This chapter steps down the data",
            "ladder: use a labeled fallback mission, or keep the layer `illustrative`.",
            "",
        ]
        return "\n".join(lines) + "\n"
    c = sel.choice
    assert c is not None
    lines += [
        f"Use **`{sel.short_name}`** ({sel.maturity}), "
        f"{'track' if isinstance(c, StackChoice) else 'stack'} **`{c.stack}`**, "
        f"footprint coverage {c.coverage:.0%} (worst date).",
        "",
    ]
    if isinstance(c, StackChoice):
        lines += ["| Window | Date | Frames | Coverage | Granules | Size (MB) |", "|---|---|---|---|---|---|"]
        for name, acqs in (("before", c.before), ("after", c.after)):
            lines += [
                f"| {name} | {a.day} | {'+'.join(g.frame for g in a.granules)} | {a.coverage:.0%} | "
                f"{'<br>'.join(f'`{g.name}`' for g in a.granules)} | {a.size_mb:,.0f} |"
                for a in acqs
            ]
        every = c.before + c.after
        total = sum(a.size_mb for a in every)
        lines += [
            "",
            f"{len(every)} acquisitions, {sum(len(a.granules) for a in every)} full-frame granules, "
            f"{total / 1000:,.1f} GB in all. The pipeline reads only the study-area window from each "
            "file, so far less than that is transferred. Where a pass is cut into two frames, both are "
            "read and mosaicked.",
        ]
    else:
        lines += ["| Pair | Reference | Secondary | Granule | Size (MB) |", "|---|---|---|---|---|"]
        lines += [
            f"| {i + 1} | {g.start} | {g.end} | `{g.name}` | {g.size_mb:,.0f} |"
            for i, g in enumerate(c.pairs)
        ]
        lines += [
            "",
            f"{len(c.pairs)} sequential interferograms, "
            f"{sum(g.size_mb for g in c.pairs) / 1000:,.1f} GB of full frames.",
        ]
    lines += [
        "",
        "## Other tracks over the study area (selected collection)",
        "",
        "| Track | Granules | Acquisitions | Best coverage |",
        "|---|---|---|---|",
    ]
    if r.product == "GCOV":
        by_track = acquisitions(sel.granules, r.bbox)
        for track, acqs in sorted(by_track.items(), key=lambda kv: -len(kv[1])):
            lines.append(
                f"| `{track}` | {sum(len(a.granules) for a in acqs)} | {acqs[0].day} to {acqs[-1].day} "
                f"({len(acqs)}) | {max(a.coverage for a in acqs):.0%} |"
            )
    else:
        for stack, gs in sorted(sel.stacks.items(), key=lambda kv: -len(kv[1])):
            lines.append(f"| `{stack}` | {len(gs)} | {_span(gs)} | {max(g.coverage for g in gs):.0%} |")
    return "\n".join(lines) + "\n"


def run(slug: str, *, search_fn: SearchFn = search) -> tuple[Report, Path]:
    report = discover(slug, search_fn=search_fn)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"{slug}-availability.md"
    path.write_text(render_report(report), encoding="utf-8")
    return report, path
