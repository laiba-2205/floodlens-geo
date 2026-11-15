# Data Sources and Attribution (FL-201 / FL-202)

Status: updated draft. Lines marked TODO must be confirmed before submission.

## 1. Dataset register

| # | Dataset | Product | Used for | Dates | Access | License / attribution |
|---|---|---|---|---|---|---|
| 1 | NASA-ISRO NISAR, L-band SAR | L2 GCOV, track 084 (ascending), frame 017, HH, Provisional maturity | Primary before/after change layer | Before: 2026-07-14, After: 2026-07-26 | NASA Earthdata login, ASF DAAC. TODO: confirm route (Vertex or API); the notebook asks for credentials by prompt and stores none | NISAR data are openly available. TODO: copy the required citation text from the product page |
| 2 | NASA-ISRO NISAR, L-band SAR | L2 GCOV, track 135 (descending), frame 073 | Reference pair only, not compared directly with #1 | 2026-07-17 and 2026-08-10 | As above | As above |
| 3 | OpenStreetMap | Hospitals, clinics, schools, major roads (motorway, trunk, primary, secondary), via OSMnx | Infrastructure exposure | Downloaded 2026-11-15 | Overpass API through OSMnx | (c) OpenStreetMap contributors, ODbL. https://www.openstreetmap.org/copyright |
| 4 | News reports (Dawn, Express Tribune, others) | Qualitative reports of flooded localities | Context and sanity check only, never as measurement | 2026-07-26 to 2026-08-03 | Public web | Report list maintained by Tayyab (team lead) with URL and date for each. Not independently verified |

## 2. Primary product IDs (track 084)

Before (2026-07-14):
`NISAR_L2_PR_GCOV_025_084_A_017_4005_DHDH_A_20260714T002131_20260714T002205_P05023_F_F_J_001`

After (2026-07-26):
`NISAR_L2_PR_GCOV_026_084_A_017_4005_DHDH_A_20260726T002130_20260726T002205_P05023_N_F_J_001`

Readable from the names: cycle 025 then 026, track 084, ascending, frame 017, the same processing
release (P05023). The scans are 12 days apart on the same track and frame, so the viewing geometry
matches. Both scans share the same 10 m UTM 43N grid (checked in `method_note.md`), so no resampling
was needed.

**Check:** the two IDs differ in one field (`F_F_J` before, `N_F_J` after). What that field means is
not confirmed. TODO: look it up in the NISAR product specification and confirm the two scans were
processed the same way. If they were not, list it as a limitation.

## 3. Verified input metadata (FL-202)

Measured directly from `t084_change_smooth_adj_db.tif` and `lahore_change_smooth_adj_db.tif`.

| Item | Value |
|---|---|
| Polarization used | HH (HHHH power, converted to dB) |
| Working grid | UTM zone 43N (EPSG:32643), 10 m pixels |
| Raster size | 3818 x 2907 pixels (track 084), 3817 x 2907 (track 135) |
| Study-area bounding box (lon/lat) | West 74.0999, South 31.3978, East 74.5001, North 31.6623 |
| Valid coverage inside the clip | 100% of pixels finite; no nodata inside the clip |
| Units | dB. Change = after minus before, negative = darker |
| Zones file CRS | EPSG:4326 (lon/lat) |
| Zones bounding box | West 74.0974, South 31.4081, East 74.4948, North 31.6622 |
| Scene-wide brightening removed | about 1.35 dB |

Note: "valid coverage" describes the clip. It does not describe the full NISAR frame.

## 4. Known limits of the inputs

- Only one scan pair on track 084 falls inside the local flooding window, and the Jul 26 scan was
  taken before the worst reported flooding (see `validation-notes.md`).
- The clip is a fixed box. Its northern edge (31.6623 N) sits at the northern edge of the zones. Media
  reports name localities further north (for example Muridke, Kala Shah Kaku, Sheikhupura district)
  that fall outside it. TODO: decide with the team whether to re-clip a larger box.
- The track 135 pair spans different dates and geometry, so it is a reference only.
- OSM coverage is incomplete, so exposure counts are minimums.
- TODO: confirm whether a track 135 scan around 2026-07-29 (the cycle between your two files) exists in
  the ASF archive. The README says Jul 26 is the only scan inside the window; this line records that
  the search should be repeated before that is stated in the pitch.

## 5. Not used (listed in the plan, not used here)

MODIS/VIIRS flood products, Black Marble night lights, SRTM, WorldPop. TODO: update this section if any
are added for the independent check.
