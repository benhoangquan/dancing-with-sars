# NISAR availability: crosswhite

Generated 2026-11-15 from the public CMR catalog (no login). Product: GCOV.
Study area `[-121.03, 44.22, -120.01, 45.07]`. An acquisition counts only if the frames of one pass together cover at least 90% of it.

| Window | Dates |
|---|---|
| before | 2026-06-17 to 2026-07-14 |
| after | 2026-09-09 to 2026-10-20 |

## Collections searched, best maturity first

| Collection | Maturity | Granules | Tracks | Dates covered | Track with data in every window |
|---|---|---|---|---|---|
| `NISAR_L2_GCOV_V1` | validated | 6 | 4 | 2026-10-22 to 2026-11-03 | none |
| `NISAR_L2_GCOV_PROVISIONAL_V1` | provisional | 49 | 4 | 2026-06-19 to 2026-10-19 | `071_D` |
| `NISAR_L2_GCOV_BETA_V1` | beta | 21 | 4 | 2025-10-17 to 2026-01-19 | none |

## Decision

Use **`NISAR_L2_GCOV_PROVISIONAL_V1`** (provisional), track **`071_D`**, footprint coverage 96% (worst date).

| Window | Date | Frames | Coverage | Granules | Size (MB) |
|---|---|---|---|---|---|
| before | 2026-06-19 | 066 | 96% | `NISAR_L2_PR_GCOV_023_071_D_066_4005_DHDH_A_20260619T031105_20260619T031140_P05023_N_F_J_001` | 7,022 |
| before | 2026-07-01 | 066 | 96% | `NISAR_L2_PR_GCOV_024_071_D_066_4005_DHDH_A_20260701T031104_20260701T031139_P05023_N_F_J_001` | 7,014 |
| before | 2026-07-13 | 065+066 | 96% | `NISAR_L2_PR_GCOV_025_071_D_065_4005_DHDH_A_20260713T031030_20260713T031105_P05023_N_F_J_001`<br>`NISAR_L2_PR_GCOV_025_071_D_066_4005_DHDH_A_20260713T031104_20260713T031139_P05023_N_F_J_001` | 13,948 |
| after | 2026-09-11 | 065+066 | 96% | `NISAR_L2_PR_GCOV_030_071_D_065_4005_DHDH_A_20260911T031027_20260911T031103_P05023_N_F_J_001`<br>`NISAR_L2_PR_GCOV_030_071_D_066_4005_DHDH_A_20260911T031102_20260911T031137_P05023_N_F_J_001` | 14,136 |
| after | 2026-09-23 | 065+066 | 96% | `NISAR_L2_PR_GCOV_031_071_D_065_4005_DHDH_A_20260923T031027_20260923T031103_P05023_N_F_J_001`<br>`NISAR_L2_PR_GCOV_031_071_D_066_4005_DHDH_A_20260923T031102_20260923T031137_P05023_N_F_J_001` | 14,140 |
| after | 2026-10-05 | 066 | 96% | `NISAR_L2_PR_GCOV_032_071_D_066_4005_DHDH_A_20261005T031102_20261005T031137_P05023_N_F_J_001` | 7,026 |
| after | 2026-10-17 | 066 | 96% | `NISAR_L2_PR_GCOV_033_071_D_066_4005_DHDH_A_20261017T031102_20261017T031137_P05023_N_F_J_001` | 7,014 |

7 acquisitions, 10 full-frame granules, 70.3 GB in all. The pipeline reads only the study-area window from each file, so far less than that is transferred. Where a pass is cut into two frames, both are read and mosaicked.

## Other tracks over the study area (selected collection)

| Track | Granules | Acquisitions | Best coverage |
|---|---|---|---|
| `071_D` | 14 | 2026-06-19 to 2026-10-17 (10) | 96% |
| `106_A` | 10 | 2026-06-21 to 2026-10-19 (10) | 100% |
| `005_A` | 17 | 2026-06-26 to 2026-10-12 (9) | 74% |
| `143_D` | 8 | 2026-06-24 to 2026-10-10 (8) | 100% |
