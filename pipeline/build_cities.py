"""Build data/normalized/cities.json from raw/cities (Wikipedia tables citing Census 2011 + Wikidata)."""
import csv, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data/normalized"; OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "pipeline"))

states = list(csv.DictReader(open(ROOT / "data/ref/states.csv")))
byname = {}
for s in states:
    for n in [s["name"]] + [a for a in s["aliases"].split("|") if a]:
        byname[n.lower()] = s["id"]
byname.update({"national capital territory of delhi": "DL", "jammu and kashmir (union territory)": "JK",
               "puducherry (union territory)": "PY", "delhi": "DL"})
d11 = {int(r["censuscode"]): r for r in csv.DictReader(open(ROOT / "data/ref/districts2011.csv"))}
d20 = list(csv.DictReader(open(ROOT / "data/ref/districts2020.csv")))
census = {int(r["key"]): r for r in json.load(open(OUT / "census2011_district.json"))["rows"]}
wd = json.load(open(ROOT / "raw/cities/wikidata.json"))
pages, alias, wdc = wd["pages"], wd["pages"].pop("__alias__"), wd["wikidata_coords"]

def canon(t):
    for _ in range(3): t = alias.get(t, t)
    return t
LINK = re.compile(r"\[\[([^\]|#]+)(?:\|([^\]]*))?\]\]")
num = lambda s: int(re.sub(r"[^\d]", "", s)) if re.search(r"\d", s) else None

# --- Wikipedia: million-plus urban agglomerations (Census 2011)
w = json.load(open(ROOT / "raw/cities/ua.json"))["parse"]["wikitext"]["*"]
w = w[w.find('{| class="wikitable sortable sticky'):]; w = w[:w.find("\n|}")]
ua = {}
for row in w.split("\n|-\n")[1:]:
    c = [x[1:] for x in row.strip().split("\n") if x.startswith("|")]
    if len(c) < 5: continue
    m = LINK.search(c[0]); title, label = m.group(1).strip(), (m.group(2) or m.group(1)).strip()
    st = LINK.search(c[2]).group(1)
    pop = num(re.search(r"Formatnum:([\d.]+)", c[4]).group(1).split(".")[0])
    ua[canon(title)] = dict(name=label, level=c[1].strip(), state=byname[st.lower()], pop=pop)
# --- Wikipedia: cities above 100,000 (Census 2011, municipal city level)
cw = json.load(open(ROOT / "raw/cities/cities.json"))["parse"]["wikitext"]["*"]
cw = cw[cw.find("== List of cities above 100,000"):]; cw = cw[:cw.find("\n|}")]
city = {}
for row in cw.split("\n|-\n")[3:]:
    row = row.replace("\n|", " || ")
    c = [x.strip() for x in row.lstrip("|").split("||")]
    m = LINK.search(c[0])
    if not m or len(c) < 3: continue
    st = LINK.search(c[1])
    co = re.search(r"Coord\|([\d.]+)\|([\d.]+)", row)
    city[canon(m.group(1).strip())] = dict(name=(m.group(2) or m.group(1)).strip(), state=byname.get(st.group(1).lower()) if st else None,
        pop=num(c[2]), lat=float(co.group(1)) if co else None, lon=float(co.group(2)) if co else None)

# state/UT capitals: title -> (state id, capital type)
CAP = {"Amaravati": ("AP", "state"), "Itanagar": ("AR", "state"), "Dispur": ("AS", "state"), "Patna": ("BR", "state"),
 "Raipur": ("CT", "state"), "Panaji": ("GA", "state"), "Gandhinagar": ("GJ", "state"), "Chandigarh": ("CH", "ut"),
 "Shimla": ("HP", "state"), "Ranchi": ("JH", "state"), "Bengaluru": ("KA", "state"), "Thiruvananthapuram": ("KL", "state"),
 "Bhopal": ("MP", "state"), "Mumbai": ("MH", "state"), "Imphal": ("MN", "state"), "Shillong": ("ML", "state"),
 "Aizawl": ("MZ", "state"), "Kohima": ("NL", "state"), "Bhubaneswar": ("OR", "state"), "Jaipur": ("RJ", "state"),
 "Gangtok": ("SK", "state"), "Chennai": ("TN", "state"), "Hyderabad": ("TG", "state"), "Agartala": ("TR", "state"),
 "Lucknow": ("UP", "state"), "Dehradun": ("UT", "state"), "Kolkata": ("WB", "state"), "Port Blair": ("AN", "ut"),
 "New Delhi": ("DL", "national"), "Srinagar": ("JK", "ut"), "Leh": ("LA", "ut"), "Kavaratti": ("LD", "ut"),
 "Puducherry (city)": ("PY", "ut"), "Daman, India": ("DH", "ut")}
# Chandigarh is state capital of Punjab and Haryana as well.
EXTRA_CAP = {"Chandigarh": "also capital of Punjab and Haryana", "Mumbai": "Maharashtra (Mumbai; Nagpur is second capital)",
             "Srinagar": "summer capital; Jammu is winter capital", "Leh": "Leh and Kargil are both administrative capitals"}

# Core district by city: slug -> (2011 state name in ref, 2011 district name in ref). Everything else: same name in same state.
CORE = {"delhi": 95, "bengaluru": 572, "ahmedabad": 474, "kanpur": 164, "kochi": 595, "vijayawada": 547, "jamshedpur": 357,
        "asansol": 335, "vasai-virar": 517, "durg-bhilainagar": 409, "amaravati": 548, "itanagar": 248, "dispur": 322,
        "panaji": 585, "imphal": 277, "shillong": 298, "bhubaneswar": 386, "gangtok": 244, "agartala": 289,
        "port-blair": 640, "leh": 3, "kavaratti": 587,
        "pimpri-chinchwad": 521, "kalyan-dombivli": 517, "navi-mumbai": 517, "howrah": 341, "guwahati": 322,
        "hubli-dharwad": 562, "mira-bhayandar": 517, "bhiwandi": 517, "noida": 141, "durgapur": 335, "nanded-waghala": 511,
        "kalaburagi": 579, "loni": 140, "siliguri": 327, "ulhasnagar": 517, "sangli-miraj-kupwad": 531}
# 2011 district whose 2020 successor differs from the same-code row of districts2020.csv
D2020 = {"delhi": "Delhi|Delhi", "new-delhi": "Delhi|Delhi", "asansol": "West Bengal|Paschim Bardhaman", "durgapur": "West Bengal|Paschim Bardhaman", "vasai-virar": "Maharashtra|Palghar"}

def slug(n): return re.sub(r"[^a-z0-9]+", "-", n.lower()).strip("-")
def norm(n): return re.sub(r"[^a-z]", "", n.lower())

rows, unmatched = {}, []
def add(title, name=None):
    ct = canon(title)
    u, c = ua.get(ct), city.get(ct)
    nm = name or (u or c or {}).get("name") or title
    nm = re.sub(r"\s*\(city\)$|, India$", "", nm)
    s = slug(nm)
    st = (u or {}).get("state") or (CAP.get(title) or (None,))[0] or (c or {}).get("state")
    pg = pages.get(ct, {})
    q = pg.get("qid")
    if q in wdc: lat, lon, src = wdc[q]["lat"], wdc[q]["lon"], "wikidata P625"
    elif pg.get("wp_lat") is not None: lat, lon, src = pg["wp_lat"], pg["wp_lon"], "wikipedia coordinates API"
    elif c and c["lat"] is not None: lat, lon, src = c["lat"], c["lon"], "wikipedia city table"
    else: lat = lon = src = None
    cap = CAP.get(title)
    r = rows.setdefault(s, {"key": s, "name": nm, "state": st, "lat": lat, "lon": lon, "coord_source": src, "wikidata": q,
        "ua_population_2011": None, "ua_level": None, "city_population_2011": None, "is_capital": False, "capital_type": None,
        "capital_note": None, "census2011_district": None, "district2020": None, "wikipedia_title": ct})
    if u: r["ua_population_2011"], r["ua_level"] = u["pop"], u["level"]
    if c and title != "Amaravati": r["city_population_2011"] = c["pop"]  # Amaravati row is not a Census 2011 count
    if cap: r["is_capital"], r["capital_type"], r["capital_note"] = True, cap[1], EXTRA_CAP.get(title)
    return r

for t in ua: add(t)
for t, v in city.items():
    if v["pop"] and v["pop"] >= 500000: add(t)
for t in CAP: add(t)
# New Delhi is capital of India; Delhi row (UA) is the same agglomeration -> keep New Delhi as its own row (NDMC).

# --- district links
stname = {s["id"]: s["name"] for s in states}
for r in rows.values():
    code = None
    if r["key"] in CORE:
        code = CORE[r["key"]]
    else:
        cands = [c for c, d in d11.items() if norm(d["district"]) == norm(r["name"]) and c != 0]
        if len(cands) > 1:
            cands = [c for c in cands if census[c]["state"] == r["state"]] or cands
        if len(cands) == 1: code = cands[0]
    if code is None: unmatched.append(r["key"]); continue
    r["census2011_district"] = str(code)
    cd = d11[code]; sid = census[code]["state"]
    m = [d for d in d20 if d["dt_code"].isdigit() and int(d["dt_code"]) == code and d["year_tag"] == "2011_c"]
    if not m:  # other year tags with the same code, or the same name in the same state
        m = [d for d in d20 if d["dt_code"].isdigit() and int(d["dt_code"]) == code and d["state"] == stname[sid]]
    if not m:
        m = [d for d in d20 if d["state"] == stname[sid] and norm(d["district"]) == norm(cd["district"])]
    if r["key"] in D2020: r["district2020"] = D2020[r["key"]]
    elif len(m) == 1: r["district2020"] = f'{m[0]["state"]}|{m[0]["district"]}'
    else: r["_no2020"] = True

out = sorted(rows.values(), key=lambda r: (-(r["ua_population_2011"] or r["city_population_2011"] or 0), r["key"]))
print("rows", len(out), "capitals", sum(r["is_capital"] for r in out), "with ua pop", sum(r["ua_population_2011"] is not None for r in out))
print("no coords:", [r["key"] for r in out if r["lat"] is None])
print("no district:", unmatched)
print("no district2020:", [r["key"] for r in out if r.get("_no2020")])
print("no state:", [r["key"] for r in out if not r["state"]])
print("coord src:", {s: sum(r["coord_source"] == s for r in out) for s in {r["coord_source"] for r in out}})
bad = [r["key"] for r in out if r["lat"] is not None and not (6 < r["lat"] < 37.5 and 68 < r["lon"] < 98)]
print("out of box:", bad)
for r in out: r.pop("_no2020", None)


F = lambda n, u, t, d, h="neutral": {"name": n, "unit": u, "type": t, "description": d, "higher_is": h}
fields = {
 "lat": F("Latitude", "degrees north", "value", "From Wikidata property P625 of the city item (see coord_source)."),
 "lon": F("Longitude", "degrees east", "value", ""),
 "coord_source": F("Coordinate source", "", "text", "Always 'wikidata P625' in this build; the script falls back to the Wikipedia coordinates API, then the Wikipedia table."),
 "wikidata": F("Wikidata QID", "", "text", ""),
 "wikipedia_title": F("English Wikipedia article title", "", "text", ""),
 "ua_population_2011": F("Urban agglomeration population, Census 2011", "persons", "count",
    "Population of the Census 2011 urban agglomeration or standalone town. Only million-plus UAs/towns are in the source; null for other cities. Kerala UAs are inflated by a changed UA definition in 2011."),
 "ua_level": F("Census unit level", "", "text", "'U.A.' or 'Town' as in the source table."),
 "city_population_2011": F("City (municipal) population, Census 2011", "persons", "count",
    "Population of the city itself from the Wikipedia table of cities above 100,000. Null if the city is not in that table. For some rows (for example Jaipur, Ludhiana) the table repeats the UA value."),
 "is_capital": F("Is a state, UT or national capital", "", "text", "true or false."),
 "capital_type": F("Capital type", "", "text", "national, state or ut."),
 "capital_note": F("Capital note", "", "text", ""),
 "census2011_district": F("Core district code (Census 2011)", "", "text", "censuscode in districts2011.csv of the district that holds the city centre. Chosen by name match or by a fixed table in the build script."),
 "district2020": F("Core district (2020 boundaries)", "", "text", "Key '<state>|<district>' in districts2020.csv. Null if no clear successor.")}
meta = {"id": "cities", "name": "Major Indian cities and urban agglomerations (Census 2011 populations)",
 "source_org": "Wikipedia (tables that cite Census of India 2011) and Wikidata", "url": "https://en.wikipedia.org/w/api.php?action=parse&page=List_of_million-plus_urban_agglomerations_in_India",
 "landing_url": "https://en.wikipedia.org/wiki/List_of_million-plus_urban_agglomerations_in_India",
 "published": "2011-03-31", "reference_year": "2011", "resolution": "city", "license": "Wikipedia text CC BY-SA 4.0; Wikidata CC0; underlying Census data: Government of India.",
 "update_frequency": "decennial", "kind": "curated",
 "limitations": "Populations are from Wikipedia tables, not the official Census tables. UA populations exist only for million-plus UAs and towns. Census 2011 city and UA boundaries differ from today. Kerala UA figures are not comparable with other states. Wikipedia UA figures can differ slightly from official final tables (for example Hyderabad UA). Core district is a single district: a city that covers several districts (Delhi, Mumbai) maps to one of them.",
 "method": "Parse the wikitext of the two Wikipedia pages. Rows = all million-plus UAs/towns + all state/UT capitals (list typed in the script, 34 cities for 36 jurisdictions because Chandigarh serves Punjab and Haryana and New Delhi serves Delhi) + all cities with 2011 city population >= 500,000. Coordinates and QIDs come from Wikidata via the Wikipedia pageprops API and wbgetentities (P625). Districts: name match inside the state, or a fixed table; district2020 via dt_code of districts2020.csv.",
 "accessed": "2026-11-26",
 "redistributed_via": "English Wikipedia (https://en.wikipedia.org/wiki/List_of_million-plus_urban_agglomerations_in_India and https://en.wikipedia.org/wiki/List_of_cities_in_India_by_population), both citing Census of India 2011"}
(OUT / "cities.json").write_text(json.dumps({"meta": meta, "fields": fields, "rows": out}, ensure_ascii=False, indent=1))
