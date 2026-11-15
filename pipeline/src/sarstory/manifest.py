"""Chapter manifest I/O and validation against `schema/chapter.schema.json`."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

from .cog import sha256_file
from .config import CHAPTERS_DIR, SCHEMA_PATH, WEB_PUBLIC
from .invariants import check_invariants


@lru_cache(maxsize=1)
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def validator() -> Draft202012Validator:
    Draft202012Validator.check_schema(schema())
    return Draft202012Validator(schema(), format_checker=Draft202012Validator.FORMAT_CHECKER)


def validate(obj: dict) -> list[str]:
    """Schema errors as `path: message` lines, sorted by path. Empty means valid."""
    errs = sorted(validator().iter_errors(obj), key=lambda e: [str(p) for p in e.absolute_path])
    return [f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message[:200]}" for e in errs]


def verify_assets(obj: dict, public_dir: Path = WEB_PUBLIC) -> list[str]:
    """Every layer file and video exists and matches its recorded byte count and sha256."""
    problems = []
    gen = obj.get("generated", {})
    for layer in gen.get("layers", []):
        for key in ("cog", "preview"):
            if not (public_dir / layer[key]).is_file():
                problems.append(f"layer {layer['id']}: {key} file {layer[key]} is missing")
        cog = public_dir / layer["cog"]
        if cog.is_file():
            if cog.stat().st_size != layer["bytes"]:
                problems.append(
                    f"layer {layer['id']}: bytes {cog.stat().st_size} != manifest {layer['bytes']}"
                )
            elif sha256_file(cog) != layer["sha256"]:
                problems.append(f"layer {layer['id']}: sha256 does not match {layer['cog']}")
    video = gen.get("flyover", {}).get("video")
    if video:
        for key in ("src", "poster"):
            if not (public_dir / video[key]).is_file():
                problems.append(f"flyover video: {key} file {video[key]} is missing")
    return problems


def manifest_path(slug: str, chapters_dir: Path = CHAPTERS_DIR) -> Path:
    return chapters_dir / f"{slug}.json"


def read_manifest(slug: str, chapters_dir: Path = CHAPTERS_DIR) -> dict:
    path = manifest_path(slug, chapters_dir)
    if not path.is_file():
        raise FileNotFoundError(f"no manifest for {slug!r}: author {path} first")
    return json.loads(path.read_text(encoding="utf-8"))


def _scalar(x) -> bool:
    return x is None or isinstance(x, (bool, int, float, str))


def _dump(o, level: int) -> str:
    pad = "  " * level
    if isinstance(o, dict):
        if not o:
            return "{}"
        if all(_scalar(v) for v in o.values()):
            inline = (
                "{ "
                + ", ".join(f"{json.dumps(k)}: {json.dumps(v, ensure_ascii=False)}" for k, v in o.items())
                + " }"
            )
            if len(inline) <= 90:
                return inline
        rows = [f"{pad}  {json.dumps(k, ensure_ascii=False)}: {_dump(v, level + 1)}" for k, v in o.items()]
        return "{\n" + ",\n".join(rows) + "\n" + pad + "}"
    if isinstance(o, list):
        if not o:
            return "[]"
        if all(_scalar(x) for x in o):
            inline = "[" + ", ".join(json.dumps(x, ensure_ascii=False) for x in o) + "]"
            if len(inline) <= 100:
                return inline
        rows = [f"{pad}  {_dump(x, level + 1)}" for x in o]
        return "[\n" + ",\n".join(rows) + "\n" + pad + "]"
    return json.dumps(o, ensure_ascii=False)


def dumps(obj: dict) -> str:
    """Stable, diff-friendly JSON: two-space indent, short scalar arrays and flat objects on one line."""
    return _dump(obj, 0) + "\n"


def write_manifest(slug: str, obj: dict, chapters_dir: Path = CHAPTERS_DIR) -> Path:
    """Validate then write. Raises ValueError with the schema errors and writes nothing if invalid."""
    if obj.get("slug") != slug:
        raise ValueError(f"manifest slug {obj.get('slug')!r} does not match {slug!r}")
    errors = validate(obj)
    if not errors:
        errors, _ = check_invariants(obj)
    if errors:
        raise ValueError(f"{slug}: manifest is not valid:\n  " + "\n  ".join(errors))
    path = manifest_path(slug, chapters_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps(obj), encoding="utf-8")
    return path
