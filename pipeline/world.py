"""Classify each hex into game terrain (water / relief / cover) with written rules and write
site/data/world.json. Rules are stored next to the data so the Almanac can show them."""
import numpy as np
import shapely
from shapely.geometry import LineString
from common import *

WATER = [
    {"id": 0, "name": "Land", "rule": "At least half of the hex's ~73 sample points fall inside the Survey of India outline (India) or a Natural Earth country (neighbours). Each state, UT and district gets at least one hex."},
    {"id": 1, "name": "Ocean", "rule": "Sea hex with mean depth below 200 m (AWS Terrain Tiles bathymetry) and no land neighbour."},
    {"id": 2, "name": "Coast", "rule": "Sea hex next to a land hex, or shallower than 200 m."},
    {"id": 3, "name": "Lake", "rule": "Hex inside India where Natural Earth 1:10m lakes cover at least half of the sample points."},
]
RELIEF = [
    {"id": 0, "name": "Flat", "rule": "Standard deviation of elevation inside the hex under 90 m."},
    {"id": 1, "name": "Hills", "rule": "Elevation standard deviation ≥ 90 m."},
    {"id": 2, "name": "Mountains", "rule": "Elevation standard deviation ≥ 300 m, or mean elevation ≥ 2,500 m."},
    {"id": 3, "name": "High peaks", "rule": "Mean elevation ≥ 4,500 m (high Himalaya, Karakoram, Ladakh ranges)."},
]
# MODIS IGBP classes: 1 ENF, 2 EBF, 3 DNF, 4 DBF, 5 mixed, 6 closed shrub, 7 open shrub, 8 woody savanna,
# 9 savanna, 10 grassland, 11 wetland, 12 cropland, 13 urban, 14 crop/natural mosaic, 15 snow, 16 barren, 17 water
COVER = [
    {"id": 0, "key": "none", "name": "None", "color": "#000000", "rule": "Water or no land-cover pixels."},
    {"id": 1, "key": "jungle", "name": "Rainforest", "color": "#2c5e2e", "igbp": [2], "rule": "Forest classes (IGBP 1–5) are the largest group and evergreen broadleaf (2) is the largest forest class."},
    {"id": 2, "key": "forest", "name": "Forest", "color": "#3f6b33", "igbp": [1, 3, 4, 5], "rule": "Forest classes are the largest group, not mostly evergreen broadleaf."},
    {"id": 3, "key": "woodland", "name": "Woodland", "color": "#64813c", "igbp": [8], "rule": "Woody savanna (8) is the largest group."},
    {"id": 4, "key": "grassland", "name": "Grassland", "color": "#8da04a", "igbp": [9, 10], "rule": "Savanna (9) plus grassland (10) is the largest group."},
    {"id": 5, "key": "scrub", "name": "Scrub", "color": "#a69a5e", "igbp": [6, 7], "rule": "Shrubland (6, 7) is the largest group and annual rain is ≥ 350 mm."},
    {"id": 6, "key": "farmland", "name": "Farmland", "color": "#b6ad52", "igbp": [12, 14], "rule": "Cropland (12) plus cropland/natural mosaic (14) is the largest group."},
    {"id": 7, "key": "floodplain", "name": "Floodplain", "color": "#97ad4a", "rule": "Farmland on flat relief with a major river (Natural Earth scale rank ≤ 6) within 0.6 hex radius of the centre."},
    {"id": 8, "key": "wetland", "name": "Wetland & mangrove", "color": "#4d8270", "igbp": [11], "rule": "Permanent wetland (11) is the largest group."},
    {"id": 9, "key": "desert", "name": "Desert", "color": "#d6bf86", "igbp": [16], "rule": "Barren (16) is the largest group, or shrubland with annual rain under 350 mm (WorldClim 2.1)."},
    {"id": 10, "key": "cold_desert", "name": "Cold desert", "color": "#a59f8e", "rule": "Barren, shrub or grass dominant and mean elevation ≥ 3,000 m."},
    {"id": 11, "key": "snow", "name": "Snow & ice", "color": "#e8eef2", "igbp": [15], "rule": "Permanent snow and ice (15) is the largest group."},
    {"id": 12, "key": "urban", "name": "Urban", "color": "#8a8378", "igbp": [13], "rule": "Urban and built-up land (13) covers ≥ 20% of the hex, whatever else is there."},
]


def classify(g, t):
    N = len(g["kind"]); cols, rows = g["cols"], g["rows"]
    kind = np.array(g["kind"])
    elev = np.array([np.nan if v is None else v for v in t["elev"]], float)
    std = np.array([np.nan if v is None else v for v in t["elev_std"]], float)
    precip = np.array([np.nan if v is None else v for v in t["precip"]], float)
    fr = {int(k): np.array([0 if x is None else x for x in v], float) for k, v in t["lc_frac"].items()}
    is_land = (kind == 1) | (kind == 2)
    water = np.zeros(N, np.int8)
    for i in range(N):
        if kind[i] == 3:
            water[i] = 3
        elif kind[i] == 0:
            near = any(is_land[j] for j in neighbors(i, cols, rows))
            water[i] = 2 if near or not (elev[i] < -200) else 1
    relief = np.zeros(N, np.int8)
    relief[std >= 90] = 1
    relief[(std >= 300) | (elev >= 2500)] = 2
    relief[elev >= 4500] = 3
    relief[~is_land] = 0

    # rivers near hex centres (major rivers only)
    cx, cy, _, _ = cell_centers()
    lines = [LineString(np.array(r["pts"]).reshape(-1, 2)) for r in t["rivers"] if r["rank"] <= 6]
    river_near = np.zeros(N, bool)
    if lines:
        tree = shapely.STRtree(lines)
        pts = shapely.points(cx, cy)
        idx = tree.query(pts, predicate="dwithin", distance=0.6 * HEX_R)
        river_near[np.unique(idx[0])] = True

    groups = {
        "forest": sum(fr[k] for k in (1, 2, 3, 4, 5)), "woodland": fr[8], "grassland": fr[9] + fr[10],
        "scrub": fr[6] + fr[7], "farmland": fr[12] + fr[14], "wetland": fr[11], "snow": fr[15], "barren": fr[16],
    }
    names = list(groups); M = np.stack([groups[n] for n in names], 1)
    dom = np.array(names)[M.argmax(1)]
    total = M.sum(1)
    cover = np.zeros(N, np.int8)
    id_of = {c["key"]: c["id"] for c in COVER}
    for i in np.nonzero(is_land & (total > 0))[0]:
        d = dom[i]
        if d == "forest":
            c = "jungle" if fr[2][i] >= max(fr[k][i] for k in (1, 3, 4, 5)) else "forest"
        elif d == "scrub":
            c = "desert" if precip[i] < 350 else "scrub"
        elif d == "barren":
            c = "desert"
        else:
            c = d
        if c in ("desert", "scrub", "grassland") and elev[i] >= 3000:
            c = "cold_desert"
        if c == "farmland" and relief[i] == 0 and river_near[i]:
            c = "floodplain"
        if fr[13][i] >= 20:
            c = "urban"
        cover[i] = id_of[c]
    return water, relief, cover, river_near


def main():
    g = read_json(f"{DATA}/grid/grid.json"); t = read_json(f"{DATA}/grid/terrain.json")
    states, _ = load_states()
    water, relief, cover, river_near = classify(g, t)
    kind = g["kind"]
    land = [i for i, k in enumerate(kind) if k == 1]
    d20 = [{"key": k, "name": k.split("|")[1], "state": None, "area_km2": a} for k, a in zip(g["d20_keys"], g["d20_area_km2"])]
    _, alias = load_states()
    for d in d20:
        d["state"] = alias[d["key"].split("|")[0].lower()]
    import csv
    ref11 = {r["censuscode"]: r for r in csv.DictReader(open(f"{DATA}/ref/districts2011.csv"))}
    c11 = {r["key"]: r["state"] for r in read_json(f"{DATA}/normalized/census2011_district.json")["rows"]}
    d11 = []
    for k, a in zip(g["d11_keys"], g["d11_area_km2"]):
        r = ref11.get(k, {})
        d11.append({"key": k, "name": r.get("district", k), "state": c11.get(k) or alias.get(r.get("state", "").lower()), "area_km2": a})
    world = {
        "version": 1,
        "grid": {"cols": g["cols"], "rows": g["rows"], "x0": g["x0"], "y0": g["y0"], "hexW": g["hex_w"], "hexR": g["hex_r"],
                 "projection": "Lambert conformal conic, lon0 82°E, lat0 24°N, standard parallels 12.47°N/35.17°N, sphere R=6371 km; units km"},
        "kind": kind, "state": g["state"], "district": g["d20"], "district11": g["d11"], "disputed": g["disputed"], "country": g["country"],
        "water": water.tolist(), "relief": relief.tolist(), "cover": cover.tolist(),
        "elev": [None if v is None else int(v) for v in t["elev"]],
        "land": land,
        "tables": {"water": WATER, "relief": RELIEF, "cover": COVER},
        "states": [{"id": s["id"], "name": s["name"], "type": s["type"], "area_km2": a} for s, a in zip(states, g["state_area_km2"])],
        "districts": d20,
        "districts11": d11,
        "countries": g["countries"], "disputedNames": g["disputed_names"],
        "rivers": [r for r in t["rivers"]],
    }
    write_json(f"{SITE_DATA}/world.json", world)
    import collections
    print("cover", collections.Counter(COVER[c]["name"] for c, k in zip(cover, kind) if k == 1))
    print("relief", collections.Counter(RELIEF[r]["name"] for r, k in zip(relief, kind) if k == 1))
    print("water", collections.Counter(WATER[w]["name"] for w in water))


if __name__ == "__main__":
    main()
