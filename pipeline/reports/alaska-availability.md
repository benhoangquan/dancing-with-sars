# NISAR availability: alaska

Generated 2026-11-14 from the public CMR catalog (no login). Product: GCOV.
Study area `[-164.8, 60.8, -163.2, 61.6]`. An acquisition counts only if the frames of one pass together cover at least 90% of it.

| Window | Dates |
|---|---|
| before | 2026-06-17 to 2026-07-11 |
| after | 2026-09-09 to 2026-10-03 |

## Collections searched, best maturity first

| Collection | Maturity | Granules | Tracks | Dates covered | Track with data in every window |
|---|---|---|---|---|---|
| `NISAR_L2_GCOV_V1` | validated | 11 | 6 | 2026-10-23 to 2026-11-02 | none |
| `NISAR_L2_GCOV_PROVISIONAL_V1` | provisional | 93 | 7 | 2026-06-18 to 2026-10-21 | `064_A` |
| `NISAR_L2_GCOV_BETA_V1` | beta | 11 | 2 | 2025-11-29 to 2026-01-18 | none |

## Decision

Use **`NISAR_L2_GCOV_PROVISIONAL_V1`** (provisional), track **`064_A`**, footprint coverage 100% (worst date).

| Window | Date | Frames | Coverage | Granules | Size (MB) |
|---|---|---|---|---|---|
| before | 2026-06-18 | 032+033 | 100% | `NISAR_L2_PR_GCOV_023_064_A_032_4005_DHDH_A_20260618T151222_20260618T151258_P05023_N_F_J_001`<br>`NISAR_L2_PR_GCOV_023_064_A_033_4005_DHDH_A_20260618T151257_20260618T151332_P05023_N_F_J_001` | 10,712 |
| before | 2026-06-30 | 032+033 | 100% | `NISAR_L2_PR_GCOV_024_064_A_032_4005_DHDH_A_20260630T151221_20260630T151257_P05023_N_F_J_001`<br>`NISAR_L2_PR_GCOV_024_064_A_033_4005_DHDH_A_20260630T151256_20260630T151331_P05023_N_F_J_001` | 10,720 |
| after | 2026-09-10 | 032+033 | 100% | `NISAR_L2_PR_GCOV_030_064_A_032_4005_DHDH_A_20260910T151218_20260910T151255_P05023_N_F_J_001`<br>`NISAR_L2_PR_GCOV_030_064_A_033_2005_DHDH_M_20260910T151254_20260910T151330_P05023_N_F_J_001` | 7,161 |
| after | 2026-09-22 | 032+033 | 100% | `NISAR_L2_PR_GCOV_031_064_A_032_4005_DHDH_A_20260922T151218_20260922T151255_P05023_N_F_J_001`<br>`NISAR_L2_PR_GCOV_031_064_A_033_2005_DHDH_M_20260922T151254_20260922T151330_P05023_N_F_J_001` | 7,172 |

4 acquisitions, 8 full-frame granules, 35.8 GB in all. The pipeline reads only the study-area window from each file, so far less than that is transferred. Where a pass is cut into two frames, both are read and mosaicked.

## Other tracks over the study area (selected collection)

| Track | Granules | Acquisitions | Best coverage |
|---|---|---|---|
| `064_A` | 20 | 2026-06-18 to 2026-10-16 (10) | 100% |
| `102_D` | 20 | 2026-06-21 to 2026-10-19 (10) | 100% |
| `131_D` | 10 | 2026-06-23 to 2026-10-21 (10) | 11% |
| `030_D` | 9 | 2026-06-28 to 2026-10-14 (9) | 100% |
| `035_A` | 9 | 2026-06-28 to 2026-10-14 (9) | 17% |
| `165_A` | 6 | 2026-06-25 to 2026-10-11 (3) | 19% |
| `001_D` | 1 | 2026-06-26 to 2026-06-26 (1) | 0% |
