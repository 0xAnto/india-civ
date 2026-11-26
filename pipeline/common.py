"""Shared constants and helpers: projection, hex grid, paths."""
import json, math, os, csv
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "raw")
DATA = os.path.join(ROOT, "data")
SITE_DATA = os.path.join(ROOT, "site", "data")

# Lambert conformal conic on a sphere (km).
EARTH_R = 6371.0088
LON0, LAT0, SP1, SP2 = 82.0, 24.0, 12.472944, 35.172806
_p1, _p2, _p0 = (math.radians(v) for v in (SP1, SP2, LAT0))
_N = math.log(math.cos(_p1) / math.cos(_p2)) / math.log(math.tan(math.pi / 4 + _p2 / 2) / math.tan(math.pi / 4 + _p1 / 2))
_F = math.cos(_p1) * math.tan(math.pi / 4 + _p1 / 2) ** _N / _N
_RHO0 = EARTH_R * _F / math.tan(math.pi / 4 + _p0 / 2) ** _N


def project(lon, lat):
    """lon/lat degrees -> (x east km, y SOUTH km). Works on numpy arrays."""
    lon = np.asarray(lon, float); lat = np.asarray(lat, float)
    rho = EARTH_R * _F / np.tan(np.pi / 4 + np.radians(lat) / 2) ** _N
    th = _N * np.radians(lon - LON0)
    return rho * np.sin(th), -( _RHO0 - rho * np.cos(th))


def unproject(x, y):
    x = np.asarray(x, float); yn = -np.asarray(y, float)
    dy = _RHO0 - yn
    rho = np.sign(_N) * np.hypot(x, dy)
    th = np.arctan2(x, dy)
    lat = np.degrees(2 * np.arctan((EARTH_R * _F / rho) ** (1 / _N)) - np.pi / 2)
    return LON0 + np.degrees(th / _N), lat


# Hex grid: pointy-top, odd rows shifted right by half a cell.
HEX_W = 20.0                      # flat-to-flat km
HEX_R = HEX_W / math.sqrt(3)      # circumradius km
HEX_AREA = 1.5 * math.sqrt(3) * HEX_R ** 2
BBOX = (66.0, 5.6, 99.6, 37.6)    # lon/lat frame shown on the map


def grid_frame():
    xs, ys = project([BBOX[0], BBOX[2], BBOX[0], BBOX[2], 82, 82], [BBOX[1], BBOX[1], BBOX[3], BBOX[3], BBOX[1], BBOX[3]])
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    cols = int(math.ceil((x1 - x0) / HEX_W)) + 1
    rows = int(math.ceil((y1 - y0) / (1.5 * HEX_R))) + 1
    return x0, y0, cols, rows


def cell_centers():
    x0, y0, cols, rows = grid_frame()
    r, c = np.divmod(np.arange(cols * rows), cols)
    x = x0 + HEX_W * (c + 0.5 * (r & 1))
    y = y0 + 1.5 * HEX_R * r
    return x, y, cols, rows


def sample_offsets(step=0.2):
    """Evenly spaced points (staggered rows) strictly inside one pointy-top hex, about 64 of them."""
    s = step * HEX_R
    pts = []
    for j in range(-12, 13):
        y = j * s * math.sqrt(3) / 2
        for i in range(-12, 13):
            x = (i + 0.5 * (j & 1)) * s
            if abs(x) < math.sqrt(3) / 2 * HEX_R and abs(y) < HEX_R - abs(x) / math.sqrt(3):
                pts.append((x, y))
    return np.array(pts)


def neighbors(i, cols, rows):
    r, c = divmod(i, cols)
    d = [(-1, 0), (1, 0), (0, -1), (1, -1), (0, 1), (1, 1)] if r & 1 else [(-1, 0), (1, 0), (-1, -1), (0, -1), (-1, 1), (0, 1)]
    for dc, dr in d:
        cc, rr = c + dc, r + dr
        if 0 <= cc < cols and 0 <= rr < rows:
            yield rr * cols + cc


def load_states():
    with open(os.path.join(DATA, "ref", "states.csv")) as f:
        rows = list(csv.DictReader(f))
    alias = {}
    for s in rows:
        for n in [s["name"], s["id"]] + [a for a in s["aliases"].split("|") if a]:
            alias[n.lower()] = s["id"]
    return rows, alias


def read_json(p):
    with open(p) as f:
        return json.load(f)


def write_json(p, obj, compact=True):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(obj, f, separators=(",", ":") if compact else None, indent=None if compact else 1, ensure_ascii=False)


if __name__ == "__main__":
    lon, lat = unproject(*project([72.88, 88.36], [19.07, 22.57]))
    assert np.allclose(lon, [72.88, 88.36]) and np.allclose(lat, [19.07, 22.57]), (lon, lat)
    o = sample_offsets()
    assert 50 < len(o) < 80 and np.abs(o).max() < HEX_R, o.max()
    x0, y0, cols, rows = grid_frame()
    print("grid", cols, rows, cols * rows, "hex area km2", round(HEX_AREA, 1))
