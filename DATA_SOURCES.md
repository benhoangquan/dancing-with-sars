# Data sources

Provider, collection, maturity and use of every dataset the pipeline reads. NASA data is used first.

| Id | Mission and product | Collection (CMR short name) | Maturity | Provider | Use |
|---|---|---|---|---|---|
| `nisar-gcov` | NISAR L2 Geocoded Polarimetric Covariance (HDF5, UTM) | `NISAR_L2_GCOV_PROVISIONAL_V1` (CMR `C2854338529-ASF`) | provisional | NASA-ISRO, distributed by ASF DAAC | HH and HV backscatter for the Rondônia and Okanagan chapters |
| `nisar-gunw` | NISAR L2 Geocoded Unwrapped Interferogram (HDF5) | `NISAR_L2_GUNW_PROVISIONAL_V1` (CMR `C2854335566-ASF`) | provisional | NASA-ISRO, distributed by ASF DAAC | Line-of-sight displacement for the San Joaquin chapter |
| `opera-rtc-s1` | OPERA Sentinel-1 RTC backscatter | `OPERA_L2_RTC-S1_V1` (not yet checked; only needed if NISAR fails) | validated | NASA JPL OPERA, ASF DAAC | Labeled fallback for GCOV chapters |
| `opera-disp-s1` | OPERA Sentinel-1 displacement | `OPERA_L3_DISP-S1_V1` (not yet checked; only needed if NISAR fails) | validated | NASA JPL OPERA, ASF DAAC | Labeled fallback for the San Joaquin chapter |
| `hls` | Harmonized Landsat Sentinel-2 | `HLSS30`, `HLSL30` via Microsoft Planetary Computer | validated | NASA, USGS | Optical before/after and smoke scenes |
| `nasadem` | NASADEM 1 arc-second | via Microsoft Planetary Computer | validated | NASA | Terrain for the pre-rendered flyover (milestone 4) |
| `terrarium` | AWS Terrain Tiles (terrarium encoding) | `s3.amazonaws.com/elevation-tiles-prod` | n/a | Mapzen, AWS Open Data | Live terrain in the browser |
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
| `rondonia` | NISAR GCOV provisional, measured | HLS, real | **real** |
| `okanagan` | fetched, no burn scar inside this box | not built | illustrative (see `docs/decisions.md`) |
| `san-joaquin` | fetched, corrected, not yet reliable | not built | illustrative (see `docs/decisions.md`) |
| `madre-de-dios` | fetched, only speckle-sized patches | not built | no chapter (see `docs/decisions.md`) |
| `demak` | fetched, change is the rice crop cycle | not built | no chapter (see `docs/decisions.md`) |
| `sundarbans` | fetched, the only drop is one acquisition's edge | not built | no chapter (see `docs/decisions.md`) |
| `alaska` | fetched, scattered 3 ha patches, no feature | not built | no chapter (see `docs/decisions.md`) |
| `greenland` | GOFF offsets fetched, pairs do not reproduce | not built | no chapter (see `docs/decisions.md`) |

## Licenses

NISAR, OPERA, HLS and NASADEM follow NASA open data policy. Confirm each product's license page before release; the pipeline writes these into each chapter manifest under `generated.sources`.
