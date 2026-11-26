"""Shared helpers for the infrastructure topic build scripts."""
import json, os, csv
import shapefile
from shapely.geometry import shape, Point
from shapely.strtree import STRtree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "raw", "infra")
OUT = os.path.join(ROOT, "data", "normalized")
META = os.path.join(ROOT, "data", "meta")
os.makedirs(OUT, exist_ok=True); os.makedirs(META, exist_ok=True)
ACCESSED = "2026-11-26"

_ids = {}
for r in csv.DictReader(open(os.path.join(ROOT, "data/ref/states.csv"))):
    _ids[r["name"].lower()] = r["id"]
    for a in filter(None, r["aliases"].split("|")):
        _ids[a.lower()] = r["id"]
_ids["delhi"] = "DL"; _ids["new delhi"] = "DL"; _ids["nct of delhi"] = "DL"
_ids["orissa"] = "OR"; _ids["uttaranchal"] = "UT"; _ids["andaman & nicobar islands"] = "AN"
_ids["dadra and nagar haveli"] = "DH"; _ids["daman and diu"] = "DH"; _ids["jammu & kashmir"] = "JK"
_ids["andaman and nicobar"] = "AN"; _ids["pondicherry"] = "PY"; _ids["telangana"] = "TG"

def state_id(name):
    return _ids.get(name.lower().strip()) if name else None

_sf = shapefile.Reader(os.path.join(ROOT, "raw/boundaries/states_Admin2"))
_geoms = [shape(s.__geo_interface__) for s in _sf.shapes()]
_names = [r[0] for r in _sf.records()]
_tree = STRtree(_geoms)

def state_of(lat, lon, tol=0.25):
    """State id from the point: inside polygon, else nearest polygon within tol degrees (coast)."""
    if lat is None or lon is None:
        return None
    p = Point(lon, lat)
    for i in _tree.query(p):
        if _geoms[i].contains(p):
            return state_id(_names[i])
    j = _tree.nearest(p)
    if _geoms[j].distance(p) <= tol:
        return state_id(_names[j])
    return None

def in_india(lat, lon):
    return 6.0 <= lat <= 37.5 and 67.5 <= lon <= 98

def write(dsid, meta, fields, rows):
    meta = dict(meta, id=dsid, accessed=ACCESSED)
    json.dump({"meta": meta, "fields": fields, "rows": rows},
              open(os.path.join(OUT, dsid + ".json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(dsid, len(rows), "rows;", os.path.getsize(os.path.join(OUT, dsid + ".json")) // 1024, "KB;",
          "state null:", sum(1 for r in rows if r.get("state") is None))

def F(name, unit, typ, desc, higher="neutral"):
    return {"name": name, "unit": unit, "type": typ, "description": desc, "higher_is": higher}

STD = {
    "name": F("Name", None, "text", "Feature name"),
    "category": F("Category", None, "text", "Category of the feature"),
    "lat": F("Latitude", "degrees", "value", "WGS84 latitude"),
    "lon": F("Longitude", "degrees", "value", "WGS84 longitude"),
    "source_ids": F("Source ids", None, "text", "Identifiers in the source datasets (e.g. Wikidata QID)"),
}
def sub(**extra):
    d = dict(STD); d.update(extra); return d
