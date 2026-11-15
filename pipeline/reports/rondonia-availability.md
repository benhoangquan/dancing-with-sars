# NISAR availability: rondonia

Generated 2026-11-14 from the public CMR catalog (no login). Product: GCOV.
Study area `[-63.8, -10.4, -62.9, -9.7]`. An acquisition counts only if the frames of one pass together cover at least 90% of it.

| Window | Dates |
|---|---|
| before | 2026-06-17 to 2026-07-11 |
| after | 2026-09-09 to 2026-10-03 |

## Collections searched, best maturity first

| Collection | Maturity | Granules | Tracks | Dates covered | Track with data in every window |
|---|---|---|---|---|---|
| `NISAR_L2_GCOV_V1` | validated | 5 | 3 | 2026-10-23 to 2026-10-28 | none |
| `NISAR_L2_GCOV_PROVISIONAL_V1` | provisional | 68 | 4 | 2026-06-18 to 2026-10-16 | `161_A` |
| `NISAR_L2_GCOV_BETA_V1` | beta | 7 | 3 | 2025-11-02 to 2026-01-08 | none |

## Decision

Use **`NISAR_L2_GCOV_PROVISIONAL_V1`** (provisional), track **`161_A`**, footprint coverage 100% (worst date).

| Window | Date | Frames | Coverage | Granules | Size (MB) |
|---|---|---|---|---|---|
| before | 2026-06-25 | 172+173 | 100% | `NISAR_L2_PR_GCOV_023_161_A_172_2005_DHDH_A_20260625T100047_20260625T100122_P05023_N_F_J_001`<br>`NISAR_L2_PR_GCOV_023_161_A_173_2000_DHNA_M_20260625T100121_20260625T100159_P05023_N_F_J_001` | 3,719 |
| before | 2026-07-07 | 172+173 | 100% | `NISAR_L2_PR_GCOV_024_161_A_172_2005_DHDH_A_20260707T100047_20260707T100121_P05023_N_F_J_001`<br>`NISAR_L2_PR_GCOV_024_161_A_173_2000_DHNA_M_20260707T100120_20260707T100158_P05023_N_F_J_001` | 3,675 |
| after | 2026-09-17 | 172+173 | 100% | `NISAR_L2_PR_GCOV_030_161_A_172_2005_DHDH_A_20260917T100044_20260917T100118_P05023_N_F_J_001`<br>`NISAR_L2_PR_GCOV_030_161_A_173_2005_DHDH_A_20260917T100117_20260917T100152_P05023_N_F_J_001` | 3,736 |
| after | 2026-09-29 | 172+173 | 100% | `NISAR_L2_PR_GCOV_031_161_A_172_2005_DHDH_A_20260929T100044_20260929T100118_P05023_N_F_J_001`<br>`NISAR_L2_PR_GCOV_031_161_A_173_2005_DHDH_A_20260929T100117_20260929T100152_P05023_N_F_J_001` | 3,736 |

4 acquisitions, 8 full-frame granules, 14.9 GB in all. The pipeline reads only the study-area window from each file, so far less than that is transferred. Where a pass is cut into two frames, both are read and mosaicked.

## Other tracks over the study area (selected collection)

| Track | Granules | Acquisitions | Best coverage |
|---|---|---|---|
| `060_A` | 10 | 2026-06-18 to 2026-10-16 (10) | 0% |
| `068_D` | 20 | 2026-06-18 to 2026-10-16 (10) | 100% |
| `161_A` | 16 | 2026-06-25 to 2026-10-11 (8) | 100% |
| `169_D` | 16 | 2026-06-25 to 2026-10-11 (8) | 40% |
