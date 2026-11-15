r"""
make_contract.py  (data contract for the app, FL-401 / FL-105 interface)

Turns zones_t084_exposure.geojson into zones_t084_contract.geojson, using the
field names in section 9 of the team execution plan.

Run from the repo root (D:\floodlens-geo) with the .venv active:
    python processing\make_contract.py

PROVISIONAL SCORE. priority_score is a transparent rule, not a probability and
not validated. The weights below are placeholders for the team to agree on.
Change them here and rerun; score_explanation updates itself.
"""
import json
import numpy as np
import geopandas as gpd
from shapely import make_valid

IN_PATH = "data/processed/zones_t084_exposure.geojson"
OUT_PATH = "data/processed/zones_t084_contract.geojson"

# ---- placeholder weights (must sum to 1.0) ---------------------------------
W_CHANGE, W_EXPOSURE, W_CONFIDENCE = 0.4, 0.4, 0.2
# confidence by tier: river-corridor zones are the stronger flood candidates
CONFIDENCE = {"1_river_corridor": 0.6, "2_likely_agricultural": 0.3}
EXPOSURE_CAP = 3          # amenities within 500 m at which exposure_norm reaches 1.0

CATEGORY = {
    "1_river_corridor": "river_corridor_candidate_change",
    "2_likely_agricultural": "agricultural_candidate_change",
}

z = gpd.read_file(IN_PATH).to_crs(4326)

# 37 zones from the raster-to-polygon step have self-touching rings (diagonal pixels).
# make_valid keeps the area identical and avoids errors in map libraries.
n_bad = int((~z.is_valid).sum())
z["geometry"] = z.geometry.apply(make_valid)
print(f"Repaired {n_bad} invalid geometries.")

# change intensity: size of the dB drop, scaled by the 95th percentile (0 to 1)
mag = z["mean_delta_db"].abs()
p95 = float(np.percentile(mag, 95))
z["change_norm"] = (mag / p95).clip(0, 1)
z["exposure_norm"] = (z["infrastructure_exposure"] / EXPOSURE_CAP).clip(0, 1)
z["confidence_norm"] = z["tier"].map(CONFIDENCE).fillna(0.3)

z["priority_score"] = (
    100 * (W_CHANGE * z["change_norm"]
           + W_EXPOSURE * z["exposure_norm"]
           + W_CONFIDENCE * z["confidence_norm"])
).round(1)

def explain(r):
    return (
        f"PROVISIONAL rule-based score, not a probability. "
        f"change {r.change_norm:.2f} (mean {r.mean_delta_db:.1f} dB, weight {W_CHANGE}) + "
        f"exposure {r.exposure_norm:.2f} ({int(r.infrastructure_exposure)} hospitals/clinics/schools "
        f"within 500 m, weight {W_EXPOSURE}) + "
        f"confidence {r.confidence_norm:.2f} (tier, weight {W_CONFIDENCE}). "
        f"Nearest amenity {r.nearest_amenity_km:.1f} km; major road in 500 m buffer {r.major_road_km:.2f} km."
    )

out = gpd.GeoDataFrame(
    {
        "zone_id": z["zone_id"],
        "change_category": z["tier"].map(CATEGORY),
        "change_intensity": z["mean_delta_db"].round(2),     # dB, negative = darker
        "infrastructure_exposure": z["infrastructure_exposure"].astype(int),
        "activity_proxy": None,                              # not used in this MVP
        "priority_score": z["priority_score"],
        "score_explanation": z.apply(explain, axis=1),
        "source": ("NASA-ISRO NISAR L2 GCOV HH, track 084 (Jul 14 and Jul 26 2026); "
                   "OpenStreetMap contributors (ODbL)"),
        "observation_date": (z["date_before"].astype(str).str[:10] + " to "
                             + z["date_after"].astype(str).str[:10]),
        "crs": "EPSG:4326 (geometry); analysis grid EPSG:32643 at 10 m",
        "quality_notes": z["quality_notes"] + " Exposure counts are minimums (OSM is incomplete).",
        # extras the interface can use
        "area_km2": z["area_km2"].round(4),
        "nearest_amenity_km": z["nearest_amenity_km"],
        "nearest_health_km": z["nearest_health_km"],
        "major_road_km": z["major_road_km"],
        "geometry": z["geometry"],
    },
    crs=4326,
)

out.to_file(OUT_PATH, driver="GeoJSON")

print("Saved:", OUT_PATH, f"({len(out)} zones)")
print("priority_score range:", out.priority_score.min(), "to", out.priority_score.max())
print(out.groupby("change_category")["priority_score"].agg(["count", "min", "mean", "max"]).round(1))
print("Exposure term is 0 for every zone on this event, so ranking comes from change and tier.")
