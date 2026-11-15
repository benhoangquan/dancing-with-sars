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

## 2026-11-14: milestone 1 build decisions

- **Toolchain:** Node 24 LTS (24.22.3, checksum verified) is installed under `~/.local/opt/node-v24` with `node`, `npm` and `npx` linked into `~/.local/bin`. Python is 3.13 through `uv`.
- **Versions in use:** Next 16.4.6, React 19.3, Tailwind 4.3 (through `@tailwindcss/turbopack`, as the Next 16.4 scaffold configures it), `maplibre-gl` 5.24.1, `@deck.gl/*` 9.4.1, `@geomatico/maplibre-cog-protocol` 0.10.0, `motion` 14, `zustand` 5, `vitest` 5, `@playwright/test` 1.65.
- **MapLibre 5, not 6:** deck.gl 9.4 and the COG protocol both allow MapLibre 6 in their peer ranges, but nothing confirms deck.gl's interleaved overlay works on 6 at runtime. Revisit only if a MapLibre 6 feature is needed.
- **`@types/node` 24:** vitest 5 needs 22 or 24 and up, and it matches the installed Node.
- **`tsType` in the schema:** `prefixItems` tuples generate `never[]` in `json-schema-to-typescript`. The four tuple definitions (`LonLat`, `BBox`, `NumberPair`, `DatePair`) carry a `tsType` annotation. Ajv registers it as a keyword; `jsonschema` ignores it.
- **Next config:** the scaffold's `cacheComponents` and `partialPrefetching` are removed; a static export needs neither. The layout is typed with `ReactNode` because the generated `LayoutProps` global does not exist before the first build. Geist web fonts are removed in favour of the system font stack.
- **Fixture data:** the three fixtures are synthetic, deterministic (fixed seeds) and labeled `illustrative`. Scale was checked against known events: the Okanagan scar is about 6,700 ha, near the August 2026 fire sizes reported in the news.
- **Authored content:** impact metrics in milestone 1 point at this project's own stats. Externally sourced numbers (for example fire statistics) are added in milestone 3 after the source is read. Organization links were checked on 2026-11-14: where a guessed donate path returned 404 (One Tree Planted, American Forests, Self-Help Enterprises), the CTA links the homepage.

## Open items for milestone 3

- American Forests describes itself as the oldest national conservation nonprofit in the United States. The Okanagan chapter is in British Columbia, so a Canadian organization may fit better. The user decides.
- Add a beat or metric on what the Okanagan fires did on the ground, sourced from BC Wildfire Service or a primary news report, once read.
- Add a sourced metric on groundwater pumping and subsidence (for example a USGS San Joaquin Valley page) to the San Joaquin chapter.
