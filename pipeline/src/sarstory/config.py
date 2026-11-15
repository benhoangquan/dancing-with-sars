"""Repository paths and per-chapter processing config (`pipeline/chapters/<slug>.toml`)."""

from __future__ import annotations

import tomllib
from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = PIPELINE_DIR.parent
SCHEMA_PATH = REPO_ROOT / "schema" / "chapter.schema.json"
WEB_PUBLIC = REPO_ROOT / "web" / "public"
CHAPTERS_DIR = WEB_PUBLIC / "chapters"
DATA_DIR = WEB_PUBLIC / "data"
CONFIG_DIR = PIPELINE_DIR / "chapters"
CACHE_DIR = PIPELINE_DIR / "cache"
REPORTS_DIR = PIPELINE_DIR / "reports"


def chapter_slugs() -> list[str]:
    """Slugs that have a processing config, in file-name order."""
    return sorted(p.stem for p in CONFIG_DIR.glob("*.toml"))


def load_config(slug: str) -> dict:
    path = CONFIG_DIR / f"{slug}.toml"
    if not path.is_file():
        raise FileNotFoundError(f"no processing config for chapter {slug!r}: {path}")
    with path.open("rb") as f:
        cfg = tomllib.load(f)
    if cfg.get("slug") != slug:
        raise ValueError(f"{path.name}: slug {cfg.get('slug')!r} does not match the file name")
    return cfg
