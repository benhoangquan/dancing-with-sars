# Chapter data contract (`schemaVersion` "1")

A chapter is one JSON manifest at `web/public/chapters/<slug>.json`. The file name equals `slug`. The canonical schema is `schema/chapter.schema.json` (JSON Schema 2020-12). Types for the web are generated from it by `npm run gen:types` into `web/src/types/chapter.ts`.

Two kinds of keys live in a manifest:

- **Authored** (edited by hand): `slug`, `order`, `theme`, `accent`, `kicker`, `title`, `dek`, `aoi` (with `iso3`), `globe.pin`, `openingCamera`, `radar`, `legend`, `beats`, `facts`, `scaleAnchors`, `landmarks`, `action` (with `local` for the "Act Where You Live" tab). `soundscape` is written by `sar audio`.
- **Generated** (`generated`, never edited by hand): `layers`, `series`, `stats`, `flyover`, `annotations`, `sources`, `footprint` (written by `sar build` and `sar fixture`), `dem` (`sar dem`), `impact` and `impact_*` stats (`sar overture`), `landmarkReadings` (`sar landmarks`), plus `pipelineVersion` and `builtAt`. A rebuild keeps the parts other commands own (`manifest.carry_extras`).

Authored objects reject unknown keys (`additionalProperties: false`).

## Conventions

- Coordinates are WGS84 `[lon, lat]`. Bounding boxes are `[west, south, east, north]`.
- Dates are `YYYY-MM-DD`. A date range is `YYYY-MM-DD/YYYY-MM-DD`.
- An `AssetPath` is relative to `web/public`, for example `data/rondonia/sar_after.tif`. It has no leading slash, no scheme and no `..`.
- Camera values follow MapLibre: `zoom`, `pitch` in degrees from the vertical, `bearing` in degrees clockwise from north.
- Numbers in text are not typed by hand. Text uses `{stat:key}` tokens that resolve against `generated.stats` (measured by the pipeline) or `{fact:key}` tokens that resolve against `facts` (sourced numbers from published studies). Impact metrics either point at a stat or carry a value with a cited source.
- Every hectare, km², dB or cm/yr figure in a beat has a `scaleAnchors` entry naming its everyday comparison (`central-park`, `football-pitch`, `manhattan`, `echo-power`, `per-decade`). The comparison is computed in `web/src/lib/references.ts` from sourced constants.
- A chapter has exactly five beats: Act I (flyover), three Act II beats (radar) and Act III (action). The flyover lasts 20 s and its last waypoint is `openingCamera`, where the Act II map starts.

## Layer ids

`optical_baseline`, `optical_before`, `optical_after`, `optical_smoke`, `optical_2026`, `sar_before`, `sar_after`, `sar_2026`, `hv_change`, `displacement`, `coherence`. A chapter uses a subset.

| Chapter | Layers | Series | Stats | Facts |
|---|---|---|---|---|
| `rondonia` | `optical_before`, `optical_after`, `sar_before`, `sar_after`, `hv_change` | `hv_cleared` (with a reference forest) | `cleared_ha`, `hv_drop_db`, `hv_before_db`, `hv_after_db`, `n_dates`, `impact_road_km_near` | none |
| `demak` | `optical_baseline` (2017), `optical_2026`, `sar_2026` | none | `n_dates` | `land_lost_ha`, `subsidence_max_cmyr`, `subsidence_common_cmyr` |
| `okanagan` | `optical_baseline` (2025), `optical_smoke`, `optical_after`, `sar_before`, `sar_after` | `hv_burned` (with the ring of forest around it) | `burn_hv_drop_db`, `placebo_sd_db`, `burned_ha` (BC Wildfire Service), `smoke_cloud_pct`, `n_dates`, `impact_buildings_near` | none |

`crosswhite`, `sinlahekin` and `little-giant` have the same layers, series and stats as `okanagan` (perimeters from WFIGS). Imagery layers (`kind` optical or sar-composite) are JPEG COGs with a mask band and WebP previews; layers that carry values or exact colors stay lossless.

San Joaquin is off the site in v1; its authored manifest lives in `pipeline/tests/data/` so its fixture and GUNW build stay tested.

## Layer statuses

`real` is NISAR data processed by the pipeline. `fallback` is other real data, labeled: a mapped fire perimeter (BC Wildfire Service) or a square of a cited area. `illustrative` is synthetic and cites a source with mission `Synthetic`. The site shows the status in the legend.

## COG rules

Every `Layer.cog` is a Cloud-Optimized GeoTIFF in EPSG:3857 with GoogleMapsCompatible tiling, 256 px blocks and overviews, because the browser reads it through `@geomatico/maplibre-cog-protocol`. `render.type` is `rgba` (uint8 RGBA) or `ramp` (float32 with NaN as no data, colored by a `#color:` fragment). `Layer.preview` is an EPSG:3857 PNG used as an image-source fallback.

## Camera interpolation

`cameraAt(waypoints, t)` is implemented in `pipeline/src/sarstory/flyover/camera.py` and `web/src/lib/camera.ts`. Both follow this spec and both are tested against `schema/golden/camera_interp.json`.

1. Clamp `t` to `[waypoints[0].t, waypoints[last].t]`.
2. Pick the segment `i` with `w[i].t <= t <= w[i+1].t`. At `t == w[last].t` use the last segment with `u = 1`.
3. `u = (t - t0) / (t1 - t0)` and `s = u * u * (3 - 2 * u)`.
4. `center.lon`, `center.lat`, `zoom` and `pitch` are `a + (b - a) * s`.
5. Bearing takes the shortest arc. `d = mod(b1 - b0 + 540, 360) - 180`, where `mod(x, m) = ((x % m) + m) % m`. `bearing = norm(b0 + d * s)`, where `norm(x) = mod(x + 180, 360) - 180`, giving a value in `[-180, 180)`.

## Validation invariants

`web/scripts/validate-chapters.mjs` (the `prebuild` step and CI) checks what the schema cannot express:

- Every layer, series, stat and annotation id referenced by beats, legend and metrics resolves.
- Every `{stat:key}` token resolves.
- Flyover windows satisfy `0 <= from <= to <= duration`. Waypoint `t` values ascend, start at 0 and end at `duration`.
- Camera centers lie inside the AOI bounding box padded by 10 percent. Zoom is 5 to 16, pitch 0 to 85, bearing -180 to 180.
- `bbox` has `west < east` and `south < north`. Series points are sorted by date.
- Every `AssetPath` exists, and its byte count and sha256 match the layer entry.
- File and total size budgets hold (25 MB per file, 150 MB total under `web/public/data`).
- `illustrative` layers cite a source with mission `Synthetic`.
- Body text with raw numbers other than years produces a warning.
- Exactly five beats; flyover duration 20 s; `openingCamera` present, inside the AOI and equal to the last waypoint.
- `{fact:key}` tokens resolve; every ha, km², dB or cm/yr figure in a beat has a scale anchor, and every anchor names a stat or fact.
- Landmarks lie inside the padded AOI; `landmarkReadings` name existing landmarks and layers.
- `dem`, `impact` and `footprint` cite known sources; their files exist and match their bytes and sha256.
