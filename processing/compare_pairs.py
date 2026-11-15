"""
compare_pairs.py
Compares the two change layers on their shared pixels:
  A = track 135, Jul 17 -> Aug 10  (lahore_change_smooth_adj_db.tif)
  B = track 084, Jul 14 -> Jul 26  (t084_change_smooth_adj_db.tif)

Question: are there places that are DARKER on Jul 26 (B) and BRIGHTER again by
Aug 10 (A)? That pattern would fit temporary surface water in the flood window.
It would also fit paddy or irrigation timing, so treat it as a lead, not proof.

Put the track 084 outputs (from the Colab zip) in data\\processed first, then run:
    python processing\\compare_pairs.py
"""
import os

import numpy as np
import rasterio
from rasterio.windows import Window

OUT_DIR = os.path.join("data", "processed")
A_PATH = os.path.join(OUT_DIR, "lahore_change_smooth_adj_db.tif")
B_PATH = os.path.join(OUT_DIR, "t084_change_smooth_adj_db.tif")
THR = 3.0  # dB


def window_for(src, left, bottom, right, top):
    t = src.transform
    col0 = int(round((left - t.c) / t.a))
    row0 = int(round((top - t.f) / t.e))
    cols = int(round((right - left) / t.a))
    rows = int(round((top - bottom) / abs(t.e)))
    return Window(col0, row0, cols, rows)


def main():
    with rasterio.open(A_PATH) as a, rasterio.open(B_PATH) as b:
        if a.crs != b.crs:
            raise SystemExit(f"CRS differ: {a.crs} vs {b.crs}")
        if abs(a.transform.a - b.transform.a) > 1e-6:
            raise SystemExit("Pixel sizes differ.")
        left = max(a.bounds.left, b.bounds.left)
        right = min(a.bounds.right, b.bounds.right)
        bottom = max(a.bounds.bottom, b.bounds.bottom)
        top = min(a.bounds.top, b.bounds.top)
        if right <= left or top <= bottom:
            raise SystemExit("The two layers do not overlap.")
        # Pixel grids must line up (offsets a whole number of pixels apart).
        for src in (a, b):
            off = (left - src.transform.c) / src.transform.a
            if abs(off - round(off)) > 0.01:
                raise SystemExit("The grids are not aligned to the same pixel edges.")
        wa = window_for(a, left, bottom, right, top)
        wb = window_for(b, left, bottom, right, top)
        A = a.read(1, window=wa)
        B = b.read(1, window=wb)

    h, w = min(A.shape[0], B.shape[0]), min(A.shape[1], B.shape[1])
    A, B = A[:h, :w], B[:h, :w]
    ok = np.isfinite(A) & np.isfinite(B)
    print(f"Shared area: {ok.sum() / 1e4:.1f} km2 ({h} x {w} pixels)")

    r = np.corrcoef(A[ok][::50], B[ok][::50])[0, 1]
    print(f"Correlation between the two change layers: {r:.2f}")

    dark_B = ok & (B < -THR)   # darker by Jul 26
    bright_A = ok & (A > THR)  # brighter by Aug 10
    dark_A = ok & (A < -THR)
    bright_B = ok & (B > THR)
    both = dark_B & bright_A

    print(f"\nDarker by Jul 26 (change < -{THR} dB): {dark_B.sum() / 1e4:.2f} km2")
    print(f"Brighter by Aug 10 (change > +{THR} dB): {bright_A.sum() / 1e4:.2f} km2")
    print(f"Both (dark on Jul 26, bright again by Aug 10): {both.sum() / 1e4:.2f} km2")
    if dark_B.any():
        share = both.sum() / dark_B.sum()
        chance = bright_A.sum() / ok.sum()
        print(f"  Of the Jul 26 dark pixels, {share * 100:.0f}% are bright again by Aug 10 "
              f"(by chance you'd expect about {chance * 100:.0f}%)")
    print(f"Opposite pattern (bright Jul 26, dark Aug 10): {(bright_B & dark_A).sum() / 1e4:.2f} km2")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib missing: pip install matplotlib")
        return

    step = 3
    hh, ww = (h // step) * step, (w // step) * step

    def pool(m):
        return m[:hh, :ww].reshape(hh // step, step, ww // step, step).max(axis=(1, 3))

    rgb = np.ones((hh // step, ww // step, 3), dtype="float32") * 0.92
    rgb[pool(dark_B)] = [1.0, 0.8, 0.6]    # light orange: dark on Jul 26 only
    rgb[pool(bright_A)] = [0.7, 0.85, 1.0]  # light blue: bright on Aug 10 only
    rgb[pool(both)] = [0.8, 0.0, 0.0]      # red: both
    plt.figure(figsize=(13, 10))
    plt.imshow(rgb)
    plt.title("Red = dark on Jul 26 and bright again by Aug 10\n"
              "orange = dark Jul 26 only, light blue = bright Aug 10 only")
    plt.axis("off")
    plt.tight_layout()
    out = os.path.join(OUT_DIR, "pair_comparison.png")
    plt.savefig(out, dpi=110)
    print("Saved", out)


if __name__ == "__main__":
    main()
