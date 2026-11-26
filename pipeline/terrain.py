"""Sample raster sources on the hex grid: elevation, land cover, GPW population density,
night lights, natural-hazard frequencies, cropland share, climate. Also project rivers.

Output: data/grid/terrain.json (per-hex arrays, null where there is no data).
"""
import glob, math, os, re
import numpy as np
from PIL import Image
import tifffile
import shapely
from shapely.geometry import shape
from common import *
from fetch_rasters import GIBS_LAYERS, GIBS_Z, TERRAIN_Z, gibs_tiles, terrain_tiles

Image.MAX_IMAGE_PIXELS = None


def parse_colormap(path):
    """GIBS colour map XML -> {(r,g,b): value}. Interval values use the bin midpoint."""
    txt = open(path).read()
    out = {}
    for m in re.finditer(r'<ColorMapEntry ([^>]*)/>', txt):
        a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        if a.get("nodata") == "true" or a.get("transparent") == "true" or "value" not in a and "sourceValue" not in a:
            continue
        rgb = tuple(int(v) for v in a["rgb"].split(","))
        v = a.get("value", a.get("sourceValue"))
        nums = [float(x) for x in re.findall(r'-?\d+\.?\d*(?:e[-+]?\d+)?', v)]
        if not nums:
            continue
        if "," in v and len(nums) == 2 and "[" in v and not v.startswith("0,"):
            lo, hi = nums
            # open-ended top bins such as [26,255) or [1000,1000000) mean ">= lower bound"
            val = lo if (hi >= 255 and lo > 0 and hi / lo > 5) else (lo + hi) / 2
        else:
            val = nums[0] if not v.startswith("0,") else nums[1]  # "0,17" water class in IGBP
        out[rgb] = val
    return out


def gibs_mosaic(key):
    tiles, span = gibs_tiles()
    rs = sorted({r for r, _ in tiles}); cs = sorted({c for _, c in tiles})
    H, W = len(rs) * 512, len(cs) * 512
    cmap = parse_colormap(f"{RAW}/gibs/{key}.xml") if os.path.exists(f"{RAW}/gibs/{key}.xml") else None
    arr = np.full((H, W), np.nan, np.float32)
    for r, c in tiles:
        im = np.asarray(Image.open(f"{RAW}/gibs/{key}/{r}_{c}.png").convert("RGBA")).astype(np.int32)
        if cmap is None:  # RGB composite: relative luminance 0..255
            v = (0.2126 * im[..., 0] + 0.7152 * im[..., 1] + 0.0722 * im[..., 2]).astype(np.float32)
        else:
            code = (im[..., 0] << 16) | (im[..., 1] << 8) | im[..., 2]
            keys = np.array([(a << 16) | (b << 8) | c_ for a, b, c_ in cmap], np.int64)
            vals = np.array(list(cmap.values()), np.float32)
            order = np.argsort(keys); keys, vals = keys[order], vals[order]
            pos = np.clip(np.searchsorted(keys, code), 0, len(keys) - 1)
            v = np.where(keys[pos] == code, vals[pos], np.nan).astype(np.float32)
        v[im[..., 3] == 0] = np.nan
        arr[(r - rs[0]) * 512:(r - rs[0] + 1) * 512, (c - cs[0]) * 512:(c - cs[0] + 1) * 512] = v
    res = 0.5625 / 2 ** GIBS_Z
    lon0, lat0 = cs[0] * span - 180, 90 - rs[0] * span

    def sample(lon, lat):
        col = ((lon - lon0) / res).astype(int); row = ((lat0 - lat) / res).astype(int)
        ok = (row >= 0) & (row < H) & (col >= 0) & (col < W)
        out = np.full(lon.shape, np.nan, np.float32)
        out[ok] = arr[row[ok], col[ok]]
        return out
    return sample


def terrain_sampler():
    tl = terrain_tiles()
    xs = sorted({x for x, _ in tl}); ys = sorted({y for _, y in tl})
    arr = np.zeros((len(ys) * 256, len(xs) * 256), np.float32)
    for x, y in tl:
        im = np.asarray(Image.open(f"{RAW}/terrain/{TERRAIN_Z}_{x}_{y}.png").convert("RGB")).astype(np.float32)
        arr[(y - ys[0]) * 256:(y - ys[0] + 1) * 256, (x - xs[0]) * 256:(x - xs[0] + 1) * 256] = im[..., 0] * 256 + im[..., 1] + im[..., 2] / 256 - 32768
    n = 2 ** TERRAIN_Z

    def sample(lon, lat):
        px = ((lon + 180) / 360 * n - xs[0]) * 256
        py = ((1 - np.arcsinh(np.tan(np.radians(lat))) / np.pi) / 2 * n - ys[0]) * 256
        return arr[np.clip(py.astype(int), 0, arr.shape[0] - 1), np.clip(px.astype(int), 0, arr.shape[1] - 1)]
    return sample


def worldclim(var):
    stack = np.stack([tifffile.imread(f) for f in sorted(glob.glob(f"{RAW}/worldclim/wc2.1_10m_{var}_*.tif"))]).astype(np.float32)
    stack[stack < (-500 if var == "prec" else -100)] = np.nan  # nodata (-32768 / -3.4e38)

    def sample(lon, lat):
        row = np.clip(((90 - lat) * 6).astype(int), 0, 1079); col = np.clip(((lon + 180) * 6).astype(int), 0, 2159)
        return stack[:, row, col]
    return sample


def rnd(a, d=1):
    return [None if (v is None or not np.isfinite(v)) else round(float(v), d) for v in a]


def main():
    g = read_json(f"{DATA}/grid/grid.json")
    kind = np.array(g["kind"]); N = kind.size
    cx, cy, cols, rows = cell_centers()
    off = sample_offsets(); S = len(off)
    lon, lat = unproject((cx[:, None] + off[None, :, 0]).ravel(), (cy[:, None] + off[None, :, 1]).ravel())
    land = (kind == 1) | (kind == 3) | (kind == 2)

    def stat(v, fn):
        v = v.reshape(N, S)
        with np.errstate(all="ignore"), __import__("warnings").catch_warnings():
            __import__("warnings").simplefilter("ignore")
            return fn(v, axis=1)

    out = {}
    el = terrain_sampler()(lon, lat)
    out["elev"] = rnd(stat(el, np.nanmean), 0)
    out["elev_std"] = rnd(stat(el, np.nanstd), 0)
    out["elev_max"] = rnd(stat(el, np.nanmax), 0)
    print("elevation done")

    lc = gibs_mosaic("landcover")(lon, lat).reshape(N, S)
    lc_frac = {}
    for cls in range(1, 18):
        lc_frac[cls] = np.nanmean(np.where(np.isnan(lc), np.nan, lc == cls), axis=1)
    out["lc_frac"] = {str(k): rnd(v * 100, 0) for k, v in lc_frac.items()}
    print("land cover done")

    for key in ("gpw2020", "nightlights", "flood", "drought", "cyclone", "landslide", "cropland"):
        v = gibs_mosaic(key)(lon, lat)
        out[key] = rnd(stat(v, np.nanmean), 2)
        print(key, "done", np.nanmax(stat(v, np.nanmean)))

    pr = worldclim("prec")(lon, lat)  # 12 x (N*S)
    ta = worldclim("tavg")(lon, lat)
    p_ann = np.nansum(pr, 0); p_ann[np.isnan(pr).all(0)] = np.nan
    out["precip"] = rnd(stat(p_ann, np.nanmean), 0)
    out["temp"] = rnd(stat(np.nanmean(ta, 0), np.nanmean), 1)
    out["temp_hot"] = rnd(stat(np.nanmax(ta, 0), np.nanmean), 1)
    out["temp_cold"] = rnd(stat(np.nanmin(ta, 0), np.nanmean), 1)
    # monsoon share: June–September rain / annual
    js = np.nansum(pr[5:9], 0)
    out["monsoon_share"] = rnd(stat(np.where(p_ann > 0, js / p_ann * 100, np.nan), np.nanmean), 0)
    print("climate done")

    # drop values outside land hexes except depth/elevation (sea depth is used for ocean vs coast)
    for k, v in list(out.items()):
        if k in ("elev", "elev_std", "elev_max"):
            continue
        if isinstance(v, dict):
            out[k] = {kk: [x if land[i] else None for i, x in enumerate(vv)] for kk, vv in v.items()}
        else:
            out[k] = [x if land[i] else None for i, x in enumerate(v)]

    # rivers: Natural Earth 10m centre lines (scale rank), projected to grid km
    rivers = []
    lo0, la0, lo1, la1 = BBOX
    box = shapely.box(lo0, la0, lo1, la1)
    for f in read_json(f"{RAW}/ne/ne_10m_rivers_lake_centerlines_scale_rank.geojson")["features"]:
        geom = shape(f["geometry"])
        if not geom.intersects(box):
            continue
        p = f["properties"]
        geom = geom.intersection(box)
        for line in getattr(geom, "geoms", [geom]):
            if line.geom_type != "LineString" or line.length < 0.05:
                continue
            xy = np.array(line.simplify(0.02).coords)
            px, py = project(xy[:, 0], xy[:, 1])
            rivers.append({"name": p.get("name") or "", "rank": int(p.get("scalerank", 9)),
                           "pts": [round(float(v), 1) for pair in zip(px, py) for v in pair]})
    out["rivers"] = rivers
    print("rivers", len(rivers))
    write_json(f"{DATA}/grid/terrain.json", out)


if __name__ == "__main__":
    main()
