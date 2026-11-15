# NISAR availability: madre-de-dios

Generated 2026-11-14 from the public CMR catalog (no login). Product: GCOV.
Study area `[-70.65, -13.15, -69.85, -12.55]`. An acquisition counts only if the frames of one pass together cover at least 90% of it.

| Window | Dates |
|---|---|
| before | 2026-06-17 to 2026-07-11 |
| after | 2026-09-09 to 2026-10-03 |

## Collections searched, best maturity first

| Collection | Maturity | Granules | Tracks | Dates covered | Track with data in every window |
|---|---|---|---|---|---|
| `NISAR_L2_GCOV_V1` | validated | 4 | 4 | 2026-10-25 to 2026-11-01 | none |
| `NISAR_L2_GCOV_PROVISIONAL_V1` | provisional | 36 | 4 | 2026-06-17 to 2026-10-20 | `025_D` |
| `NISAR_L2_GCOV_BETA_V1` | beta | 9 | 4 | 2025-10-30 to 2026-01-17 | none |

## Decision

Use **`NISAR_L2_GCOV_PROVISIONAL_V1`** (provisional), track **`025_D`**, footprint coverage 100% (worst date).

| Window | Date | Frames | Coverage | Granules | Size (MB) |
|---|---|---|---|---|---|
| before | 2026-07-09 | 095 | 100% | `NISAR_L2_PR_GCOV_025_025_D_095_2005_DHDH_A_20260709T225237_20260709T225311_P05023_N_F_J_001` | 1,873 |
| after | 2026-09-19 | 095 | 100% | `NISAR_L2_PR_GCOV_031_025_D_095_2005_DHDH_A_20260919T225234_20260919T225309_P05023_F_F_J_001` | 1,922 |

2 acquisitions, 2 full-frame granules, 3.8 GB in all. The pipeline reads only the study-area window from each file, so far less than that is transferred. Where a pass is cut into two frames, both are read and mosaicked.

## Other tracks over the study area (selected collection)

| Track | Granules | Acquisitions | Best coverage |
|---|---|---|---|
| `046_A` | 10 | 2026-06-17 to 2026-10-15 (10) | 58% |
| `118_A` | 9 | 2026-06-22 to 2026-10-20 (9) | 89% |
| `126_D` | 9 | 2026-06-22 to 2026-10-20 (9) | 34% |
| `025_D` | 8 | 2026-06-27 to 2026-10-13 (8) | 100% |
