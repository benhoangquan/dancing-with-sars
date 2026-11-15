import copy

import pytest
from conftest import manifest_slugs

from sarstory.invariants import check_invariants


@pytest.mark.parametrize("slug", manifest_slugs())
def test_repo_manifests_have_no_errors_or_warnings(manifests, slug):
    errs, warns = check_invariants(manifests[slug])
    assert errs == [] and warns == []


def run(obj, mutate):
    o = copy.deepcopy(obj)
    mutate(o)
    return check_invariants(o)


@pytest.mark.parametrize(
    ("name", "mutate", "needle"),
    [
        ("unknown token", lambda o: o["beats"][2].update(body="Fell by {stat:nope}."), "token"),
        ("beat layer missing", lambda o: o["beats"][0]["stage"].update(left="ghost"), "stage.left"),
        ("overlay missing", lambda o: o["beats"][2]["stage"].update(overlays=["ghost"]), "overlay"),
        ("annotation missing", lambda o: o["beats"][2]["stage"].update(annotations=["ghost"]), "annotation"),
        (
            "readout series missing",
            lambda o: o["beats"][2]["readout"].update(seriesId="ghost"),
            "readout series",
        ),
        ("readout stat missing", lambda o: o["beats"][2]["readout"].update(statKey="ghost"), "readout stat"),
        ("legend layer missing", lambda o: o["legend"][0].update(layerIds=["ghost"]), "legend"),
        ("metric stat missing", lambda o: o["action"]["metrics"][0].update(statKey="ghost"), "metric"),
        (
            "window beyond duration",
            lambda o: o["beats"][0]["stage"]["flyover"].update(to=999),
            "flyover window",
        ),
        (
            "window reversed",
            lambda o: o["beats"][0]["stage"]["flyover"].update(**{"from": 9, "to": 3}),
            "flyover window",
        ),
        (
            "waypoint t not starting at 0",
            lambda o: o["generated"]["flyover"]["waypoints"][0].update(t=1),
            "first t",
        ),
        (
            "waypoint t descending",
            lambda o: o["generated"]["flyover"]["waypoints"][1].update(t=40),
            "ascending",
        ),
        (
            "camera outside AOI",
            lambda o: o["generated"]["flyover"]["waypoints"][1]["camera"].update(center=[0, 0]),
            "outside the AOI",
        ),
        (
            "zoom out of range",
            lambda o: o["generated"]["flyover"]["waypoints"][1]["camera"].update(zoom=3),
            "zoom",
        ),
        ("series unsorted", lambda o: o["generated"]["series"][0]["points"].reverse(), "ascending"),
        (
            "illustrative without synthetic",
            lambda o: o["generated"]["sources"][0].update(mission="NISAR"),
            "Synthetic",
        ),
        ("real citing synthetic", lambda o: o["generated"]["layers"][0].update(status="real"), "cannot cite"),
        (
            "unknown source",
            lambda o: o["generated"]["layers"][0].update(sourceIds=["ghost"]),
            "unknown source",
        ),
        ("duplicate beat id", lambda o: o["beats"][1].update(id=o["beats"][0]["id"]), "duplicate beat"),
        ("bbox inverted", lambda o: o["aoi"].update(bbox=[-62.9, -10.4, -63.8, -9.7]), "west < east"),
    ],
)
def test_invariant_errors(rondonia, name, mutate, needle):
    errs, _ = run(rondonia, mutate)
    assert any(needle in e for e in errs), (name, errs)


def test_digits_in_text_warn_but_years_do_not(rondonia):
    _, warns = run(rondonia, lambda o: o["beats"][0].update(body="Roads reached 40 km by 2026."))
    assert any("digits" in w for w in warns)
    _, warns = run(rondonia, lambda o: o["beats"][0].update(body="Data from 2026 and 1999."))
    assert warns == []
