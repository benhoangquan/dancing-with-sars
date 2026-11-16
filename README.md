# Dancing with the SARs

An interactive scrollytelling site that turns NASA-ISRO NISAR L-band radar data into six short stories about forests, fires and flooded land. Built for the 2026 NASA Space Apps Challenge.

<!-- demo: add docs/demo.gif and an image link here once the recording exists -->

The reader starts on the NASA Blue Marble globe and picks a red pin. Each place has three acts: a 20-second terrain flyover, a radar stage with a before/after swipe (landmarks, roads and buildings overlaid), and an action sheet with organizations to contact and a "your city scale" comparison. Grey pins mark places where we checked NISAR data and found no change we could defend.

## Architecture

```
NISAR GCOV HDF5 (ASF DAAC)  ─┐
HLS optical, Copernicus DEM ─┼─▶  pipeline/  (Python, uv, CLI `sar`)  ─▶  web/public/  ─▶  web/  (Next.js static export)
fire perimeters, Overture   ─┘     window read, change maps, COG          chapters/*.json       MapLibre GL JS, deck.gl,
                                   writer, manifest builder                COGs, WebP, audio     Tailwind CSS
```

| Path | Contents |
|---|---|
| `pipeline/` | Offline Python package `sarstory`: NISAR search, windowed reads from the HDF5 granules, change detection against a placebo area, Cloud-Optimized GeoTIFF writing, terrain, buildings, landmarks, manifests |
| `schema/` | `chapter.schema.json`, the data contract between pipeline and site, plus golden test vectors shared by the Python and TypeScript tests |
| `web/` | Static site. Types are generated from the schema; Vitest unit tests and Playwright smoke tests run against the built `out/` folder |
| `docs/` | Data contract notes and the decision log |

Every layer in a chapter carries a provenance status that the site shows in its legend: `real` (NISAR processed by this pipeline), `fallback` (other real data, labeled), or `illustrative` (synthetic, labeled). Numbers in story text come from generated stat tokens, not typed by hand. The CI workflow runs `ruff`, `pytest` and `npm run verify` on every push.

## Results

NISAR provisional GCOV, HV backscatter, before versus after. For fires, the drop is measured inside the perimeter relative to the surrounding land and compared against a placebo area.

| Place | Measurement | Placebo spread | Status |
|---|---|---|---|
| Rondônia, Brazil | 374 ha of clearing, mean HV drop 6.0 dB | n/a | measured with NISAR |
| Okanagan, British Columbia | 0.8 dB relative drop inside the fire perimeter (BC Wildfire Service) | 0.2 dB | measured; perimeter is a labeled fallback |
| Sinlahekin fire, Washington | 1.04 dB drop; 2,543 mapped buildings within 1 km | 0.11 dB | measured; perimeter from NIFC WFIGS |
| Little Giant fire, Washington | 0.99 dB drop; 345 mapped buildings within 2 km | 0.07 dB | measured; perimeter from NIFC WFIGS |
| Crosswhite fire, Oregon | 1.0 dB drop; 850 mapped buildings within 2 km | 0.05 dB | measured; perimeter from NIFC WFIGS |
| Demak, Indonesia | Radar imagery of villages in tidal water; subsidence and land-loss figures cited from Deltares (2021) | n/a | NISAR imagery, cited numbers |

Six other candidate sites (Tartar, San Joaquin, Madre de Dios, Sundarbans, Alaska, Greenland) were fetched and dropped: the signal was inside the placebo spread, speckle-sized, one acquisition's edge, or did not reproduce. The reasons are in `docs/decisions.md`. Sources, collections and licenses are in [DATA_SOURCES.md](DATA_SOURCES.md).

## Quickstart

The data under `web/public/` is committed, so the site builds without credentials.

```bash
cd pipeline && uv sync && uv run sar validate
cd ../web && npm ci && npm run build
npx serve out          # open http://localhost:3000, or http://localhost:3000/#place=demak
```

Rebuilding the data needs an Earthdata Login in `~/.netrc`. See [CLAUDE.md](CLAUDE.md) for the full command list and [AI_USE.md](AI_USE.md) for how AI tools were used.
