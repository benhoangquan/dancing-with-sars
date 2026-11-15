import copy

import pytest
from conftest import manifest_slugs
from jsonschema import Draft202012Validator

from sarstory.manifest import schema, validate


def test_schema_is_valid_2020_12():
    Draft202012Validator.check_schema(schema())
    assert schema()["$schema"].endswith("2020-12/schema")


def test_the_original_chapters_exist():
    assert {"okanagan", "rondonia"} <= set(manifest_slugs())


@pytest.mark.parametrize("slug", manifest_slugs())
def test_repo_manifests_match_schema(manifests, slug):
    assert validate(manifests[slug]) == []
    assert manifests[slug]["slug"] == slug


def broken(obj, mutate):
    o = copy.deepcopy(obj)
    mutate(o)
    return validate(o)


@pytest.mark.parametrize(
    ("name", "mutate"),
    [
        ("unknown top-level key", lambda o: o.update(extra=1)),
        ("unknown key in aoi", lambda o: o["aoi"].update(extra=1)),
        ("too few beats", lambda o: o.update(beats=o["beats"][:3])),
        ("too many beats", lambda o: o.update(beats=o["beats"] * 2)),
        ("bad accent", lambda o: o.update(accent="green")),
        ("bad slug", lambda o: o.update(slug="Bad Slug")),
        ("bbox out of range", lambda o: o["aoi"].update(bbox=[-200, 0, 0, 1])),
        ("unknown unit", lambda o: o["generated"]["stats"]["cleared_ha"].update(unit="furlongs")),
        ("asset path with leading slash", lambda o: o["generated"]["layers"][0].update(cog="/data/x.tif")),
        ("asset path with ..", lambda o: o["generated"]["layers"][0].update(preview="data/../x.png")),
        ("asset path with scheme", lambda o: o["generated"]["layers"][0].update(cog="https://x.test/a.tif")),
        ("http org url", lambda o: o["action"]["organizations"][0].update(url="http://example.org")),
        ("metric with statKey and value", lambda o: o["action"]["metrics"][0].update(value=1, unit="ha")),
        ("metric with neither", lambda o: o["action"]["metrics"][0].pop("statKey")),
        ("one organization", lambda o: o["action"].update(organizations=o["action"]["organizations"][:1])),
        ("explainer too long", lambda o: o["radar"].update(explainer="x" * 401)),
        ("bad sha256", lambda o: o["generated"]["layers"][0].update(sha256="abc")),
        (
            "series with one point",
            lambda o: o["generated"]["series"][0].update(points=o["generated"]["series"][0]["points"][:1]),
        ),
        ("swipe above one", lambda o: o["beats"][0]["stage"].update(swipe=1.5)),
        ("pitch above 85", lambda o: o["generated"]["flyover"]["waypoints"][0]["camera"].update(pitch=90)),
        ("status not in enum", lambda o: o["generated"]["layers"][0].update(status="fake")),
        (
            "ramp without domain",
            lambda o: o["generated"]["layers"][4].update(
                render={"type": "ramp", "scheme": "x", "unit": "dB"}
            ),
        ),
    ],
)
def test_schema_rejects(rondonia, name, mutate):
    assert broken(rondonia, mutate), f"schema accepted: {name}"
