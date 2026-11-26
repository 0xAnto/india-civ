"""Build the hex grid: land/sea, state, district (2011 and ~2020) ownership and area weights.

Method: each hex gets ~73 evenly spaced sample points. A point is tested against the
Survey of India outline, state polygons, both district vintages, the areas that India
claims but does not administer, Natural Earth neighbour countries and lakes.
Shares of sample points are area shares (resolution ~1/73 of a hex, ~4.7 km²).
"""
import json, os, sys, collections
import numpy as np
import shapefile, shapely
from shapely.geometry import shape
from common import *

B = os.path.join(RAW, "boundaries"); NE = os.path.join(RAW, "ne")


def proj_geom(g):
    return shapely.transform(g, lambda a: np.stack(project(a[:, 0], a[:, 1]), 1))


def geojson_feats(p):
    return read_json(p)["features"]


def shp_feats(p):
    r = shapefile.Reader(p)
    names = [f[0] for f in r.fields[1:]]
    return [{"properties": dict(zip(names, sr.record)), "geometry": sr.shape.__geo_interface__} for sr in r.iterShapeRecords()]


def label(polys, px, py, mask=None):
    """Index of the polygon that contains each point (-1 if none)."""
    out = np.full(px.shape, -1, np.int32)
    idx = np.nonzero(mask)[0] if mask is not None else np.arange(px.size)
    for k, g in enumerate(polys):
        if g is None or g.is_empty:
            continue
        x0, y0, x1, y1 = g.bounds
        sel = idx[(px[idx] >= x0) & (px[idx] <= x1) & (py[idx] >= y0) & (py[idx] <= y1)]
        if sel.size == 0:
            continue
        shapely.prepare(g)
        hit = sel[shapely.contains_xy(g, px[sel], py[sel])]
        out[hit[out[hit] < 0]] = k
    return out


def main():
    states, alias = load_states()
    sid = {s["id"]: i for i, s in enumerate(states)}
    cx, cy, cols, rows = cell_centers()
    off = sample_offsets(); S = len(off)
    px = (cx[:, None] + off[None, :, 0]).ravel()
    py = (cy[:, None] + off[None, :, 1]).ravel()
    N = cx.size
    print("cells", N, "samples", px.size)

    india = proj_geom(shapely.union_all([shape(f["geometry"]) for f in geojson_feats(f"{B}/india-soi.geojson")]))
    in_india = label([india], px, py) == 0
    print("india samples", in_india.sum())

    # states
    sf = shp_feats(f"{B}/states_Admin2.shp")
    st_geoms = [None] * len(states)
    for f in sf:
        k = alias[f["properties"]["ST_NM"].lower()]
        st_geoms[sid[k]] = proj_geom(shape(f["geometry"]).buffer(0))
    st_lab = label(st_geoms, px, py, in_india)

    # districts ~2020
    d20_feats = [f for f in geojson_feats(f"{B}/districts_current.geojson") if "district" in f["properties"]]
    d20_groups = collections.OrderedDict()
    for f in d20_feats:
        p = f["properties"]
        d20_groups.setdefault(f'{p["st_nm"]}|{p["district"]}', []).append(shape(f["geometry"]).buffer(0))
    d20_keys = list(d20_groups)
    d20_geoms = [proj_geom(shapely.union_all(v)) for v in d20_groups.values()]
    d20_lab = label(d20_geoms, px, py, in_india)

    # districts 2011
    d11_feats = shp_feats(f"{B}/2011_Dist.shp")
    d11_keys = [str(f["properties"]["censuscode"]) for f in d11_feats]
    d11_geoms = [proj_geom(shape(f["geometry"]).buffer(0)) for f in d11_feats]
    d11_lab = label(d11_geoms, px, py, in_india)

    # areas inside India's official outline that India does not administer
    disp_geoms, disp_names = [], []
    for f in geojson_feats(f"{B}/pok.geojson"):
        disp_geoms.append(shape(f["geometry"]).buffer(0)); disp_names.append("Pakistan")
    for f in geojson_feats(f"{B}/shaksgam.geojson"):
        disp_geoms.append(shape(f["geometry"]).buffer(0)); disp_names.append("China")
    for f in geojson_feats(f"{B}/disputed-lsib.geojson"):
        if f["properties"]["COUNTRY_NA"].startswith("Aksai Chin"):
            disp_geoms.append(shape(f["geometry"]).buffer(0)); disp_names.append("China")
    disp_lab = label([proj_geom(g) for g in disp_geoms], px, py, in_india)

    # neighbours and lakes (Natural Earth, India point of view)
    nf = [f for f in geojson_feats(f"{NE}/ne_10m_admin_0_countries_ind.geojson") if f["properties"]["ADMIN"] != "India"]
    lo0, la0, lo1, la1 = BBOX
    box = shapely.box(lo0 - 2, la0 - 2, lo1 + 2, la1 + 2)
    nf = [f for f in nf if shape(f["geometry"]).intersects(box)]
    c_names = [f["properties"]["ADMIN"] for f in nf]
    c_lab = label([proj_geom(shape(f["geometry"]).intersection(box)) for f in nf], px, py, ~in_india)
    lakes = [shape(f["geometry"]) for f in geojson_feats(f"{NE}/ne_10m_lakes.geojson")]
    lakes = [proj_geom(g) for g in lakes if g.intersects(box)]
    lake_any = label([shapely.union_all(lakes)], px, py) == 0

    def per_cell(a):
        return a.reshape(N, S)

    fi = per_cell(in_india).mean(1)
    fl = per_cell(lake_any & in_india).mean(1)
    fc = per_cell(c_lab >= 0).mean(1)
    kind = np.zeros(N, np.int8)  # 0 sea, 1 India land, 2 foreign land, 3 lake (inside India)
    kind[fc >= 0.5] = 2
    kind[fi >= 0.5] = 1
    kind[(kind == 1) & (fl >= 0.5)] = 3

    def majority(lab, cells):
        L = per_cell(lab)
        out = np.full(N, -1, np.int32)
        for i in cells:
            v = L[i][L[i] >= 0]
            if v.size:
                out[i] = np.bincount(v).argmax()
        return out

    # every state / district gets at least one land hex (small UTs, island districts)
    forced = 0
    for lab, n_units in ((st_lab, len(states)), (d20_lab, len(d20_keys)), (d11_lab, len(d11_keys))):
        L = per_cell(lab)
        land = np.nonzero(kind == 1)[0]
        own = majority(lab, land)
        have = set(own[own >= 0].tolist())
        for u in range(n_units):
            if u in have:
                continue
            cnt = (L == u).sum(1)
            if cnt.max() == 0:
                continue
            cand = np.argsort(-cnt)
            for i in cand[:6]:
                if cnt[i] == 0:
                    break
                if kind[i] != 1 or own[i] < 0 or (own == own[i]).sum() > 1:
                    kind[i] = 1; own[i] = u; forced += 1
                    break
    print("forced land hexes", forced)

    land = np.nonzero(kind == 1)[0]
    state_own = majority(st_lab, land)
    d20_own = majority(d20_lab, land)
    d11_own = majority(d11_lab, land)
    # force-assign owners for units that won a forced hex
    for lab, own, n in ((st_lab, state_own, len(states)), (d20_lab, d20_own, len(d20_keys)), (d11_lab, d11_own, len(d11_keys))):
        L = per_cell(lab)
        have = set(own[land].tolist())
        for u in range(n):
            if u in have:
                continue
            cnt = (L[land] == u).sum(1)
            if cnt.max() > 0:
                own[land[cnt.argmax()]] = u
    dis = per_cell(disp_lab)
    disputed = np.full(N, -1, np.int8)
    for i in land:
        v = dis[i][dis[i] >= 0]
        if v.size * 2 >= S:
            disputed[i] = 0 if disp_names[np.bincount(v).argmax()] == "Pakistan" else 1
    country = majority(c_lab, np.nonzero(kind == 2)[0])

    # area weights: samples of each district inside land hexes
    def weights(lab):
        L = per_cell(lab)
        w = {}
        for i in land:
            v = L[i][L[i] >= 0]
            if v.size:
                bc = np.bincount(v)
                nz = np.nonzero(bc)[0]
                w[int(i)] = [[int(d), int(bc[d])] for d in nz]
        return w

    w20, w11 = weights(d20_lab), weights(d11_lab)
    # unit area (km2) from all its samples, India-wide
    def unit_area(lab, n):
        bc = np.bincount(lab[lab >= 0], minlength=n)
        return (bc * HEX_AREA / S).round(1).tolist()

    lon, lat = unproject(cx, cy)
    out = {
        "cols": cols, "rows": rows, "x0": float(cx[0]), "y0": float(cy[0]), "hex_w": HEX_W, "hex_r": HEX_R,
        "samples_per_hex": S,
        "kind": kind.tolist(), "state": state_own.tolist(), "d20": d20_own.tolist(), "d11": d11_own.tolist(),
        "disputed": disputed.tolist(), "disputed_names": ["Pakistan", "China"], "country": country.tolist(),
        "india_frac": np.round(fi, 3).tolist(),
        "lon": np.round(lon, 4).tolist(), "lat": np.round(lat, 4).tolist(),
        "states": [s["id"] for s in states], "state_area_km2": unit_area(st_lab, len(states)),
        "d20_keys": d20_keys, "d20_area_km2": unit_area(d20_lab, len(d20_keys)),
        "d11_keys": d11_keys, "d11_area_km2": unit_area(d11_lab, len(d11_keys)),
        "countries": c_names, "w20": w20, "w11": w11,
    }
    write_json(f"{DATA}/grid/grid.json", out)
    print("land hexes", len(land), "disputed", int((disputed >= 0).sum()), "lake", int((kind == 3).sum()))
    print("states without hex", [states[u]["id"] for u in range(len(states)) if u not in set(state_own[land].tolist())])
    print("d20 without hex", [d20_keys[u] for u in range(len(d20_keys)) if u not in set(d20_own[land].tolist())])
    print("d11 without hex", [d11_keys[u] for u in range(len(d11_keys)) if u not in set(d11_own[land].tolist())])
    print("d20 without any sample", [d20_keys[u] for u in range(len(d20_keys)) if not any(any(d == u for d, _ in v) for v in w20.values())][:20])
    print("total India area km2 (samples)", round(in_india.sum() * HEX_AREA / S))


if __name__ == "__main__":
    main()
