"""
make_candidates.py
Step 3: pick candidate change pixels, drop tiny specks, and draw an overlay
so you can see whether they sit on the river / low ground or are scattered.

Run from the project folder (with .venv active):
    python processing\\make_candidates.py
"""
import os

import numpy as np
import rasterio
from rasterio.features import sieve

from make_preview import smooth_db  # same folder

OUT_DIR = os.path.join("data", "processed")
WATER_DB = -15.0    # "dark enough to be water" guess, checked below
DROP_DB = -3.0      # change threshold (after offset removal)
MIN_PIXELS = 50     # 50 px x 100 m2 = 0.5 hectare


def maxpool(mask, step):
    h = (mask.shape[0] // step) * step
    w = (mask.shape[1] // step) * step
    m = mask[:h, :w].reshape(h // step, step, w // step, step)
    return m.max(axis=(1, 3))


def main():
    with rasterio.open(os.path.join(OUT_DIR, "lahore_hh_db_20260717.tif")) as s:
        before = s.read(1)
        profile = s.profile
    with rasterio.open(os.path.join(OUT_DIR, "lahore_hh_db_20260810.tif")) as s:
        after = s.read(1)

    b = smooth_db(before)
    a = smooth_db(after)
    change = (a - b) - np.median(a - b)

    # 1. Check the water threshold: how much is dark in BOTH scans (permanent water)?
    print("Smoothed Aug dB percentiles 1/2/5/10:", np.round(np.percentile(a, [1, 2, 5, 10]), 1))
    print("Area dark in BOTH scans (permanent water guess):")
    for t in (-13, -15, -17, -19):
        print(f"  < {t} dB: {((a < t) & (b < t)).sum() / 1e4:.1f} km2")

    # 2. Candidates
    cand = (change < DROP_DB) & (a < WATER_DB) & (b > WATER_DB)
    print(f"\nRaw candidate pixels: {cand.sum():,} ({cand.sum() / 1e4:.2f} km2)")
    clean = sieve(cand.astype("uint8"), size=MIN_PIXELS, connectivity=8)
    print(f"After removing blobs under {MIN_PIXELS} px: {int(clean.sum()):,} px "
          f"({clean.sum() / 1e4:.2f} km2)")

    prof = profile.copy()
    prof.update(dtype="uint8", nodata=0, compress="deflate")
    with rasterio.open(os.path.join(OUT_DIR, "lahore_candidates.tif"), "w", **prof) as dst:
        dst.write(clean.astype("uint8"), 1)
    print("Saved lahore_candidates.tif")

    # 3. Overlay picture
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib missing: pip install matplotlib")
        return

    step = 3
    base = a[: (a.shape[0] // step) * step : step, : (a.shape[1] // step) * step : step]
    perm = maxpool((a < WATER_DB) & (b < WATER_DB), step)
    cands = maxpool(clean.astype(bool), step)

    rgb = np.dstack([np.clip((base + 25) / 30, 0, 1)] * 3)
    rgb[perm] = [0.2, 0.4, 1.0]    # blue = dark in both scans
    rgb[cands] = [1.0, 0.1, 0.1]   # red = new dark candidate
    plt.figure(figsize=(13, 10))
    plt.imshow(rgb)
    plt.title("Blue = dark in both scans, Red = candidate new dark area")
    plt.axis("off")
    plt.tight_layout()
    out = os.path.join(OUT_DIR, "lahore_candidates.png")
    plt.savefig(out, dpi=110)
    print("Saved", out)


if __name__ == "__main__":
    main()
