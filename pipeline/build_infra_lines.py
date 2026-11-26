"""Build railways and highways as simplified polylines.
Railways: Natural Earth 10m railroads clipped to India (OSM Overpass was too slow / overloaded).
Highways: OSM National Highway ways (motorway/trunk with ref NH*) if all tiles exist, else Natural Earth 10m roads."""
import glob, json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from infra_common import *
import shapefile
from shapely.geometry import shape, LineString, MultiLineString
from shapely.ops import unary_union, linemerge

d = json.load(open(os.path.join(ROOT, "raw/ne/ne_10m_admin_0_countries_ind.geojson")))
INDIA = shape([f for f in d["features"] if f["properties"].get("NAME") == "India"][0]["geometry"]).buffer(0.05)

def km(line):
    t = 0
    c = list(line.coords)
    for (x1, y1), (x2, y2) in zip(c, c[1:]):
        p = math.pi / 180
        a = math.sin((y2 - y1) * p / 2) ** 2 + math.cos(y1 * p) * math.cos(y2 * p) * math.sin((x2 - x1) * p / 2) ** 2
        t += 12742 * math.asin(math.sqrt(a))
    return t

def lines_of(g):
    if g.is_empty: return []
    if g.geom_type == "LineString": return [g]
    if g.geom_type in ("MultiLineString", "GeometryCollection"):
        return [x for p in g.geoms for x in lines_of(p)]
    return []

def merge_group(geoms, tol, minkm):
    clipped = unary_union([g.intersection(INDIA) for g in geoms if not g.is_empty])
    m = linemerge(lines_of(clipped)) if lines_of(clipped) else None
    out = []
    for ln in (lines_of(m) if m is not None else []):
        s = ln.simplify(tol, preserve_topology=False)
        if s.is_empty or km(s) < minkm: continue
        out.append(s)
    return out

def emit_rows(prefix, group, lines, rows, extra):
    for i, s in enumerate(sorted(lines, key=lambda x: -km(x)), 1):
        cs = [[round(x, 3), round(y, 3)] for x, y in s.coords]
        dd = [cs[0]] + [c for a, c in zip(cs, cs[1:]) if c != a]
        if len(dd) < 2: continue
        mid = s.interpolate(0.5, normalized=True)
        rows.append(dict({"key": f"{prefix}_{group}_{i}", "category": group, "state": state_of(mid.y, mid.x), "lat": round(mid.y, 3), "lon": round(mid.x, 3),
                          "length_km": round(km(s)), "coords": dd}, **extra(group)))

# ---------------- railways (Natural Earth)
sf = shapefile.Reader(os.path.join(RAW, "ne_rail", "ne_10m_railroads"))
grp = {}
for sr in sf.iterShapeRecords():
    b = sr.shape.bbox
    if not (67 < b[0] and b[2] < 98 and 6 < b[1] and b[3] < 37.5): continue
    g = shape(sr.shape.__geo_interface__)
    if not g.intersects(INDIA): continue
    r = sr.record.as_dict()
    key = "electrified" if r["electric"] == 1 else "non_electrified_or_unknown"
    grp.setdefault(key, []).append(g)
rows = []
for k, gs in grp.items():
    emit_rows("rail", k, merge_group(gs, 0.01, 3), rows, lambda g: {"name": None, "source_ids": {"natural_earth": "ne_10m_railroads"}})
write("railways", {
    "name": "Railway main lines of India (Natural Earth 10m railroads, simplified)",
    "source_org": "Natural Earth", "url": "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_railroads.zip",
    "landing_url": "https://www.naturalearthdata.com/downloads/10m-cultural-vectors/railroads/",
    "published": "2022", "reference_year": "2022", "resolution": "line", "license": "Public domain",
    "update_frequency": "irregular", "kind": "curated",
    "limitations": "Natural Earth shows the main trunk network only at 1:10m scale, with no line names and no branch lines. The electrification flag is as given by Natural Earth and may be out of date. Lines are simplified (0.01 degrees) and merged, so a row is a chain of segments, not an official route. OSM via Overpass was tried and failed (overload).",
    "method": "Select Natural Earth railroads that touch India (polygon of India from Natural Earth admin-0, 0.05 degree buffer), clip to that polygon, merge touching segments (shapely linemerge) by electrified / not, simplify with tolerance 0.01 degrees, drop chains shorter than 3 km, round coordinates to 3 decimals. State is the state at the line mid-point (lines cross many states). No station list: no reliable open list with coordinates was found."},
    {"name": STD["name"], "category": STD["category"], "lat": F("Mid-point latitude", "degrees", "value", "Latitude of the line mid-point"),
     "lon": F("Mid-point longitude", "degrees", "value", "Longitude of the line mid-point"),
     "length_km": F("Length", "km", "value", "Great-circle length of the simplified chain"),
     "coords": F("Coordinates", None, "text", "[[lon,lat],...] polyline, 3 decimals"), "source_ids": STD["source_ids"]}, rows)

# ---------------- highways
need = [(lat, lon) for lat in range(6, 37, 5) for lon in range(68, 98, 5)]
SKIP = {(6,68),(6,73),(6,83),(6,88),(6,93),(11,68),(11,93),(16,68),(16,93),(21,93),(26,68),(31,68),(31,93),(36,68),(36,73)}
tiles = {(la, lo): os.path.join(RAW, "osm", f"nh_{la}_{lo}.json") for la, lo in need if (la, lo) not in SKIP}
osm_ok = all(os.path.exists(p) for p in tiles.values()) and os.environ.get("USE_OSM") != "0"
rows = []
if osm_ok:
    byref = {}
    for p in tiles.values():
        for el in json.load(open(p)).get("elements", []):
            if el.get("type") != "way" or "geometry" not in el: continue
            t = el.get("tags", {}); refs = [x.strip() for x in t.get("ref", "").replace(",", ";").split(";") if x.strip().startswith("NH")]
            if not refs: continue
            ln = LineString([(g["lon"], g["lat"]) for g in el["geometry"]])
            for r in refs: byref.setdefault((r.replace(" ", ""), t.get("highway")), []).append(ln)
    for (ref, hw), gs in sorted(byref.items()):
        for i, s in enumerate(sorted(merge_group(gs, 0.01, 5), key=lambda x: -km(x)), 1):
            cs = [[round(x, 3), round(y, 3)] for x, y in s.coords]; dd = [cs[0]] + [c for a, c in zip(cs, cs[1:]) if c != a]
            if len(dd) < 2: continue
            mid = s.interpolate(0.5, normalized=True)
            rows.append({"key": f"{ref}_{i}", "name": ref, "category": "expressway" if hw == "motorway" else "national_highway", "expressway": hw == "motorway",
                         "state": state_of(mid.y, mid.x), "lat": round(mid.y, 3), "lon": round(mid.x, 3), "length_km": round(km(s)), "coords": dd,
                         "source_ids": {"osm_ref": ref}})
    src = ("OpenStreetMap contributors", "https://overpass-api.de/api/interpreter", "ODbL 1.0", "OSM ways with highway=motorway|trunk and ref starting NH. Grouped by ref and highway type.")
else:
    sf = shapefile.Reader(os.path.join(RAW, "ne_road", "ne_10m_roads"))
    grp = {}
    for sr in sf.iterShapeRecords():
        b = sr.shape.bbox
        if not (67 < b[0] and b[2] < 98 and 6 < b[1] and b[3] < 37.5): continue
        g = shape(sr.shape.__geo_interface__)
        if not g.intersects(INDIA): continue
        r = sr.record.as_dict()
        if r["type"] == "Major Highway" or r["expressway"]: k = "expressway"
        elif r["type"] == "Road" and r["scalerank"] <= 4: k = "trunk_road"
        else: continue
        grp.setdefault(k, []).append(g)
    for k, gs in grp.items():
        emit_rows("road", k, merge_group(gs, 0.01, 5), rows, lambda g: {"name": None, "expressway": g == "expressway", "source_ids": {"natural_earth": "ne_10m_roads"}})
    src = ("Natural Earth", "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_roads.zip", "Public domain", "Natural Earth roads: type Major Highway (carries the Natural Earth expressway flag = 1) becomes category expressway; type Road with scalerank 3-4 becomes trunk_road (the main national highway corridors). Other classes (Unknown, scalerank 5 and higher) are dropped.")
write("highways", {
    "name": "Highways of India (simplified polylines)", "source_org": src[0], "url": src[1],
    "landing_url": "https://www.naturalearthdata.com/downloads/10m-cultural-vectors/roads/" if not osm_ok else "https://www.openstreetmap.org/copyright",
    "published": "2026-11", "reference_year": "2026", "resolution": "line", "license": src[2], "update_frequency": "irregular", "kind": "curated",
    "limitations": ("Complete OSM National Highway coverage. " if osm_ok else "Natural Earth has no road numbers for India and shows only the main trunk corridors; the expressway class is Natural Earth's own flag (Major Highway) and is not verified against NHAI; National Highway numbers are not available in this file. OSM via Overpass was tried and was too slow or overloaded to finish. ") + "Lines are simplified (0.01 degrees) and merged. A row is a chain of segments, not an official NH route.",
    "method": src[3] + " Clip to India, merge touching segments (shapely linemerge), simplify with tolerance 0.01 degrees, drop chains shorter than 5 km, round to 3 decimals."},
    {"name": STD["name"], "category": STD["category"], "expressway": F("Expressway", None, "text", "True if flagged as expressway / motorway"),
     "lat": F("Mid-point latitude", "degrees", "value", "Latitude of the line mid-point"), "lon": F("Mid-point longitude", "degrees", "value", "Longitude of the line mid-point"),
     "length_km": F("Length", "km", "value", "Great-circle length of the simplified chain"),
     "coords": F("Coordinates", None, "text", "[[lon,lat],...] polyline, 3 decimals"), "source_ids": STD["source_ids"]}, rows)
