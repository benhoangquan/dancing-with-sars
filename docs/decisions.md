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

## 2026-11-14: milestone 2 decisions

- **Overlays sit on the after side only.** A beat's `stage.overlays` (for example the HV drop mask) are drawn on the right-hand map in radar and split modes, not on both. The mask is the result of comparing the two scenes; drawing it on the "before" half showed clearing that had not happened yet and made the swipe show no difference. This replaces the plan's "overlays drawn on both sides".
- **Scroll engine:** one `requestAnimationFrame` loop measures each `[data-section]` against the viewport center line (`locate` in `src/lib/beats.ts`) instead of an IntersectionObserver plus a scroll listener. Same behavior, one code path, and the pure `locate` function is unit-tested.
- **Annotations use deck.gl on a separate canvas.** MapLibre's 3D terrain does not drape deck.gl layers, so each point is lifted to `map.queryTerrainElevation` and drawn as a 3D position. Areas are densified so outlines follow the relief.
- **Chart colors.** Data marks use steps of the chapter hues at OKLCH lightness 0.66 (`src/lib/chartColors.ts`), validated with the dataviz skill's `validate_palette.js` against the card surface. The vivid accents stay on UI chrome. The reference series is `#6e6e73`, chosen because the first gray tried (`#8e8e93`) failed the normal-vision floor against the blue. Cards that hold data marks use a denser frosted surface (`glass-data`, 88% opaque) so a 2px line stays legible over bright imagery; text cards keep the 72% glass of the brief.
- **`tabular-nums`** is used on every changing counter, as the brief asks, even though the dataviz skill prefers proportional figures for large static numbers: a live value that changes width as the cursor moves would jitter.
- **Headless WebGL in tests.** On a machine whose `DISPLAY` points at an unreachable X server, ANGLE's SwiftShader backend fails (`xcb_connect() failed`) and Chromium has no WebGL. The Playwright config removes `DISPLAY` and `WAYLAND_DISPLAY` from the browser's environment only.
- **Debug handle.** `?debug` in the URL exposes the two MapLibre maps as `window.__sar`, for tests and troubleshooting.

## 2026-11-14: milestone 3, data discovery (no login needed)

- **All three chapters have real NISAR data**, so the first rung of the data ladder is feasible everywhere. `sar discover` writes `pipeline/reports/<slug>-availability.md`; the table is in `DATA_SOURCES.md`.
- **The gate groups by track, not by frame.** The first version grouped by `STACK_ID` (track, direction, frame) and reported "no NISAR data" for Rondonia, because its 100 by 77 km study area is wider than one frame (each of the nearest frames covered 37 to 81 percent). One pass is cut into consecutive frames, so an acquisition is now every frame of one pass on one day, with coverage measured as the union of the footprints. `fetch` must read and mosaic every frame of an acquisition. A test reproduces the two-frame case.
- **Provisional is the data of record.** Validated (`_V1`) releases begin 2026-10-22 over these areas and cannot give a before scene. Do not mix collections inside one comparison.
- **Maturity labels.** `maturity_of` classifies by name: a name containing PROVISIONAL or BETA is that maturity, and only a plain `_V1` is validated. An earlier version checked the `V1` suffix first and labeled provisional data as validated; a test caught it.
- **Interferogram windows overlap rather than contain.** A pair belongs to the displacement series if its date span touches the window, since a real pair for the 2026-06-17 cycle has reference date 2026-06-16.
- **Next step needs the user:** Earthdata Login. Search is public; reading granule contents is not. Run `cd pipeline && uv run python -c "import earthaccess; earthaccess.login(strategy='interactive', persist=True)"` in your own terminal. `~/.netrc` exists but has no Earthdata entry as of this date.

## 2026-11-14: milestone 3, first real data (Earthdata Login done by the user)

**Status: `rondonia` is real. `okanagan` and `san-joaquin` were fetched and analyzed but stay `illustrative`, for the reasons below.**

- **Fast reader.** `nisar/hdf5.py` fetches only the byte ranges of the chunks under the study area, in parallel, and decodes them (gunzip, unshuffle). A window took 5 to 7 s against 31 to 129 s through h5py over HTTPS, transferring about 38 MB of a 1.9 GB file, with values identical to h5py (tested on synthetic files with gzip, shuffle, fletcher32, partial edge chunks and unwritten chunks). About 25 s per GCOV granule.
- **One global 60 m lattice.** GCOV windows are block-averaged (linear power) on cells whose edges are multiples of 60 m in UTM, so frames of one pass and every date line up exactly and are mosaicked without resampling.
- **Rondonia (track 161_A, frames 172 and 173, 7 acquisitions, `NISAR_L2_GCOV_PROVISIONAL_V1`).** 374 ha of loss, mean HV drop 6.0 dB (-14.0 to -20.0 dB). The stable-forest reference stays within 0.6 dB across all dates, and the loss mask is a few compact field-shaped patches in the north, not speckle. The forest cutoff (HV above -15 dB) comes from the real HV distribution, which is bimodal: pasture -17 to -21 dB, forest -10 to -12 dB. The fixture's invented 7,648 ha was far too large; the measured figure is the conservative one (3 dB, 1 ha minimum patch). Optical layers are real HLS median composites (48 scenes) read from Planetary Computer.
- **Okanagan: no detectable burn scar inside the catalog bounding box.** Raw before/after composites flag land that dropped in July and recovers by September, which is moisture and phenology, not fire (a burn scar is permanent). After removing each date's regional offset, the strongest coherent drops are about 1.3 dB over at most 288 ha at the area's northern edge, near (-119.60, 50.24). The Bradley Creek fire (about 2,800 ha, Okanagan Indian Band land at the north end of the lake) straddles that edge, so the box cuts it off. The same track and frame (`071_D`, 063) cover a box shifted north, `[-119.80, 50.05, -119.20, 50.45]`, with the same 2 + 2 acquisitions. **Decision for the user:** shift the area north (re-fetch is about 6 minutes), or keep the catalog box and the illustrative layers. The cached tiles stay in `pipeline/cache/okanagan`.
- **San Joaquin: the interferogram sums are not reliable enough to publish.** Summing raw sequential pairs gave 15 to 25 cm of spread within 12 days and unwrapping steps of one fringe (12.1 cm). Removing the ionosphere phase screen, keeping only the dominant connected component of each pair, and removing a fitted plane cleaned the series (0 to -10.3 cm, smooth, with a flat reference), but the map is not a compact bowl: about half the area is unusable in some pair, the sinking and rising regions are diffuse, and 42 percent of the sinking area is within 5 km of the boundary. That looks like residual atmosphere and orbit error mixed with any real motion. A defensible result needs more: an independent stable reference point, tropospheric correction, a stricter coherence mask, and a check against known subsidence areas. The cache and the corrections are kept (`gunw.py`, `gunw_analysis.py`, `build_gunw.py`, all tested).
- **Story cameras follow the data.** The real clearings are about 1 by 2 km in a 99 by 77 km area, so the radar beat and the end of the flyover are aimed at the largest one. Overlays stay on the after side only. The redundant pin was dropped so labels do not collide.
- **Legend colors come from the real composites** (forest `#B0D853`, pasture `#646E7A`, water `#3E457E`), not the fixture's.
- **Tests no longer depend on which data the repo holds.** Negative tests start from a freshly built illustrative manifest (pipeline) or a frozen one (`web/tests/fixtures/rondonia.illustrative.json`). Both real builds run end to end offline on synthetic caches with only the optical step stubbed.
- **`maturity_of`, drawer provenance.** Real chapters state "Measured from NISAR data", with a provisional-release caveat. Illustrative and fallback chapters keep their warnings.

## 2026-11-14: milestone 3, the other catalog locations

The user asked for the remaining catalog locations to be processed, with `okanagan` and `san-joaquin` kept illustrative. Each location was fetched and analyzed with the same rule as before: a "measured" claim needs compact patches, persistence across dates, a flat stable reference, and a position that fits the geography on the map. Results so far (every analysis ran on `NISAR_L2_*_PROVISIONAL_V1`):

- **Madre de Dios (GCOV): no chapter.** The loss mask is 119 scattered patches of 8 ha or less, the size of speckle, not mining pits or clearings. Nothing coherent to aim a camera at.
- **Demak (GCOV): no chapter.** The loss patches are inland rice paddies: median distance to the sea 14 km, none within 3 km of the coast. The area series stays high after the first drop and the stable reference is flat, so the signal is the crop cycle. The catalog story (mangrove and coastal land loss) is not in this data.
- **Greenland (GOFF, track 131_A_037, 9 sequential pairs, 2026-06-23 to 2026-10-21): no chapter.** The reader, analysis and `SarSpeedDark` ramp are built and tested (`goff.py`, `goff_analysis.py`). The result does not reproduce:
  - Two consecutive 12-day pairs differ by a median 37 to 54 percent per pixel over the ice at the product's SNR cutoff of 6. At SNR 20 or more they differ by 11 to 24 percent, but only about 7 percent of pixels qualify.
  - The median map of five pairs against the median of the other four differs by a median 17 to 30 percent (90th percentile 45 to 90 percent), at every SNR cutoff tried (6, 10, 15).
  - Offsets saturate at about 590 m (the search window): 49 m/day in a 12-day pair and 24.5 m/day in the 24-day pair, so the fast core is cut off and the series of the fastest point alternates between 18 and 45 m/day.
  - Layer 2 gives the same saturation. Layer 3 (smoothed) agrees between pairs (median 9 percent difference where speed exceeds 5 m/day) but peaks at 8.9 m/day, several times below the speed of the outlet glaciers in this area.
  - The maps show speckle across the trunk of the glacier in most pairs, with a coherent patch near the front only in some. A speed map from this would look like data without being data.
  - The schema additions for it stay (`count`, `cm/month`, `m/day` units, `speed` layer and series kinds); they are additive and used by tests. The cache stays in `pipeline/cache/greenland`.
