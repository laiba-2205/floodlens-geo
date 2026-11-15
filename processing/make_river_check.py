"""
make_river_check.py
Step 4: isolate the Ravi corridor and measure how its water changed
between July 17 and Aug 10. Also splits candidates into river vs farmland.

Run from the project folder (with .venv active):
    python processing\\make_river_check.py
"""
import os

import numpy as np
import rasterio
from rasterio.features import sieve

from make_preview import box_filter, smooth_db  # same folder

OUT_DIR = os.path.join("data", "processed")
BIG_WATER_PX = 5000   # 50 ha: keeps the river, drops ponds
BUFFER_WIN = 201      # ~1 km square buffer around the river


def maxpool(mask, step):
    h = (mask.shape[0] // step) * step
    w = (mask.shape[1] // step) * step
    return mask[:h, :w].reshape(h // step, step, w // step, step).max(axis=(1, 3))


def main():
    with rasterio.open(os.path.join(OUT_DIR, "lahore_hh_db_20260717.tif")) as s:
        b = smooth_db(s.read(1))
    with rasterio.open(os.path.join(OUT_DIR, "lahore_hh_db_20260810.tif")) as s:
        a = smooth_db(s.read(1))
    with rasterio.open(os.path.join(OUT_DIR, "lahore_candidates.tif")) as s:
        cand = s.read(1).astype(bool)

    # River corridor from the large permanent-water body at -15 dB
    both15 = (a < -15) & (b < -15)
    big = sieve(both15.astype("uint8"), size=BIG_WATER_PX, connectivity=8).astype(bool)
    corridor = box_filter(big.astype("float32"), BUFFER_WIN) > 0
    print(f"Main river body (dark in both): {big.sum() / 1e4:.2f} km2")
    print(f"Corridor (about 1 km around it): {corridor.sum() / 1e4:.1f} km2\n")

    print("Water area inside the corridor (km2):")
    for t in (-13, -14, -15, -16):
        wj, wa = b < t, a < t
        inside = corridor
        print(f"  < {t} dB | Jul 17: {(wj & inside).sum() / 1e4:6.2f} | "
              f"Aug 10: {(wa & inside).sum() / 1e4:6.2f} | "
              f"gained: {(wa & ~wj & inside).sum() / 1e4:5.2f} | "
              f"lost: {(wj & ~wa & inside).sum() / 1e4:5.2f}")

    print(f"\nCandidates in river corridor: {(cand & corridor).sum() / 1e4:.2f} km2")
    print(f"Candidates outside (farmland etc.): {(cand & ~corridor).sum() / 1e4:.2f} km2")

    # Picture: zoom on the corridor, gained = red, lost = yellow, kept = blue
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib missing: pip install matplotlib")
        return

    rows = np.where(corridor.any(axis=1))[0]
    cols = np.where(corridor.any(axis=0))[0]
    r0, r1, c0, c1 = rows[0], rows[-1] + 1, cols[0], cols[-1] + 1
    t = -15
    wj, wa = (b < t)[r0:r1, c0:c1], (a < t)[r0:r1, c0:c1]
    step = 2
    base = a[r0:r1:step, c0:c1:step]
    rgb = np.dstack([np.clip((base + 25) / 30, 0, 1)] * 3)
    rgb[maxpool(wj & wa, step)[: rgb.shape[0], : rgb.shape[1]]] = [0.2, 0.4, 1.0]
    rgb[maxpool(wa & ~wj, step)[: rgb.shape[0], : rgb.shape[1]]] = [1.0, 0.1, 0.1]
    rgb[maxpool(wj & ~wa, step)[: rgb.shape[0], : rgb.shape[1]]] = [1.0, 0.9, 0.1]
    plt.figure(figsize=(13, 10))
    plt.imshow(rgb)
    plt.title("Ravi corridor: blue = water both dates, red = gained by Aug 10, yellow = lost")
    plt.axis("off")
    plt.tight_layout()
    out = os.path.join(OUT_DIR, "ravi_corridor.png")
    plt.savefig(out, dpi=110)
    print("Saved", out)


if __name__ == "__main__":
    main()
