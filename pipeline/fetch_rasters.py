"""Download raster tiles: AWS Terrain Tiles (terrarium), NASA GIBS layers, WorldClim 2.1 (10 arc-min)."""
import math, os, zipfile
from concurrent.futures import ThreadPoolExecutor
import requests
from common import RAW, BBOX

UA = {"User-Agent": "india-civ-data-pipeline/1.0"}
GIBS = "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/{layer}/default/{time}/{tms}/{z}/{row}/{col}.png"
GIBS_LAYERS = {
    # id: (layer, time, tile matrix set)
    "landcover": ("MODIS_Combined_L3_IGBP_Land_Cover_Type_Annual", "2023-01-01", "500m"),
    "gpw2020": ("GPW_Population_Density_2020", "default", "1km"),
    "nightlights": ("VIIRS_Black_Marble", "2016-01-01", "500m"),
    "flood": ("NDH_Flood_Hazard_Frequency_Distribution_1985-2003", "default", "1km"),
    "drought": ("NDH_Drought_Hazard_Frequency_Distribution_1980-2000", "default", "1km"),
    "cyclone": ("NDH_Cyclone_Hazard_Frequency_Distribution_1980-2000", "default", "1km"),
    "landslide": ("NDH_Landslide_Hazard_Distribution_2000", "default", "1km"),
    "cropland": ("Agricultural_Lands_Croplands_2000", "default", "1km"),
}
GIBS_Z = 5  # 0.5625/2^5 = 0.0176 deg per pixel (~1.9 km); 512 px tiles span 9 deg
TERRAIN_Z = 7


def get(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    r = requests.get(url, headers=UA, timeout=120)
    r.raise_for_status()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(r.content)
    return path


def gibs_tiles():
    span = 0.5625 / 2 ** GIBS_Z * 512
    c0, c1 = int((BBOX[0] + 180) // span), int((BBOX[2] + 180) // span)
    r0, r1 = int((90 - BBOX[3]) // span), int((90 - BBOX[1]) // span)
    return [(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)], span


def terrain_tiles():
    n = 2 ** TERRAIN_Z
    def tx(lon): return int((lon + 180) / 360 * n)
    def ty(lat): return int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
    return [(x, y) for x in range(tx(BBOX[0]), tx(BBOX[2]) + 1) for y in range(ty(BBOX[3]), ty(BBOX[1]) + 1)]


def main():
    jobs = []
    for x, y in terrain_tiles():
        jobs.append((f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{TERRAIN_Z}/{x}/{y}.png", f"{RAW}/terrain/{TERRAIN_Z}_{x}_{y}.png"))
    tiles, _ = gibs_tiles()
    for k, (layer, time, tms) in GIBS_LAYERS.items():
        cmap = {"landcover": "MODIS_IGBP_Land_Cover_Type", "nightlights": None}.get(k, layer)
        if cmap:
            jobs.append((f"https://gibs.earthdata.nasa.gov/colormaps/v1.3/{cmap}.xml", f"{RAW}/gibs/{k}.xml"))
        for r, c in tiles:
            jobs.append((GIBS.format(layer=layer, time=time, tms=tms, z=GIBS_Z, row=r, col=c), f"{RAW}/gibs/{k}/{r}_{c}.png"))
    for v in ("prec", "tavg"):
        jobs.append((f"https://geodata.ucdavis.edu/climate/worldclim/2_1/base/wc2.1_10m_{v}.zip", f"{RAW}/worldclim/wc2.1_10m_{v}.zip"))
    with ThreadPoolExecutor(8) as ex:
        errs = [e for e in ex.map(lambda j: _safe(*j), jobs) if e]
    for e in errs:
        print("FAILED", e)
    for v in ("prec", "tavg"):
        with zipfile.ZipFile(f"{RAW}/worldclim/wc2.1_10m_{v}.zip") as z:
            z.extractall(f"{RAW}/worldclim/")
    print("jobs", len(jobs), "failed", len(errs))


def _safe(url, path):
    try:
        get(url, path)
    except Exception as e:
        return f"{url}: {e}"


if __name__ == "__main__":
    main()
