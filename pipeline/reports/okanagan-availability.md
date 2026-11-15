# NISAR availability: okanagan

Generated 2026-11-14 from the public CMR catalog (no login). Product: GCOV.
Study area `[-119.85, 49.75, -119.15, 50.25]`. An acquisition counts only if the frames of one pass together cover at least 90% of it.

| Window | Dates |
|---|---|
| before | 2026-06-17 to 2026-07-11 |
| after | 2026-09-09 to 2026-10-03 |

## Collections searched, best maturity first

| Collection | Maturity | Granules | Tracks | Dates covered | Track with data in every window |
|---|---|---|---|---|---|
| `NISAR_L2_GCOV_V1` | validated | 4 | 4 | 2026-10-22 to 2026-10-29 | none |
| `NISAR_L2_GCOV_PROVISIONAL_V1` | provisional | 37 | 4 | 2026-06-19 to 2026-10-17 | `071_D` |
| `NISAR_L2_GCOV_BETA_V1` | beta | 19 | 4 | 2025-10-22 to 2026-01-19 | none |

## Decision

Use **`NISAR_L2_GCOV_PROVISIONAL_V1`** (provisional), track **`071_D`**, footprint coverage 100% (worst date).

| Window | Date | Frames | Coverage | Granules | Size (MB) |
|---|---|---|---|---|---|
| before | 2026-06-19 | 063 | 100% | `NISAR_L2_PR_GCOV_023_071_D_063_4005_DHDH_A_20260619T030923_20260619T030958_P05023_N_F_J_001` | 7,117 |
| before | 2026-07-01 | 063 | 100% | `NISAR_L2_PR_GCOV_024_071_D_063_4005_DHDH_A_20260701T030922_20260701T030957_P05023_N_F_J_001` | 7,121 |
| after | 2026-09-11 | 063 | 100% | `NISAR_L2_PR_GCOV_030_071_D_063_4005_DHDH_A_20260911T030919_20260911T030954_P05023_N_F_J_001` | 7,121 |
| after | 2026-09-23 | 063 | 100% | `NISAR_L2_PR_GCOV_031_071_D_063_4005_DHDH_A_20260923T030919_20260923T030954_P05023_N_F_J_001` | 7,121 |

4 acquisitions, 4 full-frame granules, 28.5 GB in all. The pipeline reads only the study-area window from each file, so far less than that is transferred. Where a pass is cut into two frames, both are read and mosaicked.

## Other tracks over the study area (selected collection)

| Track | Granules | Acquisitions | Best coverage |
|---|---|---|---|
| `071_D` | 10 | 2026-06-19 to 2026-10-17 (10) | 100% |
| `077_A` | 9 | 2026-06-19 to 2026-10-17 (9) | 100% |
| `149_A` | 9 | 2026-06-24 to 2026-10-10 (9) | 91% |
| `172_D` | 9 | 2026-06-26 to 2026-10-12 (9) | 100% |
