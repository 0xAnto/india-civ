"""Build unesco_whs, protected_areas, asi_monuments, defence_public."""
import csv, glob, json, os, re, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from infra_common import *
csv.field_size_limit(10**9)
def v(b, k): return b.get(k, {}).get("value")
def wkt(c):
    m = re.match(r"Point\(([-\d.]+) ([-\d.]+)\)", c or "")
    return (float(m.group(2)), float(m.group(1))) if m else (None, None)
def qid(b): return v(b, "x").rsplit("/", 1)[1]

# ---------------- unesco_whs
qmap = {}
for b in json.load(open(os.path.join(RAW, "wd_whs.json")))["results"]["bindings"]:
    if v(b, "id"): qmap.setdefault(v(b, "id"), qid(b))
rows = []
for r in csv.DictReader(open(os.path.join(RAW, "whs", "whc001.csv"), encoding="utf-8-sig"), delimiter=";"):
    if "India" not in r["states_names"].split(","): continue
    pts = [(c[1], c[0]) for c in json.loads(r["coordinates"])["coordinates"]]
    pts = [p for p in pts if in_india(*p)]          # drop non-India components (Le Corbusier)
    uniq = list(dict.fromkeys(pts))
    lat, lon = uniq[0]
    rows.append({"key": r["id_no"], "name": r["name_en"], "lat": round(lat, 5), "lon": round(lon, 5),
                 "category": r["category"].lower(), "state": state_of(lat, lon),
                 "year_inscribed": int(r["date_inscribed"]), "area_ha": float(r["area_hectares"]) if float(r["area_hectares"] or 0) > 0 else None,
                 "criteria": r["criteria_txt"] or None, "in_danger": r["danger"] == "true",
                 "transboundary": r["transboundary"] == "1" or r["transboundary"].lower() == "true",
                 "components": len(uniq), "component_coords": [[round(x[1], 4), round(x[0], 4)] for x in uniq] if len(uniq) > 1 else None,
                 "list": "inscribed", "source_ids": {"unesco": r["id_no"], "wikidata": qmap.get(r["id_no"])}})
rows.sort(key=lambda x: int(x["key"]))
write("unesco_whs", {
    "name": "UNESCO World Heritage Sites in India (inscribed)",
    "source_org": "UNESCO World Heritage Centre",
    "url": "https://data.unesco.org/api/explore/v2.1/catalog/datasets/whc001/exports/csv?where=iso_codes%20like%20%22in%22",
    "landing_url": "https://whc.unesco.org/en/statesparties/in",
    "published": "2026", "reference_year": "2026", "resolution": "point", "license": "UNESCO open data (CC BY-SA 3.0 IGO)",
    "update_frequency": "annual", "kind": "official",
    "limitations": "One point per site: the first component coordinate in India. Sites with many components (Western Ghats, Maratha Military Landscapes, Hill Forts of Rajasthan, Mountain Railways) list all coordinates in component_coords. area_ha is null when UNESCO gives 0 (site area not stated). The tentative list is not included (data not reachable, see data/meta/unesco_whs.md). Le Corbusier is a transboundary site: only the Chandigarh component is used.",
    "method": "Rows of the UNESCO whc001 dataset where states_names contains India. Category from the UNESCO field (cultural, natural, mixed). Coordinates outside India are dropped. State from point-in-polygon."},
    sub(year_inscribed=F("Year inscribed", "year", "value", "Year of inscription on the World Heritage List"),
        area_ha=F("Area", "hectares", "value", "Property area; null if not stated"),
        criteria=F("Criteria", None, "text", "Selection criteria, e.g. (i)(iii)"),
        in_danger=F("On danger list", None, "text", "True if on the List of World Heritage in Danger"),
        transboundary=F("Transboundary", None, "text", "True if shared with other countries"),
        components=F("Components in India", "count", "count", "Number of distinct coordinates in India"),
        component_coords=F("Component coordinates", None, "text", "[[lon,lat],...] for multi-part sites"),
        list=F("List", None, "text", "inscribed (tentative list not included)")), rows)

# ---------------- protected_areas
def clean_wikitext(s):
    s = re.sub(r"<ref[^>/]*/>", "", s); s = re.sub(r"<ref.*?</ref>", "", s, flags=re.S)
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    prev = None
    while prev != s:  # remove {{efn|..}} / other templates except coord, innermost first
        prev = s; s = re.sub(r"\{\{(?!coord)[^{}]*\}\}", "", s, flags=re.I)
    return s
w = json.load(open(os.path.join(RAW, "wiki", "tiger.json")))["parse"]["wikitext"]
tb = clean_wikitext(w[w.index("{|"):w.index("|}")])
tiger = []
for blk in tb.split("\n|-")[3:]:
    ln = [x for x in blk.strip().split("\n") if x.startswith("|") and not x.startswith("|+")]
    cells = [c.strip() for c in " ".join(ln).lstrip("|").split("||")]
    if len(cells) < 9: continue
    nm = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", cells[0]).strip()
    st = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", cells[3]).strip()
    m = re.search(r"\{\{coord\|([\d.]+)\|(?:([\d.]+)\|)?(?:([\d.]+)\|)?N\|([\d.]+)\|(?:([\d.]+)\|)?(?:([\d.]+)\|)?E", cells[4], re.I)
    if not m: print("no coord", nm); continue
    dms = lambda a: float(a[0]) + float(a[1] or 0) / 60 + float(a[2] or 0) / 3600
    lat = dms(m.group(1, 2, 3)); lon = dms(m.group(4, 5, 6))
    inc = re.match(r"(\d{4})", cells[1])
    tot = re.sub(r"[^\d.]", "", cells[8]); core = re.sub(r"[^\d.]", "", cells[6])
    tiger.append({"name": nm + " Tiger Reserve", "lat": lat, "lon": lon, "inc": int(inc.group(1)) if inc else None,
                  "area": float(tot) if tot else None, "core": float(core) if core else None, "stname": st})
print("tiger reserves parsed:", len(tiger))
out = []
for t in tiger:
    out.append({"key": "tr_" + re.sub(r"[^a-z0-9]+", "_", t["name"].lower()).strip("_"), "name": t["name"], "lat": round(t["lat"], 5), "lon": round(t["lon"], 5),
                "category": "tiger_reserve", "state": state_id(t["stname"]) or state_of(t["lat"], t["lon"]),
                "area_km2": t["area"], "core_area_km2": t["core"], "year_established": t["inc"], "source_ids": {"wikipedia": "Tiger_reserves_of_India"}})
nps = {}
for b in json.load(open(os.path.join(RAW, "wd_np.json")))["results"]["bindings"]:
    if v(b, "instLabel") != "national park" or "Tiger Reserve" in v(b, "xLabel"): continue
    lat, lon = float(v(b, "lat")), float(v(b, "lon"))
    if not in_india(lat, lon): continue
    q = qid(b); e = nps.setdefault(q, {"name": v(b, "xLabel"), "lat": lat, "lon": lon, "area": None, "inc": None})
    if v(b, "area") and not e["area"]: e["area"] = float(v(b, "area"))
    if v(b, "inc") and not e["inc"]: e["inc"] = int(v(b, "inc")[:4])
for q, e in nps.items():
    out.append({"key": q, "name": e["name"], "lat": round(e["lat"], 5), "lon": round(e["lon"], 5), "category": "national_park",
                "state": state_of(e["lat"], e["lon"]), "area_km2": e["area"], "core_area_km2": None, "year_established": e["inc"],
                "source_ids": {"wikidata": q}})
write("protected_areas", {
    "name": "National parks and tiger reserves of India",
    "source_org": "Wikipedia (table Tiger reserves of India, from NTCA / MoEFCC) for tiger reserves; Wikidata for national parks",
    "url": "https://en.wikipedia.org/w/api.php?action=parse&page=Tiger_reserves_of_India&prop=wikitext ; https://query.wikidata.org/sparql",
    "landing_url": "https://ntca.gov.in/tiger-reserves/ ; https://www.wikidata.org/wiki/Q46169",
    "published": "2026-11", "reference_year": "2026", "resolution": "point", "license": "Wikipedia CC BY-SA 4.0; Wikidata CC0",
    "update_frequency": "irregular", "kind": "curated",
    "limitations": "WDPA needs a login so it was not used. National parks come from Wikidata and may be incomplete or have missing area and year. Tiger reserve area_km2 is the total (core + buffer) in the Wikipedia table; year_established is the year of inclusion under Project Tiger. Many tiger reserves contain a national park, so the two categories overlap in space. Points are the centre, not the boundary.",
    "method": "Tiger reserves: parse the wikitext table (name, inclusion year, state, coordinates, core and total area). National parks: Wikidata items of class national park (Q46169) in India with coordinates; area from P2046 (km2, as stored) and year from P571. State from the table (tiger) or point-in-polygon (national parks)."},
    sub(area_km2=F("Area", "km2", "value", "Total area (tiger reserve: core + buffer)"),
        core_area_km2=F("Core area", "km2", "value", "Core / critical tiger habitat area (tiger reserves only)"),
        year_established=F("Year established", "year", "value", "Tiger reserve: year of inclusion under Project Tiger. National park: Wikidata inception.")), out)

# ---------------- asi_monuments
ents = {}
for b in json.load(open(os.path.join(RAW, "wd_asi.json")))["results"]["bindings"]:
    lat, lon = float(v(b, "lat")), float(v(b, "lon"))
    if not in_india(lat, lon) or re.fullmatch(r"Q\d+", v(b, "xLabel") or ""): continue
    ents.setdefault(qid(b), {"name": v(b, "xLabel"), "lat": lat, "lon": lon, "asi": v(b, "asi")})
rows = [{"key": q, "name": e["name"], "lat": round(e["lat"], 5), "lon": round(e["lon"], 5), "category": "asi_monument",
         "state": state_of(e["lat"], e["lon"]), "asi_id": e["asi"], "source_ids": {"wikidata": q, "asi_monument_id": e["asi"]}} for q, e in ents.items()]
cnt = collections.Counter(r["state"] for r in rows)
write("asi_monuments", {
    "name": "ASI centrally protected monuments with coordinates (Wikidata P1371)",
    "source_org": "Wikidata (CC0) built from the Archaeological Survey of India monument lists",
    "url": "https://query.wikidata.org/sparql", "landing_url": "https://www.wikidata.org/wiki/Property:P1371",
    "published": "2026-11", "reference_year": "2026", "resolution": "point", "license": "CC0",
    "update_frequency": "irregular", "kind": "curated",
    "limitations": "Only monuments that have a Wikidata item with an ASI monument ID and coordinates. ASI protects about 3,700 monuments, so the count here is a partial list and is not the official count. Counts per state are in data/meta/asi_monuments.md. Another dataset (asi_state) may give official state totals.",
    "method": "SPARQL: all items with P1371 and P625 in India. Items whose label is a bare QID are dropped. State from point-in-polygon."},
    sub(asi_id=F("ASI monument id", None, "text", "Value of Wikidata property P1371")), rows)
json.dump(cnt, open("/tmp/asi_counts.json", "w"))

# ---------------- defence_public
KEEP = {"Q357095": ("Hindustan Aeronautics Limited (HQ)", "defence_psu"), "Q3630918": ("Bharat Electronics Limited (HQ)", "defence_psu"),
        "Q2956390": ("Mazagon Dock Shipbuilders", "shipyard"), "Q5522292": ("Garden Reach Shipbuilders & Engineers", "shipyard"),
        "Q5575109": ("Goa Shipyard Limited", "shipyard"), "Q5139314": ("Cochin Shipyard", "shipyard"), "Q3523533": ("Hindustan Shipyard", "shipyard"),
        "Q3530250": ("Bharat Dynamics Limited", "defence_psu"), "Q6875625": ("Mishra Dhatu Nigam", "defence_psu"), "Q2920445": ("BEML Limited (HQ)", "defence_psu"),
        "Q22101737": ("Naval Dockyard, Visakhapatnam", "naval_dockyard"), "Q356379": ("Indian Coast Guard (headquarters)", "coast_guard")}
pts = {}
for f in glob.glob(os.path.join(RAW, "wd_named_orgs.json")) + glob.glob(os.path.join(RAW, "wd_def_*.json")):
    for b in json.load(open(f))["results"]["bindings"]:
        q = qid(b)
        if q in KEEP and q not in pts:
            lat, lon = wkt(v(b, "c"))
            if lat is not None and in_india(lat, lon): pts[q] = (lat, lon)
rows = [{"key": q, "name": KEEP[q][0], "lat": round(p[0], 5), "lon": round(p[1], 5), "category": KEEP[q][1], "state": state_of(*p),
         "source_ids": {"wikidata": q}} for q, p in pts.items()]
print("defence missing coords:", [KEEP[q][0] for q in KEEP if q not in pts])
write("defence_public", {
    "name": "Public defence industry and maritime infrastructure (headquarters and shipyards)",
    "source_org": "Wikidata (CC0)", "url": "https://query.wikidata.org/sparql", "landing_url": "https://www.wikidata.org/",
    "published": "2026-11", "reference_year": "2026", "resolution": "point", "license": "CC0", "update_frequency": "irregular", "kind": "curated",
    "limitations": "Only publicly documented, non-sensitive sites: defence public-sector companies, shipyards, one naval dockyard and the Coast Guard headquarters. No military bases, no operational data. HAL, BEL and BEML points are the headquarters coordinate in Wikidata (a city-level point in Bengaluru), not plant sites. Coast Guard regional headquarters have no coordinates in Wikidata and are not included.",
    "method": "Hand-picked list of Wikidata QIDs. Coordinates from Wikidata P625 (or the headquarters P159)."},
    dict(STD), rows)
