# Decision log

Interface freeze: `schema/chapter.schema.json` changes are additive only (new optional keys, new enum values). A breaking change bumps `schemaVersion` and needs an entry here. Newest entries last.

## 2026-11-14: project decisions (user-approved plan)

1. **Chapters, in order:** `rondonia` (forest, HV backscatter in dB), `okanagan` (fire, burned hectares), `san-joaquin` (ground, subsidence in cm). Other catalog locations are out of scope for this release.
2. **Data ladder:** NISAR first. If a chapter has no usable NISAR track covering both windows, use a labeled real fallback (Sentinel-1 OPERA RTC or DISP-S1 from ASF). If that is also unavailable, ship a layer with status `illustrative`. Every layer carries a status and the site shows it.
3. **Flyover:** the live MapLibre terrain flyover, driven by the manifest waypoints, ships first. Pre-rendered PyVista videos (milestone 4) use the same waypoints and timeline and replace the live flyover for a chapter when `generated.flyover.video` exists.
4. **Hosting and publishing:** no push, GitHub repo creation or deploy happens without asking the user.
5. **Credentials:** Earthdata Login is set up by the user in their own terminal. No credential enters the repo or a chat.

## 2026-11-14: contract details

- Schema dialect is JSON Schema 2020-12. TypeScript types are generated from it (`web/src/types/chapter.ts`) and never edited by hand. Python validates with `jsonschema`, the web build validates with `ajv`.
- Manifests live at `web/public/chapters/<slug>.json`. Authored fields are edited by hand. `generated` is written by `sar build` and `sar fixture`.
- `ImpactMetric` is a union of two shapes: `{label, statKey, source}` or `{label, value, unit, source}`. The union is expressed as two named definitions so the generated TypeScript is a clean discriminated union.
- Camera interpolation is specified in `docs/data_contract.md` and pinned by `schema/golden/camera_interp.json`. Python and TypeScript both test against that file.
- COGs for the web are EPSG:3857, GoogleMapsCompatible, 256 px blocks, with overviews, because `@geomatico/maplibre-cog-protocol` rejects other projections.

## 2026-11-14: schema additions made before the freeze (end of milestone 1)

- `Unit` gained `count` and `cm/month`. Stats such as `n_dates`, `n_pairs` and `rate_cm_per_month` need them; `ratio` would mislabel a count.
- `hv_change` stores the **HV drop in dB (before minus after), positive meaning loss**, as a float32 ramp with NaN where the drop is below the threshold. Domain 2 to 10 dB, scheme `BrewerYlOrRd9`, so the browser draws only lost pixels and needs no reversed ramp.
- `displacement` uses `BrewerRdBu11` over -15 to 15 cm, so subsidence (negative) is red and uplift is blue.
- The generated-data source type is named `Source`. The citation attached to an impact metric is named `MetricSource`.
