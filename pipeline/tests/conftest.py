import copy
import json
import shutil

import pytest

from sarstory import fixture
from sarstory.config import CHAPTERS_DIR, load_config


def manifest_slugs() -> list[str]:
    return sorted(p.stem for p in CHAPTERS_DIR.glob("*.json"))


def fixture_slugs() -> list[str]:
    """Chapters that define illustrative data. Chapters added later with real data only have no fixture."""
    return [s for s in manifest_slugs() if "fixture" in load_config(s)]


@pytest.fixture(scope="session")
def manifests() -> dict[str, dict]:
    """The manifests as they are in the repo: real, illustrative or a mix."""
    return {s: json.loads((CHAPTERS_DIR / f"{s}.json").read_text(encoding="utf-8")) for s in manifest_slugs()}


@pytest.fixture(scope="session")
def fixture_manifests(tmp_path_factory) -> dict[str, dict]:
    """Every chapter built with illustrative data into a temp tree: a known, synthetic starting point for
    tests that change one thing and expect a specific error, whatever data the repo holds."""
    root = tmp_path_factory.mktemp("fixture-manifests")
    chapters = root / "public" / "chapters"
    chapters.mkdir(parents=True)
    out = {}
    for slug in fixture_slugs():
        shutil.copy(CHAPTERS_DIR / f"{slug}.json", chapters / f"{slug}.json")
        path = fixture.build_fixture(
            slug, data_dir=root / "public" / "data", chapters_dir=chapters, force=True
        )
        out[slug] = json.loads(path.read_text(encoding="utf-8"))
    return out


@pytest.fixture
def rondonia(fixture_manifests):
    """A deep copy of the illustrative rondonia manifest that a test may mutate."""
    return copy.deepcopy(fixture_manifests["rondonia"])
