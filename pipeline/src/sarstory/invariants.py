"""Checks the JSON schema cannot express: references that must resolve, flyover timing, camera limits.

`web/scripts/validate-chapters.mjs` implements the same list for the web build. The list is in
`docs/data_contract.md` under "Validation invariants".
"""

from __future__ import annotations

import re

TOKEN = re.compile(r"\{stat:([a-z0-9_]+)\}")
FACT = re.compile(r"\{fact:([a-z0-9_]+)\}")
BEATS = 5  # Act I, three Act II beats, Act III
FLYOVER_SECONDS = 20.0
ANCHORED_UNITS = {"ha", "km2", "dB", "cm/yr"}  # figures that must be paired with an everyday reference
YEAR = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
PAD = 0.10
ZOOM_RANGE, PITCH_RANGE = (5.0, 16.0), (0.0, 85.0)


def _dupes(ids: list[str]) -> list[str]:
    return sorted({i for i in ids if ids.count(i) > 1})


def _padded(bbox: list[float]) -> tuple[float, float, float, float]:
    w, s, e, n = bbox
    return w - (e - w) * PAD, s - (n - s) * PAD, e + (e - w) * PAD, n + (n - s) * PAD


def _check_camera(where: str, cam: dict, bbox: list[float], errs: list[str]) -> None:
    w, s, e, n = _padded(bbox)
    lon, lat = cam["center"]
    if not (w <= lon <= e and s <= lat <= n):
        errs.append(f"{where}: center {cam['center']} is outside the AOI bbox padded by 10%")
    if not ZOOM_RANGE[0] <= cam["zoom"] <= ZOOM_RANGE[1]:
        errs.append(f"{where}: zoom {cam['zoom']} outside {ZOOM_RANGE}")
    if not PITCH_RANGE[0] <= cam["pitch"] <= PITCH_RANGE[1]:
        errs.append(f"{where}: pitch {cam['pitch']} outside {PITCH_RANGE}")


def _sorted_points(where: str, points: list[dict], errs: list[str]) -> None:
    dates = [p["t"] for p in points]
    if dates != sorted(set(dates)):
        errs.append(f"{where}: points must have strictly ascending, unique dates")


def check_invariants(obj: dict) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for a manifest that already passed the schema."""
    errs: list[str] = []
    warns: list[str] = []
    gen = obj["generated"]
    bbox = obj["aoi"]["bbox"]
    if not (bbox[0] < bbox[2] and bbox[1] < bbox[3]):
        errs.append(f"aoi.bbox {bbox} must satisfy west < east and south < north")

    layers = {lyr["id"] for lyr in gen["layers"]}
    series = {s["id"] for s in gen["series"]}
    stats = set(gen["stats"])
    notes = {a["id"] for a in gen["annotations"]}
    sources = {s["id"]: s for s in gen["sources"]}
    facts = {f["id"]: f for f in obj.get("facts", [])}
    anchors = obj.get("scaleAnchors", {})
    landmarks = {lm["id"]: lm for lm in obj.get("landmarks", [])}
    for kind, ids in (
        ("fact", [f["id"] for f in obj.get("facts", [])]),
        ("landmark", [lm["id"] for lm in obj.get("landmarks", [])]),
        ("layer", [lyr["id"] for lyr in gen["layers"]]),
        ("series", [s["id"] for s in gen["series"]]),
        ("annotation", [a["id"] for a in gen["annotations"]]),
        ("source", [s["id"] for s in gen["sources"]]),
        ("beat", [b["id"] for b in obj["beats"]]),
        ("legend entry", [e["id"] for e in obj["legend"]]),
    ):
        for d in _dupes(ids):
            errs.append(f"duplicate {kind} id {d!r}")

    for entry in obj["legend"]:
        for lid in entry["layerIds"]:
            if lid not in layers:
                errs.append(f"legend {entry['id']}: unknown layer {lid!r}")

    flyover = gen["flyover"]
    wps = flyover["waypoints"]
    ts = [w["t"] for w in wps]
    if ts != sorted(set(ts)):
        errs.append("flyover.waypoints: t must be strictly ascending")
    if ts[0] != 0 or ts[-1] != flyover["duration"]:
        errs.append(
            f"flyover.waypoints: first t must be 0 and last t must equal duration {flyover['duration']}"
        )
    for i, wp in enumerate(wps):
        _check_camera(f"flyover.waypoints[{i}]", wp["camera"], bbox, errs)
    if len(obj["beats"]) != BEATS:
        errs.append(
            f"beats: need exactly {BEATS} (Act I, three Act II beats, Act III), have {len(obj['beats'])}"
        )
    if flyover["duration"] != FLYOVER_SECONDS:
        errs.append(f"flyover.duration must be {FLYOVER_SECONDS:g} s, is {flyover['duration']}")
    opening = obj.get("openingCamera")
    if opening is None:
        errs.append("openingCamera is missing")
    else:
        _check_camera("openingCamera", opening, bbox, errs)
        if wps[-1]["camera"] != opening:
            errs.append("flyover.waypoints: the last waypoint camera must equal openingCamera")

    units = {k: v["unit"] for k, v in gen["stats"].items()} | {k: f["unit"] for k, f in facts.items()}
    for key in anchors:
        if key not in units:
            errs.append(f"scaleAnchors: {key!r} is neither a stat nor a fact")
    for lid, lm in landmarks.items():
        w, s_, e, n = _padded(bbox)
        lon, lat = lm["lonLat"]
        if not (w <= lon <= e and s_ <= lat <= n):
            errs.append(f"landmark {lid}: {lm['lonLat']} is outside the AOI bbox padded by 10%")
    for lid, readings in gen.get("landmarkReadings", {}).items():
        if lid not in landmarks:
            errs.append(f"landmarkReadings: {lid!r} is not a landmark")
        for r in readings:
            if r["layerId"] not in layers:
                errs.append(f"landmarkReadings {lid}: layer {r['layerId']!r} does not exist")

    def check_text(where: str, text: str, anchored: bool = False) -> None:
        for key in TOKEN.findall(text):
            if key not in stats:
                errs.append(f"{where}: token {{stat:{key}}} has no stat")
        for key in FACT.findall(text):
            if key not in facts:
                errs.append(f"{where}: token {{fact:{key}}} has no fact")
        if anchored:
            for key in TOKEN.findall(text) + FACT.findall(text):
                if units.get(key) in ANCHORED_UNITS and key not in anchors:
                    errs.append(f"{where}: {key!r} ({units[key]}) needs a scaleAnchors entry")
        if re.search(r"\d", YEAR.sub("", FACT.sub("", TOKEN.sub("", text)))):
            warns.append(f"{where}: digits in text; use a {{stat:key}} or {{fact:key}} token")

    for beat in obj["beats"]:
        b, st = beat["id"], beat["stage"]
        for field in ("left", "right", "flyoverLayer"):
            if field in st and st[field] not in layers:
                errs.append(f"beat {b}: stage.{field} {st[field]!r} is not a layer")
        for lid in st.get("overlays", []):
            if lid not in layers:
                errs.append(f"beat {b}: overlay {lid!r} is not a layer")
        for nid in st.get("annotations", []):
            if nid not in notes:
                errs.append(f"beat {b}: annotation {nid!r} does not exist")
        fl = st["flyover"]
        if not 0 <= fl["from"] <= fl["to"] <= flyover["duration"]:
            errs.append(
                f"beat {b}: flyover window {fl['from']}..{fl['to']} must lie within 0..{flyover['duration']}"
            )
        if "camera" in st:
            _check_camera(f"beat {b} camera", st["camera"], bbox, errs)
        ro = beat.get("readout")
        if ro:
            if ro["seriesId"] not in series:
                errs.append(f"beat {b}: readout series {ro['seriesId']!r} does not exist")
            if "statKey" in ro and ro["statKey"] not in stats:
                errs.append(f"beat {b}: readout stat {ro['statKey']!r} does not exist")
        check_text(f"beat {b} body", beat["body"], anchored=True)

    check_text("action.body", obj["action"]["body"])
    for m in obj["action"]["metrics"]:
        if "statKey" in m and m["statKey"] not in stats:
            errs.append(f"action metric {m['label']!r}: stat {m['statKey']!r} does not exist")

    extras = [("footprint", gen["footprint"])] if "footprint" in gen else []
    for name in ("impact", "dem"):
        if name in gen:
            for sid in gen[name]["sourceIds"]:
                if sid not in sources:
                    errs.append(f"{name}: unknown source {sid!r}")
    for item_kind, items in (
        ("layer", gen["layers"]),
        ("series", gen["series"]),
        *((k, [v]) for k, v in extras),
    ):
        for it in items:
            where = f"{item_kind} {it.get('id', '')}".strip()
            for sid in it["sourceIds"]:
                if sid not in sources:
                    errs.append(f"{where}: unknown source {sid!r}")
            missions = {sources[s]["mission"] for s in it["sourceIds"] if s in sources}
            if it["status"] == "illustrative" and "Synthetic" not in missions:
                errs.append(f"{where}: illustrative data must cite a Synthetic source")
            if it["status"] != "illustrative" and "Synthetic" in missions:
                errs.append(f"{where}: status {it['status']!r} cannot cite a Synthetic source")
    for s in gen["series"]:
        _sorted_points(f"series {s['id']}", s["points"], errs)
        if "reference" in s:
            _sorted_points(f"series {s['id']} reference", s["reference"]["points"], errs)
    return errs, warns
