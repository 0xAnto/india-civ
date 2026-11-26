"""Build crop_district (2022-23) from raw/agri/apy/*.html (fetched by fetch_apy.py) and join to district2020 keys.
Run: .venv/bin/python -I pipeline/build_crop_district.py"""
import re, os, sys, csv, glob, difflib, json, html
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _resources_common import *

def norm(s):
    s = s.lower().replace("&", " and ")
    s = re.sub(r"\b(district|dist)\b", " ", s)
    return re.sub(r"[^a-z0-9]", "", s)
ref = {}
for r in csv.DictReader(open(f"{ROOT}/data/ref/districts2020.csv")):
    ref.setdefault(r["state"], {})[norm(r["district"])] = r["district"]
STATE_ALIAS = {"The Dadra & Nagar Haveli and Daman and Diu": "Dadra and Nagar Haveli and Daman and Diu", "Dadra and Nagar Haveli": "Dadra and Nagar Haveli and Daman and Diu", "Daman and Diu": "Dadra and Nagar Haveli and Daman and Diu"}
ALIAS_RAW = {  # renamed districts only: same area, new spelling or new official name
 "Assam": {"Kamrup metro": "Kamrup Metropolitan", "Marigaon": "Morigaon"},
 "Bihar": {"Kaimur (bhabua)": "Kaimur", "Pashchim champaran": "West Champaran", "Purbi champaran": "East Champaran"},
 "Chhattisgarh": {"Bemetara": "Bametara", "Dantewada": "Dakshin Bastar Dantewada", "Kabirdham": "Kabeerdham", "Kanker": "Uttar Bastar Kanker", "Korea": "Koriya"},
 "Gujarat": {"Ahmadabad": "Ahmedabad", "Chhotaudepur": "Chhota Udaipur", "Dohad": "Dahod", "Kachchh": "Kutch", "Mahesana": "Mehsana"},
 "Haryana": {"Gurgaon": "Gurugram", "Mewat": "Nuh"},
 "Jammu and Kashmir": {"Badgam": "Budgam", "Poonch": "Punch", "Rajauri": "Rajouri"},
 "Jharkhand": {"Sahebganj": "Sahibganj"},
 "Karnataka": {"Bangalore rural": "Bengaluru Rural", "Belgaum": "Belagavi", "Bellary": "Ballari", "Bijapur": "Vijayapura", "Chikballapur": "Chikkaballapura", "Chikmagalur": "Chikkamagaluru", "Gulbarga": "Kalaburagi", "Mysore": "Mysuru", "Shimoga": "Shivamogga", "Tumkur": "Tumakuru"},
 "Ladakh": {"Leh ladakh": "Leh"},
 "Maharashtra": {"Ahilyanagar": "Ahmednagar", "Chhatrapati Sambhajinagar": "Aurangabad", "Dharashiv": "Osmanabad"},
 "Odisha": {"Baleshwar": "Balasore", "Sonepur": "Subarnapur"},
 "Puducherry": {"Pondicherry": "Puducherry"},
 "Punjab": {"Firozepur": "Ferozepur", "Muktsar": "Sri Muktsar Sahib", "Nawanshahr": "Shahid Bhagat Singh Nagar"},
 "Tamil Nadu": {"Kanchipuram": "Kancheepuram", "The nilgiris": "Nilgiris"},
 "Telangana": {"Bhadradri": "Bhadradri Kothagudem", "Jangoan": "Jangaon", "Jayashankar": "Jayashankar Bhupalapally", "Jogulamba": "Jogulamba Gadwal", "Komaram bheem asifabad": "Komaram Bheem", "Medchal": "Medchal Malkajgiri", "Rajanna": "Rajanna Sircilla", "Yadadri": "Yadadri Bhuvanagiri"},
 "Tripura": {"Unakoti": "Unokoti"},
 "Uttar Pradesh": {"Allahabad": "Prayagraj", "Faizabad": "Ayodhya", "Kheri": "Lakhimpur Kheri", "Sant kabeer nagar": "Sant Kabir Nagar", "Sant ravidas nagar": "Bhadohi", "Shravasti": "Shrawasti"},
 "West Bengal": {"24 paraganas north": "North 24 Parganas", "24 paraganas south": "South 24 Parganas", "Dinajpur dakshin": "Dakshin Dinajpur", "Dinajpur uttar": "Uttar Dinajpur", "Medinipur east": "Purba Medinipur", "Medinipur west": "Paschim Medinipur"},
}
ALIAS = {(st, norm(k)): v for st, d in ALIAS_RAW.items() for k, v in d.items()}
def match(state, dist):
    st = STATE_ALIAS.get(state, state)
    cand = ref.get(st, {})
    n = norm(dist)
    if n in cand: return st, cand[n], "exact"
    if (st, n) in ALIAS: return st, ALIAS[(st, n)], "alias"
    m = difflib.get_close_matches(n, list(cand), n=1, cutoff=0.9)
    if m: print("FUZZY", st, dist, "->", cand[m[0]]); return st, cand[m[0]], "fuzzy"
    return st, None, None

def parse(fn):
    h = open(fn).read()
    if "<table" not in h.lower(): return None, []
    txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "|", h))
    unit = re.search(r"Production \(([A-Za-z]+)\)", txt)
    rows = []; cur = None
    for tr in re.split(r"<tr[^>]*>", h)[1:]:  # the portal HTML often misses closing </tr> tags
        c = [html.unescape(re.sub(r"<[^>]+>", "", x)).strip() for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, flags=re.S)]
        v = lambda x: num(x) if x not in ("", "-") else None
        if len(c) >= 6 and re.fullmatch(r"\d+", c[0]):
            cur = c[1]; rows.append((cur, c[2], v(c[3]), v(c[4])))
        elif len(c) == 4 and cur and c[0] and not c[0].lower().startswith(("s.no", "state")) and num(c[1].replace(",", "")) is not None:
            rows.append((cur, c[0], v(c[1]), v(c[2])))
    return (unit.group(1) if unit else None), rows
data = {}      # (state, district, crop) -> (area, prod)
units = {}
for fn in sorted(glob.glob(f"{ROOT}/raw/agri/apy/*.html")):
    b = os.path.basename(fn)[:-5]; kind, st, crop = b.split("_")
    unit, rows = parse(fn)
    if unit: units.setdefault(crop, set()).add(unit)
    for s, d, a, p in rows: data[(s, d, crop)] = (a, p)
print("units", units, "records", len(data))
dists = {}
for (s, d, crop), (a, p) in data.items(): dists.setdefault((s, d), {})[crop] = (a, p)
rows, unmatched = [], []
CROPS = ["rice", "wheat", "maize", "pulses", "sugarcane", "cotton", "oilseeds", "cereals", "foodgrains"]
stat = {"exact": 0, "alias": 0, "fuzzy": 0}
seen = set()
for (s, d), cr in sorted(dists.items()):
    st, rd, how = match(s, d)
    sid = state_id(st)
    if not rd: unmatched.append((s, d)); continue
    key = f"{st}|{rd}"
    if key in seen: unmatched.append((s, d + " (duplicate key)")); continue
    seen.add(key); stat[how] += 1
    row = {"key": key, "name": rd, "state": sid, "source_district": d if d != rd else None}
    for c in CROPS:
        a, p = cr.get(c, (None, None))
        row[f"{c}_area_ha"] = a; row[f"{c}_prod"] = p
        row[f"{c}_yield"] = round(p / a, 3) if a and p is not None else None
    # foodgrain total built only from listed crops: rice + wheat + maize + pulses (cereals total is also given by the source)
    parts = [row["rice_prod"], row["wheat_prod"], row["maize_prod"], row["pulses_prod"]]
    row["listed_foodgrain_prod_t"] = sum(parts) if all(x is not None for x in parts) else None
    rows.append(row)
print("matched", len(rows), stat, "unmatched", len(unmatched))
json.dump(unmatched, open(f"{ROOT}/raw/agri/apy_unmatched.json", "w"), indent=0)
F = {}
LAB = {"rice": "Rice", "wheat": "Wheat", "maize": "Maize", "pulses": "Total pulses", "sugarcane": "Sugarcane", "cotton": "Cotton (lint)", "oilseeds": "Total oilseeds", "cereals": "Cereals & millets (total)", "foodgrains": "Foodgrains (total, source group)"}
for c in CROPS:
    pu = "bales of 170 kg" if c == "cotton" else "tonnes"
    F[f"{c}_area_ha"] = {"name": f"{LAB[c]} area 2022-23", "unit": "hectares", "type": "count", "description": "All seasons added by the source.", "higher_is": "neutral"}
    F[f"{c}_prod"] = {"name": f"{LAB[c]} production 2022-23", "unit": pu, "type": "count", "description": "", "higher_is": "better"}
    F[f"{c}_yield"] = {"name": f"{LAB[c]} yield 2022-23", "unit": pu + "/hectare", "type": "rate", "description": "Production / area, computed here.", "higher_is": "better"}
F["listed_foodgrain_prod_t"] = {"name": "Listed-crop foodgrain production (rice + wheat + maize + total pulses)", "unit": "tonnes", "type": "count",
  "description": "Sum of the four listed crops only. It leaves out jowar, bajra, ragi, barley and small millets, so it is lower than the official foodgrain total. Null if any of the four is missing.", "higher_is": "better"}
F["source_district"] = {"name": "District name in source", "unit": "", "type": "text", "description": "Only when it differs from the district2020 name.", "higher_is": "neutral"}
meta = {"name": "District-wise area, production and yield of major crops, 2022-23", "source_org": "Directorate of Economics & Statistics, Ministry of Agriculture & Farmers Welfare (APY portal)",
  "url": "https://data.desagri.gov.in/report/crop/apy-query-report-show and https://data.desagri.gov.in/report/crop/report-district-level", "landing_url": "https://data.desagri.gov.in/website/crops-apy-report-web",
  "published": "2024", "reference_year": "2022-23", "resolution": "district2020", "license": "Government Open Data License - India (GODL)", "update_frequency": "annual", "kind": "official",
  "limitations": "Source reports 2022-23 district totals from the states. Some states report few districts or leave crops blank (null). New districts (for example in Andhra Pradesh after 2022) do not exist in data/ref/districts2020.csv and are not joined; see data/meta/crop_district.md. Cotton production is in bales of 170 kg. 'cereals' and 'foodgrains' are source totals that include crops not in this file.",
  "method": "fetch_apy.py posts the portal query forms (per state; crops rice, wheat, maize, cotton, sugarcane; groups cereals, pulses, foodgrains, oilseeds). build_crop_district.py parses the HTML tables, joins on normalised district names within state (exact, then difflib ratio >= 0.9), and computes yield = production / area."}
write("crop_district", meta, F, rows)
