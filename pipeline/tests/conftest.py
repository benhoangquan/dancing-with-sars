import copy
import json

import pytest

from sarstory.config import CHAPTERS_DIR


def manifest_slugs() -> list[str]:
    return sorted(p.stem for p in CHAPTERS_DIR.glob("*.json"))


@pytest.fixture(scope="session")
def manifests() -> dict[str, dict]:
    return {s: json.loads((CHAPTERS_DIR / f"{s}.json").read_text(encoding="utf-8")) for s in manifest_slugs()}


@pytest.fixture
def rondonia(manifests):
    """A deep copy of the rondonia manifest that a test may mutate."""
    return copy.deepcopy(manifests["rondonia"])
