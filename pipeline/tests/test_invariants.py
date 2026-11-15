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
        ("four beats", lambda o: o["beats"].pop(), "exactly 5"),
        ("flyover not 20 s", lambda o: o["generated"]["flyover"].update(duration=36), "must be 20"),
        ("no opening camera", lambda o: o.pop("openingCamera"), "openingCamera is missing"),
        ("opening pose drifts", lambda o: o["openingCamera"].update(pitch=40), "must equal openingCamera"),
        ("unknown fact token", lambda o: o["beats"][2].update(body="Sank {fact:nope}."), "{fact:nope}"),
        ("hectares without anchor", lambda o: o["scaleAnchors"].pop("cleared_ha"), "needs a scaleAnchors"),
        ("anchor for nothing", lambda o: o["scaleAnchors"].update(ghost="central-park"), "neither a stat"),
        (
            "landmark outside AOI",
            lambda o: o.update(landmarks=[{"id": "far", "label": "Far", "lonLat": [0, 0]}]),
            "landmark far",
        ),
        (
            "reading for unknown landmark",
            lambda o: o["generated"].update(
                landmarkReadings={
                    "ghost": [
                        {"label": "HV", "value": 1, "unit": "dB", "decimals": 1, "layerId": "sar_after"}
                    ]
                }
            ),
            "not a landmark",
        ),
        (
            "footprint cites unknown source",
            lambda o: o["generated"].update(
                footprint={
                    "kind": "shape",
                    "label": "x",
                    "areaHa": 1,
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[-63, -10], [-63.1, -10], [-63.1, -9.9], [-63, -10]]],
                    },
                    "sourceIds": ["ghost"],
                    "status": "real",
                }
            ),
            "footprint: unknown source",
        ),
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


def test_fact_tokens_resolve_and_count_as_sourced_numbers(rondonia):
    fact = {
        "id": "sinking",
        "value": 10,
        "unit": "cm/yr",
        "decimals": 0,
        "label": "Subsidence",
        "source": {"name": "Study", "url": "https://example.org/x", "accessed": "2026-11-15"},
    }
    errs, warns = run(
        rondonia,
        lambda o: (
            o.update(facts=[fact]),
            o["scaleAnchors"].update(sinking="per-decade"),
            o["beats"][2].update(body="Ground sinks {fact:sinking} here."),
        ),
    )
    assert errs == [] and warns == []
    errs, _ = run(
        rondonia, lambda o: (o.update(facts=[fact]), o["beats"][2].update(body="Sinks {fact:sinking}."))
    )
    assert any("needs a scaleAnchors" in e for e in errs)
