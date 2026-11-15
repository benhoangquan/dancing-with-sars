# NISAR availability: little-giant

Generated 2026-11-15 from the public CMR catalog (no login). Product: GCOV.
Study area `[-120.99, 47.7, -120.15, 48.22]`. An acquisition counts only if the frames of one pass together cover at least 90% of it.

| Window | Dates |
|---|---|
| before | 2026-06-17 to 2026-07-14 |
| after | 2026-09-09 to 2026-10-20 |

## Collections searched, best maturity first

| Collection | Maturity | Granules | Tracks | Dates covered | Track with data in every window |
|---|---|---|---|---|---|
| `NISAR_L2_GCOV_V1` | validated | 8 | 5 | 2026-10-24 to 2026-11-05 | none |
| `NISAR_L2_GCOV_PROVISIONAL_V1` | provisional | 63 | 5 | 2026-06-19 to 2026-10-19 | `071_D` |
| `NISAR_L2_GCOV_BETA_V1` | beta | 24 | 5 | 2025-10-17 to 2026-01-09 | none |

## Decision

Use **`NISAR_L2_GCOV_PROVISIONAL_V1`** (provisional), track **`071_D`**, footprint coverage 100% (worst date).

| Window | Date | Frames | Coverage | Granules | Size (MB) |
|---|---|---|---|---|---|
| before | 2026-06-19 | 064 | 100% | `NISAR_L2_PR_GCOV_023_071_D_064_4005_DHDH_A_20260619T030957_20260619T031032_P05023_N_F_J_001` | 7,106 |
| before | 2026-07-01 | 064+065 | 100% | `NISAR_L2_PR_GCOV_024_071_D_064_4005_DHDH_A_20260701T030956_20260701T031031_P05023_N_F_J_001`<br>`NISAR_L2_PR_GCOV_024_071_D_065_4005_DHDH_A_20260701T031030_20260701T031105_P05023_N_F_J_001` | 14,040 |
| before | 2026-07-13 | 064 | 100% | `NISAR_L2_PR_GCOV_025_071_D_064_4005_DHDH_A_20260713T030956_20260713T031031_P05023_N_F_J_001` | 7,102 |
| after | 2026-09-11 | 064+065 | 100% | `NISAR_L2_PR_GCOV_030_071_D_064_4005_DHDH_A_20260911T030953_20260911T031028_P05023_N_F_J_001`<br>`NISAR_L2_PR_GCOV_030_071_D_065_4005_DHDH_A_20260911T031027_20260911T031103_P05023_N_F_J_001` | 14,228 |
| after | 2026-09-23 | 064+065 | 100% | `NISAR_L2_PR_GCOV_031_071_D_064_4005_DHDH_A_20260923T030953_20260923T031028_P05023_N_F_J_001`<br>`NISAR_L2_PR_GCOV_031_071_D_065_4005_DHDH_A_20260923T031027_20260923T031103_P05023_N_F_J_001` | 14,228 |
| after | 2026-10-05 | 064 | 100% | `NISAR_L2_PR_GCOV_032_071_D_064_4005_DHDH_A_20261005T030953_20261005T031029_P05023_N_F_J_001` | 7,294 |
| after | 2026-10-17 | 064+065 | 100% | `NISAR_L2_PR_GCOV_033_071_D_064_4005_DHDH_A_20261017T030953_20261017T031029_P05023_N_F_J_001`<br>`NISAR_L2_PR_GCOV_033_071_D_065_4005_DHDH_A_20261017T031028_20261017T031103_P05023_N_F_J_001` | 14,232 |

7 acquisitions, 11 full-frame granules, 78.2 GB in all. The pipeline reads only the study-area window from each file, so far less than that is transferred. Where a pass is cut into two frames, both are read and mosaicked.

## Other tracks over the study area (selected collection)

| Track | Granules | Acquisitions | Best coverage |
|---|---|---|---|
| `071_D` | 14 | 2026-06-19 to 2026-10-17 (10) | 100% |
| `077_A` | 10 | 2026-06-19 to 2026-10-17 (10) | 61% |
| `106_A` | 20 | 2026-06-21 to 2026-10-19 (10) | 4% |
| `005_A` | 9 | 2026-06-26 to 2026-10-12 (9) | 100% |
| `172_D` | 9 | 2026-06-26 to 2026-10-12 (9) | 94% |
