"""Build forest_state from ISFR 2023 Volume 1: tables 9.1 (forest cover), 9.7 (tree cover), 3.3 (mangrove).
Run: .venv/bin/python -I pipeline/build_forest_state.py"""
import re, sys, os, csv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _resources_common import *
V = open(f"{ROOT}/raw/forest/v1.txt").read().split("\n")
names = {x["id"]: x["name"] for x in csv.DictReader(open(f"{ROOT}/data/ref/states.csv"))}
def find(pat, nth=0):
    return [i for i, l in enumerate(V) if re.search(pat, l)][nth]
def rows_in(lo, hi, ncols, serial=False, skipwords=()):
    out, bad = {}, []
    for i in range(lo, hi):
        l = V[i]
        l = re.sub(r"^\s*\d{1,3}\s{2,}", "", l) if serial else l
        l = re.sub(r"\s(#+|\*+)(?=\s)", "", l)
        l = re.sub(r"(?<=[A-Za-z])\*+", "", l)
        sr = split_row(l)
        if not sr or len(sr[1]) != ncols: continue
        nm = sr[0].strip()
        if nm in ("Total", "Grand Total"): continue
        sid = state_id(nm)
        if not sid: bad.append(nm); continue
        out[sid] = [None if t in ("-", "NA") else num(t) for t in sr[1]]
    return out, bad
# Table 9.1: GA, FC2013, FC2023, change, %  (J&K and Ladakh have no own GA: 4 numbers)
t91 = find(r"Table 9\.1 Decadal Change in Forest Cover")
fc, b1 = rows_in(t91, t91 + 60, 5)
fc4, _ = rows_in(t91, t91 + 60, 4)
# Table 9.7 tree cover: GA, TC2013, TC2023, change, %
t97a, t97b = find(r"Table 9\.7 Decadal Change of Tree Cover", 0), find(r"Table 9\.7 Decadal Change of Tree Cover", 1)
tc = {}
for lo, hi in ((t97a, t97a + 50), (t97b, t97b + 60)):
    r, b2 = rows_in(lo, hi, 5, serial=True); tc.update(r)
    r4, _ = rows_in(lo, hi, 4, serial=True)
    for k, v in r4.items(): tc.setdefault(k, [None] + v)
# Table 3.3 mangrove: 2021 (VD, MD, OM, Total), 2023 (VD, MD, OM, Total), change = 9 numbers
m33 = find(r"Table 3\.3 State/UT wise Mangrove Cover Assessment 2023")
mg, b3 = rows_in(m33, m33 + 40, 9, serial=True)
print("unmatched", b1, b3)
rows = []
for sid, nm in names.items():
    f = fc.get(sid); f4 = fc4.get(sid); t = tc.get(sid); m = mg.get(sid)
    ga = f[0] if f else None
    fcov = f[2] if f else (f4[1] if f4 else None)
    fc13 = f[1] if f else (f4[0] if f4 else None)
    rows.append({"key": sid, "name": nm, "state": sid, "geo_area_km2": ga,
        "forest_cover_km2": fcov, "forest_cover_pct": round(100 * fcov / ga, 2) if ga and fcov is not None else None,
        "forest_cover_2013_km2": fc13, "forest_cover_change_km2": (f[3] if f else (f4[2] if f4 else None)),
        "tree_cover_km2": t[2] if t else None, "tree_cover_pct": round(100 * t[2] / ga, 2) if ga and t and t[2] is not None else None,
        "mangrove_km2": m[7] if m else (0.0 if sid in names and fcov is not None and False else None)})
# Rows whose state name wraps over two text lines (or has a page number in front) are not parsed. Values below are typed from the same tables.
OVR = {"DH": {"geo_area_km2": 602.0, "forest_cover_km2": 225.62, "forest_cover_2013_km2": 219.96, "forest_cover_change_km2": 5.66, "tree_cover_km2": 36.83, "mangrove_km2": 3.86},
       "MN": {"tree_cover_km2": 209.82}, "AP": {"mangrove_km2": 421.43}, "AN": {"mangrove_km2": 608.29}}
for r in rows:
    for k, v in OVR.get(r["state"], {}).items():
        r[k] = v
    ga = r["geo_area_km2"]
    if ga:
        r["forest_cover_pct"] = round(100 * r["forest_cover_km2"] / ga, 2)
        if r["tree_cover_km2"] is not None: r["tree_cover_pct"] = round(100 * r["tree_cover_km2"] / ga, 2)
# mangrove: coastal states not in table 3.3 have no mangrove cover in ISFR 2023; the table lists only states with mangrove. Keep null for non-listed states.
U = {"geo_area_km2": ("Geographical area", "km2", "count"), "forest_cover_km2": ("Forest cover 2023 (VDF+MDF+OF, inside and outside RFA)", "km2", "count"),
     "forest_cover_pct": ("Forest cover share of geographical area", "percent", "rate"), "forest_cover_2013_km2": ("Forest cover 2013 (ISFR 2013 assessment)", "km2", "count"),
     "forest_cover_change_km2": ("Change in forest cover 2013 to 2023", "km2", "count"), "tree_cover_km2": ("Tree cover 2023 (outside recorded forest)", "km2", "count"),
     "tree_cover_pct": ("Tree cover share of geographical area", "percent", "rate"), "mangrove_km2": ("Mangrove cover 2023", "km2", "count")}
F = {k: {"name": v[0], "unit": v[1], "type": v[2], "description": "India State of Forest Report 2023, Volume 1.", "higher_is": "neutral" if k in ("geo_area_km2",) else "better"} for k, v in U.items()}
meta = {"name": "India State of Forest Report 2023: forest, tree and mangrove cover by state", "source_org": "Forest Survey of India (MoEFCC)",
 "url": "https://fsi.nic.in/uploads/isfr2023/isfr_book_eng-vol-1_2023.pdf", "landing_url": "https://fsi.nic.in/forest-report-2023", "published": "2024-12-21", "reference_year": "2023",
 "resolution": "state", "license": "Government of India open data; cite FSI", "update_frequency": "biennial", "kind": "satellite",
 "limitations": "Satellite interpretation (LISS-III, 23.5 m) plus field checks. Tree cover is a sample-plot estimate. J&K and Ladakh have no separate geographical area in the report (combined 222,236 km2), so their percent fields are null. Mangrove is null for states not listed in table 3.3 (no mangrove cover reported). 2013 forest cover for Telangana and Andhra Pradesh follow the report.",
 "method": "pdftotext -layout; rows parsed from tables 9.1, 9.7 and 3.3. Percent = 100 x area / geographical area, computed here and rounded to 2 decimals."}
write("forest_state", meta, F, rows)
for r in rows:
    if r["state"] in ("MP", "JK", "LA", "WB", "RJ"): print(r)
print(sum(1 for r in rows if r["forest_cover_km2"] is not None), sum(1 for r in rows if r["tree_cover_km2"] is not None), sum(1 for r in rows if r["mangrove_km2"] is not None))
