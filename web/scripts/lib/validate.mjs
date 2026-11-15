// Chapter manifest validation: JSON Schema (Ajv 2020-12) plus the invariants the schema cannot express.
// Mirrors pipeline/src/sarstory/invariants.py; the list is in docs/data_contract.md.
import { createHash } from "node:crypto";
import { readFileSync, existsSync, statSync } from "node:fs";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";

const SCHEMA_URL = new URL("../../../schema/chapter.schema.json", import.meta.url);
const TOKEN = /\{stat:([a-z0-9_]+)\}/g;
const FACT = /\{fact:([a-z0-9_]+)\}/g;
const BEATS = 5; // Act I, three Act II beats, Act III
const FLYOVER_SECONDS = 20;
const ANCHORED_UNITS = new Set(["ha", "km2", "dB", "cm/yr"]);
const YEAR = /(?<!\d)(?:19|20)\d{2}(?!\d)/g;
const PAD = 0.1;
const ZOOM = [5, 16];
const PITCH = [0, 85];
export const MAX_FILE_BYTES = 25e6;
export const MAX_TOTAL_BYTES = 150e6;

let compiled;
export function validator() {
  if (!compiled) {
    const schema = JSON.parse(readFileSync(SCHEMA_URL, "utf8"));
    const ajv = new Ajv2020({ allErrors: true, strict: true });
    ajv.addKeyword("tsType"); // read by json-schema-to-typescript only
    addFormats(ajv);
    compiled = ajv.compile(schema);
  }
  return compiled;
}

export function schemaErrors(obj) {
  const validate = validator();
  if (validate(obj)) return [];
  return validate.errors.map((e) => `${e.instancePath || "<root>"}: ${e.message}`);
}

const dupes = (ids) => [...new Set(ids.filter((i, n) => ids.indexOf(i) !== n))];
const inside = (cam, bbox) => {
  const [w, s, e, n] = bbox;
  const [pw, ps, pe, pn] = [w - (e - w) * PAD, s - (n - s) * PAD, e + (e - w) * PAD, n + (n - s) * PAD];
  const [lon, lat] = cam.center;
  return lon >= pw && lon <= pe && lat >= ps && lat <= pn;
};

function checkCamera(where, cam, bbox, errs) {
  if (!inside(cam, bbox)) errs.push(`${where}: center ${JSON.stringify(cam.center)} is outside the AOI bbox padded by 10%`);
  if (cam.zoom < ZOOM[0] || cam.zoom > ZOOM[1]) errs.push(`${where}: zoom ${cam.zoom} outside ${ZOOM}`);
  if (cam.pitch < PITCH[0] || cam.pitch > PITCH[1]) errs.push(`${where}: pitch ${cam.pitch} outside ${PITCH}`);
}

const ascending = (xs) => xs.every((x, i) => i === 0 || x > xs[i - 1]);

/** Invariants for a manifest that already passed the schema. Returns { errors, warnings }. */
export function invariants(obj) {
  const errs = [];
  const warns = [];
  const gen = obj.generated;
  const bbox = obj.aoi.bbox;
  if (!(bbox[0] < bbox[2] && bbox[1] < bbox[3])) errs.push(`aoi.bbox ${JSON.stringify(bbox)} must satisfy west < east and south < north`);

  const layers = new Set(gen.layers.map((l) => l.id));
  const series = new Set(gen.series.map((s) => s.id));
  const stats = new Set(Object.keys(gen.stats));
  const notes = new Set(gen.annotations.map((a) => a.id));
  const sources = new Map(gen.sources.map((s) => [s.id, s]));
  const facts = new Map((obj.facts ?? []).map((f) => [f.id, f]));
  const anchors = obj.scaleAnchors ?? {};
  const landmarks = new Map((obj.landmarks ?? []).map((l) => [l.id, l]));
  const groups = [
    ["fact", (obj.facts ?? []).map((f) => f.id)],
    ["landmark", (obj.landmarks ?? []).map((l) => l.id)],
    ["layer", gen.layers.map((l) => l.id)],
    ["series", gen.series.map((s) => s.id)],
    ["annotation", gen.annotations.map((a) => a.id)],
    ["source", gen.sources.map((s) => s.id)],
    ["beat", obj.beats.map((b) => b.id)],
    ["legend entry", obj.legend.map((e) => e.id)],
  ];
  for (const [kind, ids] of groups) for (const d of dupes(ids)) errs.push(`duplicate ${kind} id '${d}'`);

  for (const entry of obj.legend)
    for (const lid of entry.layerIds) if (!layers.has(lid)) errs.push(`legend ${entry.id}: unknown layer '${lid}'`);

  const fly = gen.flyover;
  const ts = fly.waypoints.map((w) => w.t);
  if (!ascending(ts)) errs.push("flyover.waypoints: t must be strictly ascending");
  if (ts[0] !== 0 || ts[ts.length - 1] !== fly.duration)
    errs.push(`flyover.waypoints: first t must be 0 and last t must equal duration ${fly.duration}`);
  fly.waypoints.forEach((w, i) => checkCamera(`flyover.waypoints[${i}]`, w.camera, bbox, errs));
  if (obj.beats.length !== BEATS) errs.push(`beats: need exactly ${BEATS} (Act I, three Act II beats, Act III), have ${obj.beats.length}`);
  if (fly.duration !== FLYOVER_SECONDS) errs.push(`flyover.duration must be ${FLYOVER_SECONDS} s, is ${fly.duration}`);
  if (!obj.openingCamera) errs.push("openingCamera is missing");
  else {
    checkCamera("openingCamera", obj.openingCamera, bbox, errs);
    if (JSON.stringify(fly.waypoints[fly.waypoints.length - 1].camera) !== JSON.stringify(obj.openingCamera))
      errs.push("flyover.waypoints: the last waypoint camera must equal openingCamera");
  }

  const units = new Map([...Object.entries(gen.stats).map(([k, v]) => [k, v.unit]), ...[...facts].map(([k, f]) => [k, f.unit])]);
  for (const key of Object.keys(anchors)) if (!units.has(key)) errs.push(`scaleAnchors: '${key}' is neither a stat nor a fact`);
  for (const [id, lm] of landmarks) if (!inside({ center: lm.lonLat }, bbox)) errs.push(`landmark ${id}: ${JSON.stringify(lm.lonLat)} is outside the AOI bbox padded by 10%`);
  for (const [id, readings] of Object.entries(gen.landmarkReadings ?? {})) {
    if (!landmarks.has(id)) errs.push(`landmarkReadings: '${id}' is not a landmark`);
    for (const r of readings) if (!layers.has(r.layerId)) errs.push(`landmarkReadings ${id}: layer '${r.layerId}' does not exist`);
  }

  const checkText = (where, text, anchored = false) => {
    for (const m of text.matchAll(TOKEN)) if (!stats.has(m[1])) errs.push(`${where}: token {stat:${m[1]}} has no stat`);
    for (const m of text.matchAll(FACT)) if (!facts.has(m[1])) errs.push(`${where}: token {fact:${m[1]}} has no fact`);
    if (anchored)
      for (const m of [...text.matchAll(TOKEN), ...text.matchAll(FACT)])
        if (ANCHORED_UNITS.has(units.get(m[1])) && !(m[1] in anchors))
          errs.push(`${where}: '${m[1]}' (${units.get(m[1])}) needs a scaleAnchors entry`);
    if (/\d/.test(text.replace(TOKEN, "").replace(FACT, "").replace(YEAR, "")))
      warns.push(`${where}: digits in text; use a {stat:key} or {fact:key} token`);
  };

  for (const beat of obj.beats) {
    const st = beat.stage;
    const b = beat.id;
    for (const field of ["left", "right", "flyoverLayer"])
      if (field in st && !layers.has(st[field])) errs.push(`beat ${b}: stage.${field} '${st[field]}' is not a layer`);
    for (const lid of st.overlays ?? []) if (!layers.has(lid)) errs.push(`beat ${b}: overlay '${lid}' is not a layer`);
    for (const nid of st.annotations ?? []) if (!notes.has(nid)) errs.push(`beat ${b}: annotation '${nid}' does not exist`);
    const f = st.flyover;
    if (!(f.from >= 0 && f.from <= f.to && f.to <= fly.duration))
      errs.push(`beat ${b}: flyover window ${f.from}..${f.to} must lie within 0..${fly.duration}`);
    if (st.camera) checkCamera(`beat ${b} camera`, st.camera, bbox, errs);
    if (beat.readout) {
      if (!series.has(beat.readout.seriesId)) errs.push(`beat ${b}: readout series '${beat.readout.seriesId}' does not exist`);
      if (beat.readout.statKey && !stats.has(beat.readout.statKey)) errs.push(`beat ${b}: readout stat '${beat.readout.statKey}' does not exist`);
    }
    checkText(`beat ${b} body`, beat.body, true);
  }
  checkText("action.body", obj.action.body);
  for (const m of obj.action.metrics)
    if (m.statKey && !stats.has(m.statKey)) errs.push(`action metric '${m.label}': stat '${m.statKey}' does not exist`);

  for (const name of ["impact", "dem"])
    for (const sid of gen[name]?.sourceIds ?? []) if (!sources.has(sid)) errs.push(`${name}: unknown source '${sid}'`);
  const groupsWithStatus = [["layer", gen.layers], ["series", gen.series], ...(gen.footprint ? [["footprint", [gen.footprint]]] : [])];
  for (const [kind, items] of groupsWithStatus)
    for (const it of items) {
      const where = `${kind} ${it.id ?? ""}`.trim();
      for (const sid of it.sourceIds) if (!sources.has(sid)) errs.push(`${where}: unknown source '${sid}'`);
      const synthetic = it.sourceIds.some((s) => sources.get(s)?.mission === "Synthetic");
      if (it.status === "illustrative" && !synthetic) errs.push(`${where}: illustrative data must cite a Synthetic source`);
      if (it.status !== "illustrative" && synthetic) errs.push(`${where}: status '${it.status}' cannot cite a Synthetic source`);
    }
  for (const s of gen.series) {
    if (!ascending(s.points.map((p) => p.t))) errs.push(`series ${s.id}: points must have strictly ascending, unique dates`);
    if (s.reference && !ascending(s.reference.points.map((p) => p.t)))
      errs.push(`series ${s.id} reference: points must have strictly ascending, unique dates`);
  }
  return { errors: errs, warnings: warns };
}

/** Layer and video files exist and match their recorded bytes and sha256. */
export function assetErrors(obj, publicDir) {
  const errs = [];
  const sha = (p) => createHash("sha256").update(readFileSync(p)).digest("hex");
  for (const l of obj.generated.layers) {
    for (const key of ["cog", "preview"]) if (!existsSync(new URL(l[key], publicDir))) errs.push(`layer ${l.id}: ${key} file ${l[key]} is missing`);
    const cog = new URL(l.cog, publicDir);
    if (existsSync(cog)) {
      if (statSync(cog).size !== l.bytes) errs.push(`layer ${l.id}: bytes ${statSync(cog).size} != manifest ${l.bytes}`);
      else if (sha(cog) !== l.sha256) errs.push(`layer ${l.id}: sha256 does not match ${l.cog}`);
    }
  }
  const v = obj.generated.flyover.video;
  if (v) for (const key of ["src", "poster"]) if (!existsSync(new URL(v[key], publicDir))) errs.push(`flyover video: ${key} file ${v[key]} is missing`);
  for (const [name, item, key] of [["dem", obj.generated.dem, "cog"], ["impact", obj.generated.impact, "geojson"]]) {
    if (!item) continue;
    const f = new URL(item[key], publicDir);
    if (!existsSync(f)) errs.push(`${name}: file ${item[key]} is missing`);
    else if (statSync(f).size !== item.bytes) errs.push(`${name}: bytes ${statSync(f).size} != manifest ${item.bytes}`);
    else if (sha(f) !== item.sha256) errs.push(`${name}: sha256 does not match ${item[key]}`);
  }
  const files = [
    ...(obj.landmarks ?? []).filter((l) => l.photo).map((l) => [`landmark ${l.id} photo`, l.photo.src]),
    ...Object.entries(obj.soundscape ?? {}).map(([k, snd]) => [`soundscape ${k}`, snd.src]),
  ];
  for (const [where, src] of files) if (!existsSync(new URL(src, publicDir))) errs.push(`${where}: file ${src} is missing`);
  return errs;
}

/** Full check of one manifest: schema, then invariants and assets. */
export function validateChapter(obj, publicDir) {
  const errors = schemaErrors(obj);
  if (errors.length) return { errors, warnings: [] };
  const inv = invariants(obj);
  return { errors: [...inv.errors, ...(publicDir ? assetErrors(obj, publicDir) : [])], warnings: inv.warnings };
}
