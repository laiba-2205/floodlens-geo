"""
make_zones.py
Step 5: turn the track 084 change layer (Jul 14 -> Jul 26) into candidate zones.

Inputs (in data\\processed, from the Colab zip):
    t084_hh_db_20260714.tif
    t084_hh_db_20260726.tif

Outputs (in data\\processed):
    zones_t084.geojson   one record per zone, EPSG:4326
    method_note.md       how it was made, parameters, caveats
    zones_map.png        picture of the zones
    corridor_check.png   shows the river body and corridor used for the tiers

Run from the project folder (with .venv active; make_preview.py must be in the
same folder as this script):
    python processing\\make_zones.py
or, to try a different corridor cutoff (default -13.5 dB):
    python processing\\make_zones.py -14
"""
import json
import os
import sys

import numpy as np
import rasterio
from rasterio.features import geometry_mask, shapes, sieve
from rasterio.warp import transform as warp_transform
from rasterio.warp import transform_geom
from rasterio.windows import Window
from rasterio.windows import transform as window_transform

from make_preview import box_filter, smooth_db  # same folder

OUT_DIR = os.path.join("data", "processed")
BEFORE_TIF = os.path.join(OUT_DIR, "t084_hh_db_20260714.tif")
AFTER_TIF = os.path.join(OUT_DIR, "t084_hh_db_20260726.tif")

BEFORE_ID = "NISAR_L2_PR_GCOV_025_084_A_017_4005_DHDH_A_20260714T002131_20260714T002205_P05023_F_F_J_001"
AFTER_ID = "NISAR_L2_PR_GCOV_026_084_A_017_4005_DHDH_A_20260726T002130_20260726T002205_P05023_N_F_J_001"
BEFORE_DATE, AFTER_DATE = "2026-07-14", "2026-07-26"

WATER_DB = -15.0      # dark enough to be water (first-pass choice, checked on the Ravi)
CORRIDOR_WATER_DB = -13.5  # looser cutoff used ONLY to find the whole river for the corridor
#   override from the command line, e.g.:  python processing\make_zones.py -14
DROP_DB = -3.0        # change threshold after offset removal
MIN_PIXELS = 50       # drop zones under 0.5 ha
BIG_WATER_PX = 5000   # 50 ha: the main river body
BUFFER_WIN = 201      # ~1 km square buffer around the river
WIN = 7               # smoothing window (70 m)

TIER_RIVER = "1_river_corridor"
TIER_FARM = "2_likely_agricultural"


# Optional hand-drawn river line for reaches the radar threshold can't pick up
# (the narrow upper Ravi). Points are fractions of the box: (x from left, y from top),
# read off corridor_check.png. They are APPROXIMATE: check the magenta line in that
# picture and edit these. Set to [] to switch the line off.
RIVER_WAYPOINTS = []


def grow_from_seed(seed, loose):
    """Hysteresis: keep only the parts of `loose` that connect to `seed` (8-connectivity)."""
    try:
        from scipy import ndimage
        lab, n = ndimage.label(loose, structure=np.ones((3, 3), dtype=int))
        keep = np.unique(lab[seed & loose])
        keep = keep[keep > 0]
        return np.isin(lab, keep)
    except ImportError:
        grown = seed & loose
        for _ in range(400):
            nxt = (box_filter(grown.astype("float32"), 3) > 0) & loose
            if nxt.sum() == grown.sum():
                break
            grown = nxt
        return grown


def line_mask(shape, pts):
    """Boolean mask with a thin line through fractional (x, y) points."""
    H, W = shape
    m = np.zeros(shape, dtype=bool)
    xy = [(x * (W - 1), y * (H - 1)) for x, y in pts]
    for (x0, y0), (x1, y1) in zip(xy[:-1], xy[1:]):
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        cols = np.clip(np.linspace(x0, x1, n).round().astype(int), 0, W - 1)
        rows = np.clip(np.linspace(y0, y1, n).round().astype(int), 0, H - 1)
        m[rows, cols] = True
    return m


def maxpool(mask, step):
    h = (mask.shape[0] // step) * step
    w = (mask.shape[1] // step) * step
    return mask[:h, :w].reshape(h // step, step, w // step, step).max(axis=(1, 3))


def main():
    with rasterio.open(BEFORE_TIF) as s:
        before, transform, crs = s.read(1), s.transform, s.crs
    with rasterio.open(AFTER_TIF) as s:
        after = s.read(1)
    if before.shape != after.shape:
        raise SystemExit("The two dB rasters have different shapes.")
    if not (np.isfinite(before).all() and np.isfinite(after).all()):
        raise SystemExit("Found empty (NaN) pixels. Tell me and I'll add nodata handling.")

    b = smooth_db(before)
    a = smooth_db(after)
    raw = a - b
    offset = float(np.median(raw))
    change = raw - offset
    H, W = change.shape
    px = abs(transform.a)
    px_km2 = (px * px) / 1e6

    # Candidates: got darker, dark now, not dark before; then drop specks.
    cand = (change < DROP_DB) & (a < WATER_DB) & (b > WATER_DB)
    clean = sieve(cand.astype("uint8"), size=MIN_PIXELS, connectivity=8).astype(bool)

    # River corridor, built in three steps:
    #  1. strict seed: the large area dark on both dates at WATER_DB (the lower Ravi)
    #  2. hysteresis: grow the seed into looser-dark pixels (corr_db) that CONNECT to it,
    #     so the river's edges and shallower reaches count but separate dark fields do not
    #  3. optional hand-drawn line (RIVER_WAYPOINTS) for reaches the radar can't separate
    corr_db = float(sys.argv[1]) if len(sys.argv) > 1 else CORRIDOR_WATER_DB

    def strict_body(t):
        both_t = (a < t) & (b < t)
        return sieve(both_t.astype("uint8"), size=BIG_WATER_PX, connectivity=8).astype(bool)

    print(f"Median offset removed: {offset:.2f} dB")
    print(f"Candidate pixels after specks removed: {clean.sum() * px_km2:.2f} km2")
    big_strict = strict_body(WATER_DB)
    print(f"Strict river seed at {WATER_DB} dB: {big_strict.sum() * px_km2:.2f} km2")
    try:
        import scipy.ndimage  # noqa: F401
        have_scipy = True
    except ImportError:
        have_scipy = False
    if have_scipy:
        print("Seed grown into connected looser-dark pixels (km2):")
        for t in (-14.5, -14.0, -13.5, -13.0):
            g = grow_from_seed(big_strict, (a < t) & (b < t))
            print(f"  < {t} dB: {g.sum() * px_km2:.2f}")
    else:
        print("(scipy not installed: skipping the growth table. pip install scipy to enable it.)")
    if corr_db <= WATER_DB:
        big = big_strict   # same cutoff as the seed: nothing to grow
    else:
        big = grow_from_seed(big_strict, (a < corr_db) & (b < corr_db))
    line = line_mask((H, W), RIVER_WAYPOINTS) if RIVER_WAYPOINTS else np.zeros((H, W), dtype=bool)
    corridor = box_filter((big | line).astype("float32"), BUFFER_WIN) > 0
    print(f"Using {corr_db} dB for the corridor: river body {big.sum() * px_km2:.2f} km2, "
          f"hand-drawn line {'on' if line.any() else 'off'}, corridor {corridor.sum() * px_km2:.1f} km2")

    # Corridor water table for the method note.
    table = []
    for t in (-14, -15, -16):
        wj, wa = b < t, a < t
        table.append((t, (wj & corridor).sum() * px_km2, (wa & corridor).sum() * px_km2,
                      (wa & ~wj & corridor).sum() * px_km2, (wj & ~wa & corridor).sum() * px_km2))

    # One zone per connected blob of candidate pixels.
    tier_img = np.zeros((H, W), dtype="uint8")
    zones = []
    for geom, _ in shapes(clean.astype("uint8"), mask=clean, transform=transform, connectivity=8):
        ring = np.array(geom["coordinates"][0])
        c0 = max(int(np.floor((ring[:, 0].min() - transform.c) / px)), 0)
        c1 = min(int(np.ceil((ring[:, 0].max() - transform.c) / px)), W)
        r0 = max(int(np.floor((transform.f - ring[:, 1].max()) / px)), 0)
        r1 = min(int(np.ceil((transform.f - ring[:, 1].min()) / px)), H)
        win = Window(c0, r0, c1 - c0, r1 - r0)
        m = geometry_mask([geom], out_shape=(r1 - r0, c1 - c0),
                          transform=window_transform(win, transform), invert=True)
        n = int(m.sum())
        if n == 0:
            continue
        sl = (slice(r0, r1), slice(c0, c1))
        frac_river = float(corridor[sl][m].mean())
        tier = TIER_RIVER if frac_river >= 0.5 else TIER_FARM
        rows, cols = np.nonzero(m)
        zones.append(dict(
            geom=geom, n=n, tier=tier, frac_river=frac_river,
            mean_delta=float(change[sl][m].mean()),
            before_db=float(b[sl][m].mean()), after_db=float(a[sl][m].mean()),
            cx=transform.c + (c0 + cols.mean() + 0.5) * px,
            cy=transform.f - (r0 + rows.mean() + 0.5) * px,
            sl=sl, m=m,
        ))
    if not zones:
        raise SystemExit("No zones found. Check the thresholds.")

    zones.sort(key=lambda z: (z["tier"], -z["n"]))
    lon, lat = warp_transform(crs, "EPSG:4326", [z["cx"] for z in zones], [z["cy"] for z in zones])

    features = []
    for i, (z, lo, la) in enumerate(zip(zones, lon, lat), start=1):
        tier_img[z["sl"]][z["m"]] = 1 if z["tier"] == TIER_RIVER else 2
        if z["tier"] == TIER_RIVER:
            note = ("Candidate change inside the Ravi corridor: dark on the after date, not on the before date. "
                    "Not a verified flood.")
        else:
            note = ("Candidate change outside the river corridor. Likely crop, paddy or irrigation change; "
                    "low confidence as flood evidence.")
        features.append({
            "type": "Feature",
            "geometry": transform_geom(crs, "EPSG:4326", z["geom"], precision=6),
            "properties": {
                "zone_id": f"Z{i:04d}",
                "tier": z["tier"],
                "area_km2": round(z["n"] * px_km2, 4),
                "mean_delta_db": round(z["mean_delta"], 2),
                "before_mean_db": round(z["before_db"], 2),
                "after_mean_db": round(z["after_db"], 2),
                "share_in_river_corridor": round(z["frac_river"], 2),
                "centroid_lon": round(lo, 5),
                "centroid_lat": round(la, 5),
                "date_before": BEFORE_DATE,
                "date_after": AFTER_DATE,
                "product_id_before": BEFORE_ID,
                "product_id_after": AFTER_ID,
                "label": "candidate_change",
                "quality_notes": note,
            },
        })

    n1 = sum(1 for z in zones if z["tier"] == TIER_RIVER)
    a1 = sum(z["n"] for z in zones if z["tier"] == TIER_RIVER) * px_km2
    a2 = sum(z["n"] for z in zones if z["tier"] == TIER_FARM) * px_km2
    fc = {
        "type": "FeatureCollection",
        "name": "floodlens_t084_candidate_zones",
        "metadata": {
            "source": "NISAR L2 GCOV Provisional, HH, track 084 frame 17 ascending",
            "before": BEFORE_ID, "after": AFTER_ID,
            "label": "candidate change, not a verified flood",
        },
        "features": features,
    }
    gj = os.path.join(OUT_DIR, "zones_t084.geojson")
    with open(gj, "w") as f:
        json.dump(fc, f)
    print(f"\nZones: {len(zones)} total | tier 1 river corridor: {n1} zones, {a1:.2f} km2 "
          f"| tier 2 likely agricultural: {len(zones) - n1} zones, {a2:.2f} km2")
    print("Saved", gj)

    # Method note
    rows_md = "\n".join(
        f"| < {t} dB | {j:.2f} | {af:.2f} | {g:.2f} | {l:.2f} |" for t, j, af, g, l in table)
    note = f"""# Method note: FloodLens candidate zones (track 084)

**Label:** candidate change, not a verified flood.

## Data
- Before: `{BEFORE_ID}` ({BEFORE_DATE})
- After: `{AFTER_ID}` ({AFTER_DATE})
- NISAR L2 GCOV, Provisional maturity, HH polarization (HHHH), track 084, frame 17, ascending.
- Both scans share the same 10 m UTM 43N grid (checked), so they were subtracted pixel by pixel with no resampling.

## Processing
1. Clipped the Lahore box (about 2,907 x 3,818 pixels) from each file.
2. Converted linear power to dB: 10 * log10(HHHH).
3. Smoothed each scan with a {WIN} x {WIN} window (70 m) in linear power, to reduce speckle.
4. Change = after minus before, then removed the scene-wide median shift of {offset:.2f} dB.
5. Candidate pixel: change below {DROP_DB} dB, after-scan below {WATER_DB} dB, before-scan above {WATER_DB} dB.
6. Removed blobs under {MIN_PIXELS} pixels (0.5 ha). Each remaining connected blob is one zone.
7. River corridor: the large area dark on both dates at {WATER_DB} dB (the lower Ravi), grown into connected pixels below {corr_db} dB (hysteresis), plus a hand-drawn line along the upper Ravi where radar could not separate it (waypoints read from the map, approximate), then about 1 km around all of it.
8. Tier 1 = at least half the zone inside the corridor. Tier 2 = the rest, flagged likely agricultural.

## Results
- {len(zones)} zones: tier 1 {n1} zones ({a1:.2f} km2), tier 2 {len(zones) - n1} zones ({a2:.2f} km2).
- Ravi corridor water area (km2), before vs after:

| Threshold | {BEFORE_DATE} | {AFTER_DATE} | Gained | Lost |
|---|---|---|---|---|
{rows_md}

## Caveats
- The {WATER_DB} dB water cutoff, the {corr_db} dB corridor cutoff and the {DROP_DB} dB change threshold are first-pass choices made by inspection, not tuned or validated.
- The upper-river part of the corridor follows a hand-drawn line with approximate waypoints, not a surveyed centreline. See corridor_check.png.
- No ground truth or independent reference (for example Sentinel-1 or a flood map) has been compared yet.
- The scene-wide brightening of about {offset:.1f} dB (crops, soil moisture) was removed with a single median shift, which is crude.
- Paddy transplanting, irrigation and crop growth look like flooding in radar. Tier 2 zones are mostly this kind of area.
- Ascending geometry and early-morning pass time differ from the descending track 135 pair, so the two pairs cannot be chained.
- OpenStreetMap water and built-up masks have not been applied. Permanent water is approximated from the radar itself.
- Small zones near pixel-scale edges are sensitive to the speckle filter.
"""
    with open(os.path.join(OUT_DIR, "method_note.md"), "w", encoding="utf-8") as f:
        f.write(note)
    print("Saved method_note.md")

    # Picture
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib missing: pip install matplotlib")
        return
    step = 3
    hh, ww = (H // step) * step, (W // step) * step
    base = a[:hh:step, :ww:step]
    rgb = np.dstack([np.clip((base + 25) / 30, 0, 1)] * 3)
    rgb[maxpool(big, step)] = [0.2, 0.4, 1.0]
    rgb[maxpool(tier_img == 2, step)] = [1.0, 0.65, 0.0]
    rgb[maxpool(tier_img == 1, step)] = [1.0, 0.0, 0.0]
    plt.figure(figsize=(13, 10))
    plt.imshow(rgb)
    plt.title("Candidate zones: red = river corridor, orange = likely agricultural, blue = main river")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "zones_map.png"), dpi=110)
    print("Saved zones_map.png")

    # Check picture for the corridor: is the whole river in, and nothing else?
    chk = np.dstack([np.clip((base + 25) / 30, 0, 1)] * 3)
    chk[maxpool(corridor, step)] = chk[maxpool(corridor, step)] * 0.75 + np.array([1.0, 1.0, 0.0]) * 0.25
    chk[maxpool(big, step)] = [0.0, 0.9, 0.9]          # cyan: river body at the corridor cutoff
    chk[maxpool(big_strict, step)] = [0.2, 0.4, 1.0]   # blue: body at the strict cutoff
    if line.any():
        chk[maxpool(line, step)] = [1.0, 0.0, 1.0]      # magenta: hand-drawn upper-river line
    plt.figure(figsize=(13, 10))
    plt.imshow(chk)
    plt.title(f"Corridor check: blue = strict river {WATER_DB} dB, cyan = grown to {corr_db} dB, "
              "magenta = drawn line, yellow tint = 1 km corridor")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "corridor_check.png"), dpi=110)
    print("Saved corridor_check.png")


if __name__ == "__main__":
    main()