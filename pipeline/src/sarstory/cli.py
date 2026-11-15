"""`sar` command line: fixture, validate, clean, discover, fetch, build."""

from __future__ import annotations

import argparse
import shutil
import sys

from . import fixture, manifest
from .config import CACHE_DIR, CHAPTERS_DIR, DATA_DIR, chapter_slugs, load_config
from .invariants import check_invariants
from .nisar import discover as nisar_discover
from .nisar import fetch as nisar_fetch
from .nisar.build import build as nisar_build
from .nisar.build_gunw import build as nisar_build_gunw


def cmd_fixture(args: argparse.Namespace) -> int:
    slugs = chapter_slugs() if args.all else args.slugs
    if not slugs:
        print("sar fixture: name a chapter or pass --all", file=sys.stderr)
        return 2
    failed = 0
    for slug in slugs:
        if args.all and "fixture" not in load_config(slug):
            print(f"skip  {slug}: no [fixture] config, so no illustrative data exists for it")
            continue
        try:
            path = fixture.build_fixture(slug, force=args.force)
        except (RuntimeError, ValueError, FileNotFoundError) as e:
            print(f"skip  {slug}: {e}", file=sys.stderr)
            failed += 1
            continue
        size = sum(f.stat().st_size for f in (DATA_DIR / slug).glob("*") if f.is_file())
        print(f"wrote {path.relative_to(path.parents[2])}  ({size / 1e6:.1f} MB of layer files)")
    return 1 if failed else 0


def cmd_validate(args: argparse.Namespace) -> int:
    slugs = args.slugs or sorted(p.stem for p in CHAPTERS_DIR.glob("*.json"))
    if not slugs:
        print("sar validate: no manifests found", file=sys.stderr)
        return 1
    problems, orders = 0, {}
    for slug in slugs:
        obj = manifest.read_manifest(slug)
        found = manifest.validate(obj)
        warnings = []
        if not found:
            errs, warnings = check_invariants(obj)
            found = errs + manifest.verify_assets(obj)
        if obj.get("slug") != slug:
            found.append(f"slug {obj.get('slug')!r} does not match the file name")
        if obj.get("order") in orders:
            found.append(f"order {obj['order']} is also used by {orders[obj['order']]}")
        orders[obj.get("order")] = slug
        if found:
            problems += len(found)
            print(f"FAIL  {slug}", file=sys.stderr)
            for line in found:
                print(f"      {line}", file=sys.stderr)
        else:
            for line in warnings:
                print(f"warn  {slug}: {line}", file=sys.stderr)
            gen = obj["generated"]
            statuses = sorted({layer["status"] for layer in gen["layers"]})
            kinds = "/".join(statuses)
            counts = f"{len(gen['layers'])} layers, {len(gen['series'])} series"
            print(f"ok    {slug}  {counts}, status {kinds}")
    return 1 if problems else 0


def cmd_discover(args: argparse.Namespace) -> int:
    slugs = chapter_slugs() if args.all else args.slugs
    if not slugs:
        print("sar discover: name a chapter or pass --all", file=sys.stderr)
        return 2
    missing = 0
    for slug in slugs:
        try:
            report, path = nisar_discover.run(slug)
        except Exception as e:  # network or catalog errors should name the chapter and keep going
            print(f"FAIL  {slug}: {type(e).__name__}: {e}", file=sys.stderr)
            missing += 1
            continue
        sel = report.selected
        shown = path.relative_to(path.parents[2])
        if sel:
            print(f"ok    {slug}  {sel.short_name} ({sel.maturity}), stack {sel.choice.stack}  -> {shown}")
        else:
            print(f"none  {slug}  no stack with data in every window; step down the ladder  -> {shown}")
            missing += 1
    return 1 if missing else 0


def cmd_fetch(args: argparse.Namespace) -> int:
    failed = 0
    for slug in args.slugs:
        try:
            path = nisar_fetch.run(slug)
        except Exception as e:
            print(f"FAIL  {slug}: {type(e).__name__}: {e}", file=sys.stderr)
            failed += 1
            continue
        print(f"ok    {slug}  cached in {path}")
    return 1 if failed else 0


def cmd_build(args: argparse.Namespace) -> int:
    failed = 0
    for slug in args.slugs:
        try:
            optical = "reuse" if args.reuse_optical else not args.no_optical
            build_fn = nisar_build_gunw if load_config(slug)["product"] == "GUNW" else nisar_build
            path = build_fn(slug, optical=optical)
        except Exception as e:
            print(f"FAIL  {slug}: {type(e).__name__}: {e}", file=sys.stderr)
            failed += 1
            continue
        print(f"wrote {path.relative_to(path.parents[2])}")
    return 1 if failed else 0


def cmd_clean(_: argparse.Namespace) -> int:
    shutil.rmtree(CACHE_DIR, ignore_errors=True)
    print(f"removed {CACHE_DIR}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sar", description="Dancing with the SARs pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("fixture", help="write illustrative layers and series into chapter manifests")
    p.add_argument("slugs", nargs="*")
    p.add_argument("--all", action="store_true", help="every chapter with a processing config")
    p.add_argument("--force", action="store_true", help="replace layers that hold real or fallback data")
    p.set_defaults(func=cmd_fixture)
    p = sub.add_parser("validate", help="check manifests against the schema and their asset files")
    p.add_argument("slugs", nargs="*")
    p.set_defaults(func=cmd_validate)
    p = sub.add_parser("discover", help="search the public NISAR catalog and choose a stack (no login)")
    p.add_argument("slugs", nargs="*")
    p.add_argument("--all", action="store_true", help="every chapter with a processing config")
    p.set_defaults(func=cmd_discover)
    p = sub.add_parser(
        "fetch", help="read each chosen granule's study-area window into the cache (needs login)"
    )
    p.add_argument("slugs", nargs="+")
    p.set_defaults(func=cmd_fetch)
    p = sub.add_parser("build", help="turn the fetched tiles into a chapter manifest with real layers")
    p.add_argument("slugs", nargs="+")
    p.add_argument("--no-optical", action="store_true", help="skip the optical layers (no network needed)")
    p.add_argument(
        "--reuse-optical", action="store_true", help="keep the optical layers already in the manifest"
    )
    p.set_defaults(func=cmd_build)
    p = sub.add_parser("clean", help="remove the pipeline cache")
    p.set_defaults(func=cmd_clean)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
