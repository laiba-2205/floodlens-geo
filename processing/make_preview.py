"""
make_preview.py
Step 2: smooth speckle, remove the scene-wide brightness shift, save a cleaner
change layer, and make a preview PNG so you can look at it.

Run from the project folder (with .venv active):
    python processing\\make_preview.py
"""
import os

import numpy as np
import rasterio

OUT_DIR = os.path.join("data", "processed")
WIN = 7  # smoothing window in pixels (7 x 10 m = 70 m)


def box_filter(a, win):
    """Mean over a win x win window, computed with an integral image."""
    pad = win // 2
    p = np.pad(a, pad, mode="edge").astype("float64")
    c = p.cumsum(axis=0).cumsum(axis=1)
    c = np.pad(c, ((1, 0), (1, 0)))
    s = c[win:, win:] - c[:-win, win:] - c[win:, :-win] + c[:-win, :-win]
    return (s / (win * win)).astype("float32")


def smooth_db(db):
    lin = 10.0 ** (db / 10.0)
    return 10.0 * np.log10(box_filter(lin, WIN))


def main():
    with rasterio.open(os.path.join(OUT_DIR, "lahore_hh_db_20260717.tif")) as s:
        before = s.read(1)
        profile = s.profile
    with rasterio.open(os.path.join(OUT_DIR, "lahore_hh_db_20260810.tif")) as s:
        after = s.read(1)

    b = smooth_db(before)
    a = smooth_db(after)
    raw_change = a - b
    offset = float(np.nanmedian(raw_change))
    change = raw_change - offset
    print(f"Smoothed with {WIN}x{WIN} window. Median offset removed: {offset:.2f} dB")

    p = np.percentile(change, [1, 5, 50, 95, 99])
    print("Adjusted change percentiles 1/5/50/95/99:", np.round(p, 2))

    print("\nCandidate counts (km2):")
    for thr in (-2, -3, -4):
        drop = change < thr
        both = drop & (a < -15) & (b > -15)
        print(f"  change < {thr} dB: {drop.sum() / 1e4:.2f} | "
              f"and Aug < -15 dB and Jul > -15 dB: {both.sum() / 1e4:.2f}")

    prof = profile.copy()
    prof.update(dtype="float32", nodata=np.nan, compress="deflate")
    with rasterio.open(os.path.join(OUT_DIR, "lahore_change_smooth_adj_db.tif"), "w", **prof) as dst:
        dst.write(change.astype("float32"), 1)
    print("\nSaved lahore_change_smooth_adj_db.tif")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed. Run: pip install matplotlib   then rerun for the PNG.")
        return

    step = 4  # downsample for display
    fig, ax = plt.subplots(1, 3, figsize=(18, 6))
    ax[0].imshow(b[::step, ::step], cmap="gray", vmin=-25, vmax=5)
    ax[0].set_title("July 17 (dB, smoothed)")
    ax[1].imshow(a[::step, ::step], cmap="gray", vmin=-25, vmax=5)
    ax[1].set_title("Aug 10 (dB, smoothed)")
    im = ax[2].imshow(change[::step, ::step], cmap="RdBu", vmin=-8, vmax=8)
    ax[2].set_title("Change (Aug - Jul), offset removed\nblue = brighter, red = darker")
    fig.colorbar(im, ax=ax[2], shrink=0.7)
    for x in ax:
        x.axis("off")
    plt.tight_layout()
    out = os.path.join(OUT_DIR, "lahore_preview.png")
    plt.savefig(out, dpi=110)
    print("Saved", out)


if __name__ == "__main__":
    main()
