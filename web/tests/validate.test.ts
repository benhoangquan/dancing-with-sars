import { readFileSync, readdirSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { invariants, schemaErrors, validateChapter } from "../scripts/lib/validate.mjs";

const publicDir = new URL("../public/", import.meta.url);
const chaptersDir = new URL("chapters/", publicDir);
const slugs = readdirSync(chaptersDir).filter((f) => f.endsWith(".json")).map((f) => f.replace(".json", "")).sort();
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Manifest = any;
const load = (slug: string): Manifest => JSON.parse(readFileSync(new URL(`${slug}.json`, chaptersDir), "utf8"));
// The mutation tests below change one thing and expect a specific error, so they start from a known illustrative
// manifest (written by the pipeline's own fixture builder), not from whatever real data the repo holds.
const illustrative: Manifest = JSON.parse(readFileSync(new URL("./fixtures/rondonia.illustrative.json", import.meta.url), "utf8"));
const clone = (): Manifest => structuredClone(illustrative);

describe("repo manifests", () => {
  it("include the v1 chapters", () => expect(slugs).toEqual(expect.arrayContaining(["okanagan", "rondonia"])));
  for (const slug of slugs) {
    it(`${slug} passes schema, invariants and asset checks with no warnings`, () => {
      const { errors, warnings } = validateChapter(load(slug), publicDir);
      expect(errors).toEqual([]);
      expect(warnings).toEqual([]);
    });
  }
});

const schemaCases: [string, (o: Manifest) => void][] = [
  ["unknown top-level key", (o) => (o.extra = 1)],
  ["too few beats", (o) => (o.beats = o.beats.slice(0, 3))],
  ["bad accent", (o) => (o.accent = "green")],
  ["bbox out of range", (o) => (o.aoi.bbox = [-200, 0, 0, 1])],
  ["unknown unit", (o) => (o.generated.stats.cleared_ha.unit = "furlongs")],
  ["asset path with leading slash", (o) => (o.generated.layers[0].cog = "/data/x.tif")],
  ["asset path with ..", (o) => (o.generated.layers[0].preview = "data/../x.png")],
  ["asset path with scheme", (o) => (o.generated.layers[0].cog = "https://x.test/a.tif")],
  ["http organization url", (o) => (o.action.organizations[0].url = "http://example.org")],
  ["metric with statKey and value", (o) => Object.assign(o.action.metrics[0], { value: 1, unit: "ha" })],
  ["metric with neither", (o) => delete o.action.metrics[0].statKey],
  ["one organization", (o) => (o.action.organizations = o.action.organizations.slice(0, 1))],
  ["explainer too long", (o) => (o.radar.explainer = "x".repeat(401))],
  ["bad sha256", (o) => (o.generated.layers[0].sha256 = "abc")],
  ["series with one point", (o) => (o.generated.series[0].points = o.generated.series[0].points.slice(0, 1))],
  ["swipe above one", (o) => (o.beats[0].stage.swipe = 1.5)],
  ["pitch above 85", (o) => (o.generated.flyover.waypoints[0].camera.pitch = 90)],
  ["status outside enum", (o) => (o.generated.layers[0].status = "fake")],
  ["ramp without domain", (o) => (o.generated.layers[4].render = { type: "ramp", scheme: "x", unit: "dB" })],
];
describe("schema rejects", () => {
  for (const [name, mutate] of schemaCases)
    it(name, () => {
      const o = clone();
      mutate(o);
      expect(schemaErrors(o).length).toBeGreaterThan(0);
    });
});

const invariantCases: [string, (o: Manifest) => void, string][] = [
  ["unknown token", (o) => (o.beats[2].body = "Fell by {stat:nope}."), "token"],
  ["beat layer missing", (o) => (o.beats[0].stage.left = "ghost"), "stage.left"],
  ["overlay missing", (o) => (o.beats[2].stage.overlays = ["ghost"]), "overlay"],
  ["annotation missing", (o) => (o.beats[2].stage.annotations = ["ghost"]), "annotation"],
  ["readout series missing", (o) => (o.beats[2].readout.seriesId = "ghost"), "readout series"],
  ["readout stat missing", (o) => (o.beats[2].readout.statKey = "ghost"), "readout stat"],
  ["legend layer missing", (o) => (o.legend[0].layerIds = ["ghost"]), "legend"],
  ["metric stat missing", (o) => (o.action.metrics[0].statKey = "ghost"), "metric"],
  ["window beyond duration", (o) => (o.beats[0].stage.flyover.to = 999), "flyover window"],
  ["window reversed", (o) => Object.assign(o.beats[0].stage.flyover, { from: 9, to: 3 }), "flyover window"],
  ["waypoints not starting at 0", (o) => (o.generated.flyover.waypoints[0].t = 1), "first t"],
  ["waypoint t descending", (o) => (o.generated.flyover.waypoints[1].t = 40), "ascending"],
  ["camera outside AOI", (o) => (o.generated.flyover.waypoints[1].camera.center = [0, 0]), "outside the AOI"],
  ["zoom out of range", (o) => (o.generated.flyover.waypoints[1].camera.zoom = 3), "zoom"],
  ["series unsorted", (o) => o.generated.series[0].points.reverse(), "ascending"],
  ["illustrative without synthetic", (o) => (o.generated.sources[0].mission = "NISAR"), "Synthetic"],
  ["real citing synthetic", (o) => (o.generated.layers[0].status = "real"), "cannot cite"],
  ["unknown source", (o) => (o.generated.layers[0].sourceIds = ["ghost"]), "unknown source"],
  ["duplicate beat id", (o) => (o.beats[1].id = o.beats[0].id), "duplicate beat"],
  ["bbox inverted", (o) => (o.aoi.bbox = [-62.9, -10.4, -63.8, -9.7]), "west < east"],
  ["four beats", (o) => o.beats.pop(), "exactly 5"],
  ["flyover not 20 s", (o) => (o.generated.flyover.duration = 36), "must be 20"],
  ["no opening camera", (o) => delete o.openingCamera, "openingCamera is missing"],
  ["opening pose drifts", (o) => (o.openingCamera.pitch = 40), "must equal openingCamera"],
  ["unknown fact token", (o) => (o.beats[2].body = "Sank {fact:nope}."), "{fact:nope}"],
  ["hectares without anchor", (o) => delete o.scaleAnchors.cleared_ha, "needs a scaleAnchors"],
  ["anchor for nothing", (o) => (o.scaleAnchors.ghost = "central-park"), "neither a stat"],
  ["landmark outside AOI", (o) => (o.landmarks = [{ id: "far", label: "Far", lonLat: [0, 0] }]), "landmark far"],
];
describe("invariants reject", () => {
  for (const [name, mutate, needle] of invariantCases)
    it(name, () => {
      const o = clone();
      mutate(o);
      const { errors } = invariants(o);
      expect(errors.some((e: string) => e.includes(needle))).toBe(true);
    });
  it("warn on digits in text but not on years", () => {
    const o = clone();
    o.beats[0].body = "Roads reached 40 km by 2026.";
    expect(invariants(o).warnings.some((w: string) => w.includes("digits"))).toBe(true);
    o.beats[0].body = "Data from 2026 and 1999.";
    expect(invariants(o).warnings).toEqual([]);
  });
});
