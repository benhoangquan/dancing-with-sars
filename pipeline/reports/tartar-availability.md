# NISAR availability: tartar

Generated 2026-11-15 from the public CMR catalog (no login). Product: GCOV.
Study area `[-117.36, 44.14, -116.79, 44.73]`. An acquisition counts only if the frames of one pass together cover at least 90% of it.

| Window | Dates |
|---|---|
| before | 2026-06-17 to 2026-07-14 |
| after | 2026-09-09 to 2026-10-20 |

## Collections searched, best maturity first

| Collection | Maturity | Granules | Tracks | Dates covered | Track with data in every window |
|---|---|---|---|---|---|
| `NISAR_L2_GCOV_V1` | validated | 4 | 4 | 2026-10-24 to 2026-11-01 | none |
| `NISAR_L2_GCOV_PROVISIONAL_V1` | provisional | 60 | 4 | 2025-11-03 to 2026-10-20 | `042_D` |
| `NISAR_L2_GCOV_BETA_V1` | beta | 19 | 4 | 2025-10-17 to 2026-01-17 | none |

## Decision

Use **`NISAR_L2_GCOV_PROVISIONAL_V1`** (provisional), track **`042_D`**, footprint coverage 100% (worst date).

| Window | Date | Frames | Coverage | Granules | Size (MB) |
|---|---|---|---|---|---|
| before | 2026-06-17 | 066 | 100% | `NISAR_L2_PR_GCOV_023_042_D_066_4005_DHDH_A_20260617T025426_20260617T025504_P05023_F_F_J_001` | 7,511 |
| before | 2026-06-29 | 066 | 100% | `NISAR_L2_PR_GCOV_024_042_D_066_4005_DHDH_A_20260629T025426_20260629T025505_P05023_N_F_J_001` | 7,667 |
| before | 2026-07-11 | 066 | 100% | `NISAR_L2_PR_GCOV_025_042_D_066_4005_DHDH_A_20260711T025425_20260711T025504_P05023_N_F_J_001` | 7,683 |
| after | 2026-09-09 | 066 | 100% | `NISAR_L2_PR_GCOV_030_042_D_066_4005_DHDH_A_20260909T025423_20260909T025502_P05023_N_F_J_001` | 7,680 |
| after | 2026-09-21 | 066 | 100% | `NISAR_L2_PR_GCOV_031_042_D_066_4005_DHDH_A_20260921T025423_20260921T025502_P05023_N_F_J_001` | 7,679 |
| after | 2026-10-03 | 066 | 100% | `NISAR_L2_PR_GCOV_032_042_D_066_4005_DHDH_A_20261003T025423_20261003T025502_P05023_N_F_J_001` | 7,688 |
| after | 2026-10-15 | 066 | 100% | `NISAR_L2_PR_GCOV_033_042_D_066_4005_DHDH_A_20261015T025423_20261015T025458_P05023_N_F_J_001` | 6,966 |

7 acquisitions, 7 full-frame granules, 52.9 GB in all. The pipeline reads only the study-area window from each file, so far less than that is transferred. Where a pass is cut into two frames, both are read and mosaicked.

## Other tracks over the study area (selected collection)

| Track | Granules | Acquisitions | Best coverage |
|---|---|---|---|
| `077_A` | 25 | 2025-11-03 to 2026-10-17 (25) | 100% |
| `042_D` | 10 | 2026-06-17 to 2026-10-15 (10) | 100% |
| `114_D` | 9 | 2026-06-22 to 2026-10-20 (9) | 92% |
| `005_A` | 8 | 2026-06-26 to 2026-10-12 (8) | 31% |
