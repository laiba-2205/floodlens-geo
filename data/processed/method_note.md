# Method note: FloodLens candidate zones (track 084)

**Label:** candidate change, not a verified flood.

## Data
- Before: `NISAR_L2_PR_GCOV_025_084_A_017_4005_DHDH_A_20260714T002131_20260714T002205_P05023_F_F_J_001` (2026-07-14)
- After: `NISAR_L2_PR_GCOV_026_084_A_017_4005_DHDH_A_20260726T002130_20260726T002205_P05023_N_F_J_001` (2026-07-26)
- NISAR L2 GCOV, Provisional maturity, HH polarization (HHHH), track 084, frame 17, ascending.
- Both scans share the same 10 m UTM 43N grid (checked), so they were subtracted pixel by pixel with no resampling.

## Processing
1. Clipped the Lahore box (about 2,907 x 3,818 pixels) from each file.
2. Converted linear power to dB: 10 * log10(HHHH).
3. Smoothed each scan with a 7 x 7 window (70 m) in linear power, to reduce speckle.
4. Change = after minus before, then removed the scene-wide median shift of 1.35 dB.
5. Candidate pixel: change below -3.0 dB, after-scan below -15.0 dB, before-scan above -15.0 dB.
6. Removed blobs under 50 pixels (0.5 ha). Each remaining connected blob is one zone.
7. River corridor: the large area dark on both dates at -15.0 dB (the lower Ravi), grown into connected pixels below -15.0 dB (hysteresis), plus a hand-drawn line along the upper Ravi where radar could not separate it (waypoints read from the map, approximate), then about 1 km around all of it.
8. Tier 1 = at least half the zone inside the corridor. Tier 2 = the rest, flagged likely agricultural.

## Results
- 337 zones: tier 1 21 zones (0.54 km2), tier 2 316 zones (6.31 km2).
- Ravi corridor water area (km2), before vs after:

| Threshold | 2026-07-14 | 2026-07-26 | Gained | Lost |
|---|---|---|---|---|
| < -14 dB | 8.99 | 7.24 | 0.94 | 2.68 |
| < -15 dB | 7.02 | 5.32 | 0.77 | 2.47 |
| < -16 dB | 6.01 | 2.30 | 0.38 | 4.10 |

## Caveats
- The -15.0 dB water cutoff, the -15.0 dB corridor cutoff and the -3.0 dB change threshold are first-pass choices made by inspection, not tuned or validated.
- The upper-river part of the corridor follows a hand-drawn line with approximate waypoints, not a surveyed centreline. See corridor_check.png.
- No ground truth or independent reference (for example Sentinel-1 or a flood map) has been compared yet.
- The scene-wide brightening of about 1.4 dB (crops, soil moisture) was removed with a single median shift, which is crude.
- Paddy transplanting, irrigation and crop growth look like flooding in radar. Tier 2 zones are mostly this kind of area.
- Ascending geometry and early-morning pass time differ from the descending track 135 pair, so the two pairs cannot be chained.
- OpenStreetMap water and built-up masks have not been applied. Permanent water is approximated from the radar itself.
- Small zones near pixel-scale edges are sensitive to the speckle filter.
