r"""
make_exposure.py  (FL-203 / FL-204)
Counts hospitals, clinics and schools near each candidate zone, and measures
major-road length near each zone, using OpenStreetMap.

Run from D:\floodlens-geo with the .venv active:
    pip install osmnx
    python processing\make_exposure.py

Outputs (in data/processed/):
    exposure_counts.csv          one row per zone, easy to read in Excel
    zones_t084_exposure.geojson  zones in EPSG:4326 with exposure columns added

Data: (c) OpenStreetMap contributors, ODbL. OSM coverage is incomplete in
places, so counts are minimums, not totals.
"""
import sys
import geopandas as gpd
import pandas as pd
import osmnx as ox
from shapely.geometry import box

ZONES_PATH = "data/processed/zones_t084.geojson"
OUT_CSV = "data/processed/exposure_counts.csv"
OUT_GEOJSON = "data/processed/zones_t084_exposure.geojson"
METRIC_CRS = 32643          # UTM 43N, metres (Lahore)
BUFFER_M = 500              # "near" = within 500 m of the zone
AMENITIES = ["hospital", "clinic", "school"]
ROAD_TYPES = ["motorway", "trunk", "primary", "secondary"]

# ---------------------------------------------------------------- load zones
zones = gpd.read_file(ZONES_PATH)
print("Columns:", list(zones.columns))
print("Zones CRS:", zones.crs)
if zones.crs is None:
    sys.exit("Zones file has no CRS. Tell me and I will fix it before continuing.")

# find the id column, or create one
id_col = next((c for c in ["zone_id", "id", "ID", "zone", "Zone"] if c in zones.columns), None)
if id_col is None:
    zones["zone_id"] = [f"Z{i:04d}" for i in range(len(zones))]
    id_col = "zone_id"
    print("No id column found, created zone_id.")
print("Using id column:", id_col)

z = zones.to_crs(METRIC_CRS)
buf = z[[id_col, "geometry"]].copy()
buf["geometry"] = z.buffer(BUFFER_M)

# ---------------------------------------------------------------- download OSM
west, south, east, north = zones.to_crs(4326).total_bounds
area = box(west - 0.005, south - 0.005, east + 0.005, north + 0.005)
print("Downloading OSM data for the zone area (needs internet)...")

try:
    pois = ox.features_from_polygon(area, tags={"amenity": AMENITIES})
except Exception as e:
    print("No amenities returned:", e)
    pois = gpd.GeoDataFrame()

try:
    roads = ox.features_from_polygon(area, tags={"highway": ROAD_TYPES})
except Exception as e:
    print("No roads returned:", e)
    roads = gpd.GeoDataFrame()

# ---------------------------------------------------------------- amenities
result = pd.DataFrame({id_col: z[id_col].values}).set_index(id_col)
for a in AMENITIES:
    result[a] = 0

if len(pois) and "amenity" in pois.columns:
    pois = pois[pois["amenity"].isin(AMENITIES)].to_crs(METRIC_CRS)
    # school/hospital can be mapped as building polygons, so use centroids
    pois["geometry"] = pois.geometry.centroid
    joined = gpd.sjoin(pois[["amenity", "geometry"]], buf, predicate="within")
    counts = joined.groupby([id_col, "amenity"]).size().unstack(fill_value=0)
    for a in counts.columns:
        result.loc[counts.index, a] = counts[a]
    print(f"Amenities found in area: {len(pois)}")

    # distance from each zone to the nearest amenity (tells us if 0 counts is real)
    zc = z[[id_col, "geometry"]]
    near = gpd.sjoin_nearest(zc, pois[["geometry"]], distance_col="d")
    result["nearest_amenity_km"] = (near.groupby(id_col)["d"].min() / 1000).round(2)
    health = pois[pois["amenity"].isin(["hospital", "clinic"])]
    if len(health):
        nh = gpd.sjoin_nearest(zc, health[["geometry"]], distance_col="d")
        result["nearest_health_km"] = (nh.groupby(id_col)["d"].min() / 1000).round(2)
else:
    print("No amenities found in this area.")

# ---------------------------------------------------------------- roads
result["major_road_km"] = 0.0
if len(roads):
    roads = roads[roads.geometry.type.isin(["LineString", "MultiLineString"])].to_crs(METRIC_CRS)
    roads = roads[["geometry"]]
    clipped = gpd.overlay(roads, buf, how="intersection", keep_geom_type=True)
    if len(clipped):
        clipped["km"] = clipped.geometry.length / 1000
        km = clipped.groupby(id_col)["km"].sum()
        result.loc[km.index, "major_road_km"] = km.round(2)
    print(f"Major road segments in area: {len(roads)}")
else:
    print("No major roads found in this area.")

result["infrastructure_exposure"] = result[AMENITIES].sum(axis=1)
result["exposure_note"] = (
    f"OSM amenities and major roads within {BUFFER_M} m of the zone. "
    "OSM coverage is incomplete; counts are minimums."
)

# ---------------------------------------------------------------- save
result.reset_index().to_csv(OUT_CSV, index=False)

out = zones.merge(result.reset_index(), on=id_col, how="left").to_crs(4326)
out.to_file(OUT_GEOJSON, driver="GeoJSON")

print()
print(result.drop(columns="exposure_note").describe().loc[["count", "mean", "max"]])
print(f"Zones with at least one amenity nearby: {(result['infrastructure_exposure'] > 0).sum()} of {len(result)}")
print("Saved:", OUT_CSV)
print("Saved:", OUT_GEOJSON)