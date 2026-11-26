"""Build forest_district from ISFR 2023 Volume 2 tables 10.x.3 (district-wise forest cover) and join to district2020.
Run: .venv/bin/python -I pipeline/build_forest_district.py"""
import re, sys, os, csv, json, difflib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _resources_common import *
V = open(f"{ROOT}/raw/forest/v2.txt").read().split("\n")
def norm(s): return re.sub(r"[^a-z0-9]", "", s.lower().replace("&", "and"))
ref = {}
for r in csv.DictReader(open(f"{ROOT}/data/ref/districts2020.csv")): ref.setdefault(r["state"], {})[norm(r["district"])] = r["district"]
STATE_FIX = {"Andaman & Nicobar Islands": "Andaman and Nicobar Islands", "Dadra & Nagar Haveli and Daman & Diu": "Dadra and Nagar Haveli and Daman and Diu", "Jammu & Kashmir": "Jammu and Kashmir"}
# titles with data (second hit of each title is the real table; first hits are the list of tables)
titles = [(i, re.search(r"Table\s+10\.(\d+)\.3\s+District-?\s*wise Forest Cover in (.+?)\s*$", l, flags=re.I)) for i, l in enumerate(V) if i > 1400]
titles = [(i, m) for i, m in titles if m]
tables = {}
for i, m in titles: tables.setdefault(m.group(2).strip(), []).append(i)
ALIAS = {"Kaimur (Bhabua)": "Kaimur", "Kachchh": "Kutch", "Mahesana": "Mehsana", "Mewat": "Nuh", "Kodarma": "Koderma", "Baleswar": "Balasore", "Baudh": "Boudh", "Firozpur": "Ferozepur", "Muktsar": "Sri Muktsar Sahib",
         "Korea": "Koriya", "Bemetara": "Bametara", "Dantewada": "Dakshin Bastar Dantewada", "Kawardha (Kabirdham)": "Kabeerdham", "Uttar Bastar Kanker (Kanker)": "Uttar Bastar Kanker", "Ananthapuramu": "Anantapur",
         "Bengaluru": "Bengaluru Urban", "Balodabazar Bhatapara": "Baloda Bazar", "Gaurela-Pendra-Marwahi": "Gaurela Pendra Marwahi", "Kheri": "Lakhimpur Kheri", "Sahibzada Ajit Singh Nagar": "S.A.S. Nagar", "The Nilgiris": "Nilgiris", "Unakoti": "Unokoti", "Shupiyan": "Shopiyan", "Badgam": "Budgam", "Rajauri": "Rajouri", "Kumuram Bheem": "Komaram Bheem"}
out, unmatched, stat = [], [], {"exact": 0, "fuzzy": 0}
NUM = r"-?\d[\d,]*\.?\d*"
for st, idxs in tables.items():
    start = idxs[0]
    stn = STATE_FIX.get(st, st)
    end = start
    for j in range(start, start + 400):
        if V[j].strip().startswith("Grand Total") or V[j].strip().startswith("Total") and "Grand" not in V[j] and j > start + 8 and re.search(NUM, V[j]):
            end = j; break
    else: end = start + 120
    for j in range(start, end):
        l = V[j]
        m = re.match(r"^\s*([A-Za-z][A-Za-z .'()&\-/,]*?)?\s*((?:" + NUM + r"\s+){7}" + NUM + r")\s*$", l)
        if not m: continue
        nums = [num(x) for x in m.group(2).split()]
        name = (m.group(1) or "").strip()
        if not name:
            above = V[j - 1].strip(); below = V[j + 1].strip()
            fa = above if above and not re.search(r"\d", above) and not above.startswith(("Table", "(km", "District", "Area")) else ""
            fb = below if below and not re.search(r"\d", below) and not below.startswith(("Table", "*")) else ""
            name = (fa + (" " if fa and not fa.endswith("-") else "") + fb).strip()
        name = re.sub(r"\s+", " ", name)
        name = name.split("/")[0].strip()  # UP rows read "new name/ old name"
        name = re.sub(r"(?<=[a-z])\s*H$", "", name)  # trailing H marks hill districts in the PDF
        if not name or name.lower().startswith(("grand", "total")): continue
        out.append((stn, name, nums))
print("raw rows", len(out))
rows, bad, seen = [], [], set()
for st, name, v in out:
    cand = ref.get(st, {})
    name0 = name; name = ALIAS.get(name, name)
    n = norm(name)
    how = "exact" if n in cand else None
    if not how:
        mm = difflib.get_close_matches(n, list(cand), n=1, cutoff=0.88)
        if mm: n = mm[0]; how = "fuzzy"
    if not how: bad.append((st, name)); continue
    rd = cand[n]; key = f"{st}|{rd}"
    if key in seen: bad.append((st, name + " (duplicate)")); continue
    seen.add(key); stat[how] += 1
    rows.append({"key": key, "name": rd, "state": state_id(st), "source_district": name0 if name0 != rd else None, "calc_area_km2": v[0], "vdf_km2": v[1], "mdf_km2": v[2], "of_km2": v[3],
                 "forest_cover_km2": v[4], "forest_cover_pct": v[5], "change_vs_2021_km2": v[6], "scrub_km2": v[7]})
print("matched", len(rows), stat, "unmatched", len(bad))
json.dump(bad, open(f"{ROOT}/raw/forest/forest_district_unmatched.json", "w"), indent=0)
U = {"calc_area_km2": ("Calculated area by Survey of India", "km2", "count"), "vdf_km2": ("Very dense forest", "km2", "count"), "mdf_km2": ("Moderately dense forest", "km2", "count"), "of_km2": ("Open forest", "km2", "count"),
     "forest_cover_km2": ("Forest cover 2023 (total)", "km2", "count"), "forest_cover_pct": ("Forest cover share of calculated area", "percent", "rate"), "change_vs_2021_km2": ("Change in forest cover vs ISFR 2021 (raster based)", "km2", "count"), "scrub_km2": ("Scrub", "km2", "count")}
F = {k: {"name": a, "unit": b, "type": c, "description": "ISFR 2023 Volume 2, district tables.", "higher_is": "better" if k.startswith(("vdf", "mdf", "of_", "forest")) else "neutral"} for k, (a, b, c) in U.items()}
F["source_district"] = {"name": "District name in source", "unit": "", "type": "text", "description": "Only when it differs from the district2020 name.", "higher_is": "neutral"}
write("forest_district", {"name": "India State of Forest Report 2023: district-wise forest cover", "source_org": "Forest Survey of India (MoEFCC)", "url": "https://fsi.nic.in/uploads/isfr2023/isfr_book_eng-vol-2_2023.pdf",
  "landing_url": "https://fsi.nic.in/forest-report-2023", "published": "2024-12-21", "reference_year": "2023", "resolution": "district2020", "license": "Government of India open data; cite FSI", "update_frequency": "biennial", "kind": "satellite",
  "limitations": "Districts of the 2023 report that are not in data/ref/districts2020.csv (new districts) are not joined. See data/meta/forest_district.md. Row names that the PDF wraps over several lines are rebuilt by a script heuristic and may fail (counted as unmatched).",
  "method": "pdftotext -layout of Volume 2; rows with 8 numbers (calculated area, VDF, MDF, OF, total, %, change, scrub); names joined from wrapped lines; matched to district2020 by normalised name inside the state (exact, then difflib ratio >= 0.88)."}, F, rows)
