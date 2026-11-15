# FloodLens geospatial: Lahore candidate change zones (NISAR)

Radar change detection for Lahore, Pakistan (box: lon 74.10 to 74.50, lat 31.40 to 31.66) using NISAR L2 GCOV scenes from July and August 2026.

**Everything here is labelled "candidate change", not a verified flood.** There is no ground truth yet.

## Result

- Neither scene pair shows a wide flood footprint in the Lahore box.
- The main signal is small: some extra dark (water-like) area in the bends of the Ravi channel on Jul 26, about 0.8 km² gained in the river corridor at the -15 dB cutoff, against about 2.5 km² lost.
- Most other flagged area is in farmland in the northwest of the box. It has a patchwork of field-shaped blocks, which looks like paddy, irrigation or crop timing rather than flooding. These zones are kept in the data but marked low confidence.
- The Jul 17 to Aug 10 pair (track 135) is after the local flooding window and shows mostly water receding: about 0.4 km² gained and 2.5 km² lost in the corridor at -15 dB.

## Primary product: track 084, Jul 14 to Jul 26

Jul 26 is the only NISAR scan inside the local flooding window (about Jul 25 to 31).

| File | What it is |
|---|---|
| `data/processed/zones_t084.geojson` | 337 candidate zones (EPSG:4326), one record each |
| `data/processed/method_note.md` | Data, steps, parameters, corridor water table, caveats |
| `data/processed/zones_map.png` | Zones on the radar image |
| `data/processed/corridor_check.png` | The river corridor used for tiering |
| `data/processed/t084_change_smooth_adj_db.tif` | Change layer (Jul 26 minus Jul 14, dB), UTM zone 43N, 10 m |
| `data/processed/lahore_change_smooth_adj_db.tif` | Second reference: Jul 17 to Aug 10, track 135 |

### Zone tiers

| Tier | Meaning | Zones | Area |
|---|---|---|---|
| `1_river_corridor` | At least half the zone lies within about 1 km of the lower Ravi | 21 | 0.54 km² |
| `2_likely_agricultural` | Everywhere else, probably crop or paddy change | 316 | 6.31 km² |

Zone fields: `zone_id`, `tier`, `area_km2`, `mean_delta_db` (each zone's own mean change), `before_mean_db`, `after_mean_db`, `share_in_river_corridor`, `centroid_lon`, `centroid_lat`, `date_before`, `date_after`, `product_id_before`, `product_id_after`, `label` (always `candidate_change`), `quality_notes`.

## Method in brief

1. Clip the Lahore box from each NISAR GCOV file and convert HH power to dB.
2. Smooth with a 7 x 7 window (70 m) in linear power to reduce speckle.
3. Change = after minus before, then remove the scene-wide median shift (about 1.35 dB).
4. Candidate pixel: change below -3 dB, dark after (below -15 dB), not dark before. Drop blobs under 0.5 ha.
5. Tag each zone river or agricultural by its overlap with the Ravi corridor.

Full details and caveats are in `data/processed/method_note.md`.

## Data

NISAR L2 GCOV, Provisional maturity, HH polarization. Download from ASF Vertex (needs an Earthdata login). The raw files are about 6 GB each and are **not** in this repo.

| Pair | Track and geometry | Scenes |
|---|---|---|
| Primary | 084, frame 17, ascending | `NISAR_L2_PR_GCOV_025_084_A_017_...20260714T002131...` and `NISAR_L2_PR_GCOV_026_084_A_017_...20260726T002130...` |
| Reference | 135, frame 73, descending | `NISAR_L2_PR_GCOV_025_135_D_073_...20260717T134739...` and `NISAR_L2_PR_GCOV_027_135_D_073_...20260810T134737...` |

The two pairs have different geometry and pass times, so they cannot be chained into one time series.

## Re-running

Python environment: `pip install -r requirements.txt`. Install `scipy` too if it is not in the list.

Track 135 reference pair (raw files in `data\raw`):
```
python processing\inspect_nisar.py data\raw\<file>
python processing\prepare_lahore.py
python processing\make_preview.py
python processing\make_candidates.py
python processing\make_river_check.py
```

Track 084 primary pair: the clipped dB files `t084_hh_db_20260714.tif` and `t084_hh_db_20260726.tif` come from the Colab notebook (they are not in the repo because of their size). Place them in `data\processed`, then:
```
python processing\make_zones.py -15
```
`-15` reproduces the shared zones. Leave `RIVER_WAYPOINTS = []` in `make_zones.py` for the same result.

Pair comparison: `python processing\compare_pairs.py`.

## Known limitations

- The -15 dB water cutoff and -3 dB change threshold were chosen by inspection, not tuned or validated.
- No independent check yet (for example Sentinel-1 or a published flood map).
- The river corridor covers only the lower Ravi, where it is clearly dark in radar. Zones on the upper river, if any, would be labelled agricultural.
- Paddy and irrigation look like flooding in radar, so tier 2 cannot be separated from flooding with radar alone.
- Exposure counts (people, buildings, roads) are not included yet. They need an OpenStreetMap extract for Lahore.
- The removal of the scene-wide brightness shift is a single median offset, which is crude.
