"""Print what is inside a NISAR GCOV HDF5 file without loading the whole image.

Usage:  python processing/inspect_nisar.py data/raw/<file>.h5
"""
import sys

import h5py
import numpy as np

if len(sys.argv) < 2:
    sys.exit("Usage: python processing/inspect_nisar.py <path to .h5 file>")

path = sys.argv[1]
GRID = "/science/LSAR/GCOV/grids/frequencyA"
IDENT = "/science/LSAR/identification"


def text(value):
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return str(value)


def list_everything(name, obj):
    if isinstance(obj, h5py.Dataset):
        print(f"  {name}  shape={obj.shape} dtype={obj.dtype}")


with h5py.File(path, "r") as f:
    print("FILE:", path)
    print("Top-level groups:", list(f.keys()))

    if IDENT in f:
        print("\n--- Identification ---")
        ident = f[IDENT]
        for key in ["zeroDopplerStartTime", "zeroDopplerEndTime", "trackNumber",
                    "frameNumber", "orbitPassDirection", "boundingPolygon"]:
            if key in ident:
                print(f"{key}: {text(ident[key][()])}")
    else:
        print("\nIdentification group not found at", IDENT)

    if GRID not in f:
        print("\nExpected grid group not found:", GRID)
        print("Listing every dataset in the file so we can find the right path:")
        f.visititems(list_everything)
        sys.exit(1)

    grid = f[GRID]
    print("\n--- Datasets in", GRID, "---")
    for key, item in grid.items():
        if isinstance(item, h5py.Dataset):
            print(f"  {key}  shape={item.shape} dtype={item.dtype}")

    if "listOfPolarizations" in grid:
        pols = [text(p) for p in grid["listOfPolarizations"][()]]
        print("\nPolarizations:", pols)

    if "xCoordinates" in grid and "yCoordinates" in grid:
        x = grid["xCoordinates"][()]
        y = grid["yCoordinates"][()]
        print(f"\nx range: {x.min():.1f} to {x.max():.1f}  ({len(x)} columns)")
        print(f"y range: {y.min():.1f} to {y.max():.1f}  ({len(y)} rows)")
    for key in ["xCoordinateSpacing", "yCoordinateSpacing"]:
        if key in grid:
            print(f"{key}: {grid[key][()]}")
    if "projection" in grid:
        proj = grid["projection"]
        print("projection value:", proj[()])
        print("projection attributes:", {k: text(v) for k, v in proj.attrs.items()})

    if "HHHH" in grid:
        hh = grid["HHHH"]
        rows, cols = hh.shape
        r, c = rows // 2, cols // 2
        patch = hh[r:r + 5, c:c + 5]
        print("\nSmall 5x5 sample of HHHH from the centre (linear power):")
        print(patch)
        print("NaN count in sample:", int(np.isnan(patch).sum()))
