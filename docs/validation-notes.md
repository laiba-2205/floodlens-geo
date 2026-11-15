# Validation Notes (FL-205)

Status: updated draft. Everything below describes candidate surface change, not confirmed flooding.

## 1. What was checked

| Check | Result |
|---|---|
| Imagery dates and comparability | Primary pair is 2026-07-14 to 2026-07-26 on the same track and frame (084, ascending), 12 days apart. |
| Seasonal trend | About 1.35 dB of overall brightening between the dates was removed before looking for change. |
| CRS and alignment | Rasters are in UTM 43N at 10 m. Zones are exported in EPSG:4326. Both scans share one grid. |
| Raster coverage | 100% finite pixels inside the clip; no nodata. |
| Geometry validity | 37 of 337 zone polygons had self-touching rings from raster polygonization. `make_contract.py` repairs them with `make_valid`; total area is unchanged (6.851 km2). |
| Zones | 337 candidate zones. 21 are in the Ravi river corridor (0.54 km2, small water gains in channel bends). 316 are likely agricultural (6.31 km2). |
| Wide flood footprint | None found in either scan pair, inside the clipped box. |
| Reference pair (track 135, Jul 17 to Aug 10) | Different dates and geometry, so it supports the picture but is not directly comparable. |

## 2. Infrastructure exposure (FL-203 / FL-204)

Source: OpenStreetMap through OSMnx. 579 hospitals, clinics and schools and 2,335 major-road segments
were found in the study area.

| Measure | All zones | River corridor (21) | Likely agricultural (316) |
|---|---|---|---|
| Zones with a hospital, clinic or school within 500 m | 0 of 337 | 0 | 0 |
| Nearest amenity (km), min / mean / max | 1.84 / 10.0 / 15.4 | 2.94 / 4.47 / 6.13 | 1.84 / 10.39 / 15.40 |
| Nearest hospital or clinic (km), mean | 11.2 | 6.40 | 11.49 |
| Zones touching a major road within 500 m | 12 | 0 | 12 |
| Major road in a 500 m buffer, max (km) | 2.59 | 0.00 | 2.59 |

Reading: no candidate zone is within 500 m of a mapped hospital, clinic or school. The 21 river-corridor
zones are the closest group to amenities (about 3 to 6 km). The exposure term of the score is therefore
flat on this event.

## 3. Timing against media reports (qualitative, not verified)

Local news reports place the heaviest flooding after the Jul 26 scan. The full report list with URLs is
maintained by Tayyab (team lead).

- Reports dated Jul 26 and 27 describe Chenab and Ravi flooding of crops and elevated Ravi levels.
- Reports dated Jul 29 describe flooding in Ferozewala tehsil (Rachna Town, Rana Town, Pathan Colony and
  others) after a nullah embankment breach, still worsening that day.
- A report dated Jul 31 says water in affected villages was receding.
- A report dated Aug 3 gives the government's figure of 1,449 sq km affected across Sheikhupura,
  Gujranwala and Narowal.

Consequences: (a) the Jul 26 scan likely predates peak flooding, so "no wide footprint" is expected and
is not evidence that no flood occurred; (b) several reported localities lie north of the clip.
Check each article's year: some search results are from 2024 and 2025 floods.

## 4. False-positive risks

- Irrigated paddy fields darken in radar in the same way open water does. The 316 agricultural zones
  are labelled low confidence for this reason.
- The 21 river-corridor zones are small channel-bend changes. They may be normal river movement and
  not flood spread.
- Speckle was smoothed, which can blur small real changes.
- Urban rain flooding (waterlogged streets in Lahore city) is a different process from river and nullah
  flooding and is not what this method is designed to detect.

## 5. Not yet done

- **Independent flood check.** No Sentinel-1 or published flood map comparison has been made. Until it
  is, the zones must not be described as flooded. TODO: compare the 21 river zones with a flood
  product for about 2026-07-26 to 2026-07-31, and record the result per zone as overlap, no overlap, or
  no coverage.
- Once Tayyab's news list is ready, geocode its localities and measure their distance to the zones and to the clip.
- Decide whether to re-clip a larger box to the north.
- Confirm with the team that the provisional priority score weights in `make_contract.py` are acceptable.

## 6. Limitations to state in the demo

1. Outputs show observed radar change. They do not confirm flood damage.
2. Only one pair falls inside the flood window, and it was acquired before the reported peak.
3. OSM is incomplete, so exposure values are minimums.
4. The priority score is a provisional rule, not a validated probability.
