# Data sources

Provider, collection, maturity and use of every dataset the pipeline reads. NASA data is used first.

| Id | Mission and product | Collection (CMR short name) | Maturity | Provider | Use |
|---|---|---|---|---|---|
| `nisar-gcov` | NISAR L2 Geocoded Polarimetric Covariance (HDF5, UTM) | `NISAR_L2_GCOV_PROVISIONAL_V1` (CMR `C2854338529-ASF`) | provisional | NASA-ISRO, distributed by ASF DAAC | HH and HV backscatter for all three chapters |
| `nisar-gunw` | NISAR L2 Geocoded Unwrapped Interferogram (HDF5) | `NISAR_L2_GUNW_PROVISIONAL_V1` (CMR `C2854335566-ASF`) | provisional | NASA-ISRO, distributed by ASF DAAC | Line-of-sight displacement for the San Joaquin chapter |
| `opera-rtc-s1` | OPERA Sentinel-1 RTC backscatter | `OPERA_L2_RTC-S1_V1` (not yet checked; only needed if NISAR fails) | validated | NASA JPL OPERA, ASF DAAC | Labeled fallback for GCOV chapters |
| `opera-disp-s1` | OPERA Sentinel-1 displacement | `OPERA_L3_DISP-S1_V1` (not yet checked; only needed if NISAR fails) | validated | NASA JPL OPERA, ASF DAAC | Labeled fallback for the San Joaquin chapter |
| `hls` | Harmonized Landsat Sentinel-2 | `HLSS30`, `HLSL30` via Microsoft Planetary Computer | validated | NASA, USGS | Optical before/after and smoke scenes |
| `copernicus-dem` | Copernicus DEM GLO-30 | `cop-dem-glo-30` via Microsoft Planetary Computer, resampled to 1,600 px, int16 COG | n/a | ESA, Airbus | Terrain and hillshade in each place (`sar dem`); read in the browser as `cog://...#dem`, no tile server |
| `bcws` | BC Wildfire Service fire perimeters (current) | `WHSE_LAND_AND_NATURAL_RESOURCE.PROT_CURRENT_FIRE_POLYS_SP` (BC open data WFS) | n/a | Government of British Columbia, Open Government Licence – BC | Perimeter of the Quilpituk Creek fire (K51402, 1,278 ha, mapped 2026-08-21); labeled fallback |
| `overture` | Overture Maps buildings and transportation | Overture GeoParquet via `overturemaps` | n/a | Overture Maps Foundation, ODbL | Buildings and roads on the radar stage (`sar overture`) |
| `osm` | OpenStreetMap relations via Nominatim | relation 3614774 (Terra Indígena Uru-Eu-Wau-Wau); city boundaries; Sayung village points | n/a | OpenStreetMap contributors, ODbL | Territory outline, "your city scale" outlines (Montréal, New York, Toronto, Greater London, Jakarta), Demak landmark points |
| `cited` | Deltares, *Economic assessment of subsidence in Semarang and Demak, Indonesia* (April 2021), for Building with Nature Indonesia | [PDF on ecoshape.org](https://www.ecoshape.org/app/uploads/sites/2/2017/08/Economic-assessment-of-subsidence-in-Semarang-and-Demak-Indonesia.pdf) | n/a | Deltares | Demak facts: subsidence up to 13 cm/yr in Sayung (2017), over 8 cm/yr in northern Semarang and Sayung, about 2,534 ha lost to the sea since 1984 |
| `blue-marble` | NASA Blue Marble Next Generation | NASA GIBS `BlueMarble_NextGeneration`, z0 to z4, saved as WebP | n/a | NASA Earth Observatory, public domain | The hero and hotspot globe (`sar globe`) |
| `commons-audio` | Wikimedia Commons recordings | "20090610 0 ambience.ogg" (nille, public domain), "Chainsaw 12.ogg" (ezwa, public domain), "Ocean Waves on a Tropical Beach.ogg" (Jarrod stanley, CC0) | n/a | Wikimedia Commons | Before and after ambience (`sar audio`); none recorded at the places. The Okanagan "after" loop is synthesized and labeled as such |
| `synthetic` | Synthetic patterns written by `sar fixture` | none | n/a | this project | `illustrative` layers only |

## NISAR coverage found on 2026-11-14

`sar discover` searched the public CMR catalog. Each NISAR L2 product has three collections: `_BETA_V1`, `_PROVISIONAL_V1` and the plain `_V1` (validated). Over our study areas the validated releases only start on 2026-10-22, so they cannot supply a "before" scene, and Beta stops in January 2026. The Provisional collections are the data of record for all three chapters. Full tables: `pipeline/reports/<chapter>-availability.md`.

| Chapter | Collection | Track and frames | Acquisitions | Full-frame size |
|---|---|---|---|---|
| `rondonia` | `NISAR_L2_GCOV_PROVISIONAL_V1` | `161_A`, frames 172 and 173 mosaicked | 2 before, 2 after | 14.9 GB (8 granules) |
| `okanagan` | `NISAR_L2_GCOV_PROVISIONAL_V1` | `071_D`, frame 063 | 2 before, 2 after | 28.5 GB (4 granules of 7.1 GB, 40 MHz mode) |
| `san-joaquin` | `NISAR_L2_GUNW_PROVISIONAL_V1` | `114_D_070` | 9 sequential interferograms, one with a 36-day baseline | 20.5 GB |
| `madre-de-dios` | `NISAR_L2_GCOV_PROVISIONAL_V1` | `025_D` | see `pipeline/reports/madre-de-dios-availability.md` | |
| `demak` | `NISAR_L2_GCOV_PROVISIONAL_V1` | `154_A` | see `pipeline/reports/demak-availability.md` | |
| `sundarbans` | `NISAR_L2_GCOV_PROVISIONAL_V1` | `170_A`, frames 012 and 013 mosaicked | 8 dates, 16 granules | 62 GB |
| `alaska` | `NISAR_L2_GCOV_PROVISIONAL_V1` | `064_A`, frames 032 and 033 mosaicked | 8 dates, 16 granules | 62 GB |
| `greenland` | `NISAR_L2_GOFF_PROVISIONAL_V1` | `131_A_037` | 9 sequential offset pairs, 2026-06-23 to 2026-10-21 | 8.0 GB |

Granules are full frames of 1.6 to 7.1 GB, so the pipeline reads only the study-area window from each HDF5 file rather than downloading them. Provisional products are calibrated but not final; the site labels every layer built from them with its maturity.

NISAR public L-band data covers acquisitions from 2026-06-17 onward (ASF DAAC notice, 2026-07-21). The earlier record is released in stages through the end of 2026. Access needs an Earthdata Login account, set up by the user.

## What is real in the site today

| Chapter | Radar | Optical | Status |
|---|---|---|---|
| `rondonia` | NISAR GCOV provisional, measured (374 ha, 6.0 dB) | HLS 2026, real | **real** |
| `demak` | NISAR GCOV provisional composite (imagery; the change here is the rice cycle, so no change number) | HLS 2017 and 2026, real | **real imagery**, numbers cited |
| `okanagan` | NISAR GCOV provisional, measured inside the BC Wildfire Service perimeter (0.8 dB relative drop, placebo spread 0.2 dB) | HLS 2025, smoke scene and post-fire, real | **real**, perimeter is a labeled fallback |
| `san-joaquin` | fetched, corrected, not yet reliable | not built | off the site in v1 (see `docs/decisions.md`) |
| `madre-de-dios` | fetched, only speckle-sized patches | not built | no chapter (see `docs/decisions.md`) |
| `sundarbans` | fetched, the only drop is one acquisition's edge | not built | no chapter (see `docs/decisions.md`) |
| `alaska` | fetched, scattered 3 ha patches, no feature | not built | no chapter (see `docs/decisions.md`) |
| `greenland` | GOFF offsets fetched, pairs do not reproduce | not built | no chapter (see `docs/decisions.md`) |

## Licenses

NISAR, OPERA, HLS and Blue Marble follow NASA open data policy. Copernicus DEM: free use with attribution. Overture and OpenStreetMap: ODbL, attributed on the map. BC Wildfire Service: Open Government Licence – British Columbia. Commons audio: public domain or CC0, credited in the app while sound plays. Confirm each product's license page before release; the pipeline writes these into each chapter manifest under `generated.sources`.
