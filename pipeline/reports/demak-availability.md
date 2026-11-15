# NISAR availability: demak

Generated 2026-11-14 from the public CMR catalog (no login). Product: GCOV.
Study area `[110.4, -7.05, 110.75, -6.75]`. An acquisition counts only if the frames of one pass together cover at least 90% of it.

| Window | Dates |
|---|---|
| before | 2026-06-17 to 2026-07-11 |
| after | 2026-09-09 to 2026-10-03 |

## Collections searched, best maturity first

| Collection | Maturity | Granules | Tracks | Dates covered | Track with data in every window |
|---|---|---|---|---|---|
| `NISAR_L2_GCOV_V1` | validated | 2 | 2 | 2026-10-22 to 2026-10-23 | none |
| `NISAR_L2_GCOV_PROVISIONAL_V1` | provisional | 20 | 2 | 2026-06-24 to 2026-10-11 | `154_A` |
| `NISAR_L2_GCOV_BETA_V1` | beta | 0 | 0 | none | none |

## Decision

Use **`NISAR_L2_GCOV_PROVISIONAL_V1`** (provisional), track **`154_A`**, footprint coverage 100% (worst date).

| Window | Date | Frames | Coverage | Granules | Size (MB) |
|---|---|---|---|---|---|
| before | 2026-06-24 | 174 | 100% | `NISAR_L2_PR_GCOV_023_154_A_174_4005_DHDH_A_20260624T222243_20260624T222317_P05023_N_F_J_001` | 5,397 |
| before | 2026-07-06 | 174 | 100% | `NISAR_L2_PR_GCOV_024_154_A_174_4005_DHDH_A_20260706T222242_20260706T222317_P05023_N_F_J_001` | 5,517 |
| after | 2026-09-16 | 174 | 100% | `NISAR_L2_PR_GCOV_030_154_A_174_4005_DHDH_A_20260916T222239_20260916T222314_P05023_N_F_J_001` | 5,545 |
| after | 2026-09-28 | 174 | 100% | `NISAR_L2_PR_GCOV_031_154_A_174_4005_DHDH_A_20260928T222239_20260928T222314_P05023_N_F_J_001` | 5,550 |

4 acquisitions, 4 full-frame granules, 22.0 GB in all. The pipeline reads only the study-area window from each file, so far less than that is transferred. Where a pass is cut into two frames, both are read and mosaicked.

## Other tracks over the study area (selected collection)

| Track | Granules | Acquisitions | Best coverage |
|---|---|---|---|
| `154_A` | 9 | 2026-06-24 to 2026-10-10 (9) | 100% |
| `162_D` | 9 | 2026-06-25 to 2026-10-11 (9) | 100% |
