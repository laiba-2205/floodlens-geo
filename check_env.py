import importlib
import sys

print("Python", sys.version.split()[0])

packages = [
    "numpy", "h5py", "rasterio", "pyproj", "shapely",
    "geopandas", "matplotlib", "asf_search", "earthaccess",
]

missing = []
for name in packages:
    try:
        module = importlib.import_module(name)
        print(f"OK    {name} {getattr(module, '__version__', '')}")
    except Exception as error:
        print(f"FAIL  {name}: {error}")
        missing.append(name)

print()
print("Everything imports. Environment is ready." if not missing
      else "Problems with: " + ", ".join(missing))
