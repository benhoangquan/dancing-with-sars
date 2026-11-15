# NISAR availability: sundarbans

Generated 2026-11-14 from the public CMR catalog (no login). Product: GCOV.
Study area `[88.6, 21.65, 89.45, 22.35]`. An acquisition counts only if the frames of one pass together cover at least 90% of it.

| Window | Dates |
|---|---|
| before | 2026-06-17 to 2026-07-11 |
| after | 2026-09-09 to 2026-10-03 |

## Collections searched, best maturity first

| Collection | Maturity | Granules | Tracks | Dates covered | Track with data in every window |
|---|---|---|---|---|---|
| `NISAR_L2_GCOV_V1` | validated | 10 | 3 | 2026-10-23 to 2026-11-11 | none |
| `NISAR_L2_GCOV_PROVISIONAL_V1` | provisional | 69 | 3 | 2026-06-20 to 2026-10-18 | `170_A` |
| `NISAR_L2_GCOV_BETA_V1` | beta | 0 | 0 | none | none |

## Decision

Use **`NISAR_L2_GCOV_PROVISIONAL_V1`** (provisional), track **`170_A`**, footprint coverage 100% (worst date).

| Window | Date | Frames | Coverage | Granules | Size (MB) |
|---|---|---|---|---|---|
| before | 2026-06-25 | 012+013 | 100% | `NISAR_L2_PR_GCOV_023_170_A_012_4005_DHDH_A_20260625T232913_20260625T232922_P05023_N_P_J_001`<br>`NISAR_L2_PR_GCOV_023_170_A_013_4005_DHDH_A_20260625T232921_20260625T232956_P05023_N_F_J_001` | 8,065 |
| before | 2026-07-07 | 012+013 | 100% | `NISAR_L2_PR_GCOV_024_170_A_012_4005_DHDH_A_20260707T232912_20260707T232921_P05023_N_P_J_001`<br>`NISAR_L2_PR_GCOV_024_170_A_013_4005_DHDH_A_20260707T232920_20260707T232955_P05023_N_F_J_001` | 8,048 |
| after | 2026-09-17 | 012+013 | 100% | `NISAR_L2_PR_GCOV_030_170_A_012_4005_DHDH_A_20260917T232910_20260917T232918_P05023_F_P_J_001`<br>`NISAR_L2_PR_GCOV_030_170_A_013_4005_DHDH_A_20260917T232917_20260917T232952_P05023_F_F_J_001` | 7,875 |
| after | 2026-09-29 | 012+013 | 100% | `NISAR_L2_PR_GCOV_031_170_A_012_4005_DHDH_A_20260929T232910_20260929T232918_P05023_N_P_J_001`<br>`NISAR_L2_PR_GCOV_031_170_A_013_4005_DHDH_A_20260929T232917_20260929T232952_P05023_N_F_J_001` | 7,872 |

4 acquisitions, 8 full-frame granules, 31.9 GB in all. The pipeline reads only the study-area window from each file, so far less than that is transferred. Where a pass is cut into two frames, both are read and mosaicked.

## Other tracks over the study area (selected collection)

| Track | Granules | Acquisitions | Best coverage |
|---|---|---|---|
| `091_D` | 20 | 2026-06-20 to 2026-10-18 (10) | 35% |
| `019_D` | 15 | 2026-06-27 to 2026-10-13 (9) | 100% |
| `170_A` | 18 | 2026-06-25 to 2026-10-11 (9) | 100% |
