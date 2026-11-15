"""
prepare_lahore.py
Clips the Lahore box out of the two NISAR GCOV files, converts HH to dB,
and saves small GeoTIFFs plus a change layer (after minus before).

Run from the project folder (with .venv active):
    python processing\\prepare_lahore.py

Outputs go to data\\processed\\
"""
import glob
import os
import sys

import h5py
import numpy as np
import rasterio
from rasterio.transform import from_origin

# Lahore box in the scene grid (from the earlier inspection)
ROW0, ROW1 = 6449, 9356
COL0, COL1 = 13867, 17684

GRID = "/science/LSAR/GCOV/grids/frequencyA"
RAW_DIR = os.path.join("data", "raw")
OUT_DIR = os.path.join("data", "processed")
os.makedirs(OUT_DIR, exist_ok=True)


def find_one(prefix):
    hits = glob.glob(os.path.join(RAW_DIR, prefix + "*.h5"))
    if len(hits) != 1:
        sys.exit(f"Expected 1 file starting with {prefix} in {RAW_DIR}, found {len(hits)}")
    return hits[0]


def load_db(path):
    """Read only the Lahore window of HHHH and return (dB array, transform, epsg, mask window)."""
    with h5py.File(path, "r") as f:
        g = f[GRID]
        x = g["xCoordinates"][COL0:COL1]
        y = g["yCoordinates"][ROW0:ROW1]
        epsg = int(g["projection"][()])
        lin = g["HHHH"][ROW0:ROW1, COL0:COL1].astype("float32")
        mask = g["mask"][ROW0:ROW1, COL0:COL1]

    valid = np.isfinite(lin) & (lin > 0)
    db = np.full(lin.shape, np.nan, dtype="float32")
    db[valid] = 10.0 * np.log10(lin[valid])

    # Coordinates are pixel centres, so shift by half a pixel to get the top-left corner.
    transform = from_origin(float(x[0]) - 5.0, float(y[0]) + 5.0, 10.0, 10.0)
    return db, transform, epsg, mask


def save_tif(path, arr, transform, epsg):
    with rasterio.open(
        path, "w", driver="GTiff", height=arr.shape[0], width=arr.shape[1],
        count=1, dtype="float32", crs=f"EPSG:{epsg}", transform=transform,
        nodata=np.nan, compress="deflate",
    ) as dst:
        dst.write(arr, 1)


def describe(name, arr):
    ok = np.isfinite(arr)
    print(f"{name}: valid {ok.sum():,} of {arr.size:,} ({100 * ok.mean():.2f}%)")
    if ok.any():
        p = np.percentile(arr[ok], [1, 5, 50, 95, 99])
        print(f"  dB percentiles 1/5/50/95/99: {np.round(p, 2)}")


def main():
    before_path = find_one("NISAR_L2_PR_GCOV_025")  # July 17
    after_path = find_one("NISAR_L2_PR_GCOV_027")   # August 10

    print("Reading July 17 ...")
    before, t1, e1, m1 = load_db(before_path)
    print("Reading August 10 ...")
    after, t2, e2, m2 = load_db(after_path)

    if t1 != t2 or e1 != e2 or before.shape != after.shape:
        sys.exit("Grids do not match. Stop and check.")

    change = after - before  # negative = got darker = possible new water

    save_tif(os.path.join(OUT_DIR, "lahore_hh_db_20260717.tif"), before, t1, e1)
    save_tif(os.path.join(OUT_DIR, "lahore_hh_db_20260810.tif"), after, t1, e1)
    save_tif(os.path.join(OUT_DIR, "lahore_change_db.tif"), change, t1, e1)

    describe("July 17 dB", before)
    describe("Aug 10 dB", after)
    describe("Change dB (after - before)", change)

    ok = np.isfinite(change)
    for thr in (-2, -3, -4, -5):
        n = int((change[ok] < thr).sum())
        print(f"pixels with change < {thr} dB: {n:,} ({n * 100 / 1e6:.2f} km2)")

    print("\nMask values in window (July 17):", dict(zip(*np.unique(m1, return_counts=True))))
    print("Mask values in window (Aug 10):", dict(zip(*np.unique(m2, return_counts=True))))
    print(f"\nSaved 3 GeoTIFFs in {OUT_DIR}")


if __name__ == "__main__":
    main()
