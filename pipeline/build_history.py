"""Build data/normalized/history.json from raw/history/ (see history_config.py)."""
import json, re, sys
from pathlib import Path
from shapely.geometry import shape, box, mapping
from shapely.ops import unary_union
sys.path.insert(0, str(Path(__file__).parent))
import history_config as H

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw" / "history"
BBOX = box(60, 5, 100, 40)
TOL = 0.05
resolved = json.loads((RAW / "wikidata_resolved.json").read_text())
warn = []

def coord(ref):
    d = resolved.get(ref)
    if not d or not d["coords"]: return None
    m = re.match(r"Point\(([-\d.]+) ([-\d.]+)\)", d["coords"][0])
    return round(float(m.group(2)), 4), round(float(m.group(1)), 4)  # lat, lon

def entity(ref, name=None):
    d = resolved[ref]; c = coord(ref)
    if c is None: warn.append(f"no coordinates on Wikidata: {ref} ({d['qid']})"); return None
    lat, lon = c
    if not (5 <= lat <= 40 and 60 <= lon <= 100): warn.append(f"outside bbox: {ref} {lat},{lon}")
    return dict(name=name or H.NAMES.get(ref) or d["label"], lat=lat, lon=lon, qid=d["qid"], wikipedia=d["wikipedia"])

_cache = {}
def basemap(year):
    if year not in _cache: _cache[year] = json.loads((RAW / f"world_{year}.geojson").read_text())["features"]
    return _cache[year]

def rnd(c):
    if isinstance(c[0], (int, float)): return [round(c[0], 2), round(c[1], 2)]
    return [rnd(x) for x in c]

def extent(pol):
    if not pol["ext"]:
        return dict(source="none", year=None, geometry=None, confidence=None, note=pol["extnote"])
    year, names = pol["ext"]
    feats = [f for f in basemap(year) if f["properties"].get("NAME") in names and f["geometry"]]
    if not feats: warn.append(f"no basemap feature {names} in {year}"); return dict(source="none", year=None, geometry=None, confidence=None, note="Named feature not found in the basemap file.")
    g = unary_union([shape(f["geometry"]).buffer(0) for f in feats]).intersection(BBOX)
    g = g.simplify(TOL, preserve_topology=True)
    if g.is_empty: warn.append(f"empty after clip: {names} {year}"); return dict(source="none", year=None, geometry=None, confidence=None, note="Feature lies outside the bounding box.")
    geoms = [x for x in (g.geoms if hasattr(g, "geoms") else [g]) if x.geom_type == "Polygon" and x.area > 0.01]
    if not geoms: warn.append(f"only tiny parts: {names} {year}"); return dict(source="none", year=None, geometry=None, confidence=None, note="Only tiny fragments in the bounding box.")
    gm = mapping(unary_union(geoms)); gm = {"type": gm["type"], "coordinates": rnd(gm["coordinates"])}
    y = int(year[2:]) * -1 if year.startswith("bc") else int(year)
    prec = sorted({f["properties"].get("BORDERPRECISION") for f in feats})
    conf = "low" if y < 1000 else "medium"
    note = (f"{pol['extnote']} Source feature NAME {names}, BORDERPRECISION {prec} (source scale: 1 approximate, 3 legally defined). "
            f"Clipped to lon 60-100, lat 5-40 and simplified to {TOL} degrees.")
    return dict(source="historical-basemaps", year=y, geometry=gm, confidence=conf, note=note)

def build():
    eras, nplaces, npol, next_, nrt, ncap = [], 0, 0, 0, 0, 0
    for e in H.ERAS:
        pols = []
        for p in e["polities"]:
            caps = []
            for c in p["caps"]:
                en = entity(c["ref"], c["name"])
                if en: caps.append(dict(name=en["name"], lat=en["lat"], lon=en["lon"], start=c["start"], end=c["end"], qid=en["qid"]))
            ex = extent(p)
            pols.append(dict(id=p["id"], name=p["name"], start=p["start"], end=p["end"], peak_year=p["peak"], qid=p["qid"], capitals=caps, extent=ex))
            ncap += len(caps); npol += 1; next_ += ex["geometry"] is not None
        places, seen = [], set()
        for pl in e["places"]:
            en = entity(pl["ref"], pl["name"])
            if not en or (en["qid"], pl["type"]) in seen: continue
            seen.add((en["qid"], pl["type"]))
            places.append(dict(name=en["name"], lat=en["lat"], lon=en["lon"], type=pl["type"], start=pl["start"], end=pl["end"],
                               qid=en["qid"], wikipedia=en["wikipedia"], note=pl["note"]))
        nplaces += len(places)
        routes = []
        for r in H.ROUTES_BY_ERA.get(e["id"], []):
            cs = [coord(w) for w in r["waypoints"]]
            if None in cs: warn.append(f"route {r['name']} has waypoint without coordinates"); continue
            routes.append(dict(name=r["name"], type=r["type"], coords=[[lon, lat] for lat, lon in cs], source=r["source"],
                               confidence=r["confidence"], note=r["note"], waypoints=[entity(w)["name"] for w in r["waypoints"]]))
        nrt += len(routes)
        out = dict(id=e["id"], name=e["name"], start=e["start"], end=e["end"], summary=e["summary"], sources=e["sources"])
        if e.get("key_dates"): out["key_dates"] = e["key_dates"]
        out.update(polities=pols, places=places, routes=routes)
        eras.append(out)
    meta = dict(
        id="history", name="India Civ historical timeline layer (eras, polities, places, routes)",
        source_org="Wikidata (CC0); aourednik/historical-basemaps (GPL-3.0); Wikipedia and Britannica as dating references",
        url="https://query.wikidata.org/sparql",
        landing_url="https://github.com/aourednik/historical-basemaps",
        published=None, reference_year="-3300 to 1956", resolution="point",
        license="Wikidata: CC0. Historical-basemaps geometry: GPL-3.0 (derived extents keep GPL-3.0). Era summaries: written by this project; sources cited per era.",
        update_frequency="one-off", kind="historical",
        limitations=("Historical data. Dates are rounded and negative years mean BCE (1 BCE = -1, no year 0). Extents come from a world-wide basemap with coarse, "
                     "generalised borders at fixed years; they are not surveyed. Extents before 1000 CE have confidence low. Polities without a matching "
                     "basemap polygon have geometry null. Routes are straight lines between documented waypoint cities, not surveyed paths. "
                     "Do not merge this file with modern statistics."),
        method=("Places and capitals are chosen in pipeline/history_config.py and resolved to Wikidata QIDs from English Wikipedia titles (redirects followed) "
                "to get coordinates. Dates are curated from the cited articles. Extents: basemap features matched by NAME, unioned, clipped to lon 60-100 and lat 5-40, "
                "simplified at 0.05 degrees, rounded to 2 decimals, parts under 0.01 square degrees dropped. Routes: polylines through waypoint cities."),
        accessed="2026-11-26")
    fields = {"start": {"name": "Start year", "unit": "year (CE; negative = BCE)", "type": "value", "description": "Approximate start year. null if unknown.", "higher_is": "neutral"},
              "end": {"name": "End year", "unit": "year (CE; negative = BCE)", "type": "value", "description": "Approximate end year. null if unknown.", "higher_is": "neutral"}}
    return dict(meta=meta, fields=fields, eras=eras), (len(eras), npol, ncap, nplaces, next_, nrt)

doc, counts = build()
(ROOT / "data" / "normalized").mkdir(parents=True, exist_ok=True)
out = ROOT / "data" / "normalized" / "history.json"
out.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")))
print("eras, polities, capitals, places, extents, routes =", counts, "size KB", out.stat().st_size // 1024)
for e in doc["eras"]: print(e["id"], len(e["polities"]), len(e["places"]), sum(p["extent"]["geometry"] is not None for p in e["polities"]))
for w in warn: print("WARN", w)
lab = resolved["_polity_labels"]
for e in H.ERAS:
    for p in e["polities"]:
        if p["qid"]: print("QID", p["qid"], lab.get(p["qid"]), "<-", p["name"])
