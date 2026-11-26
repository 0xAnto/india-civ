"""Build mineral-resource datasets at state level and point level.
  minerals_state  - IBM Indian Minerals Yearbook 2024, table 1-2 (value of mineral production, reporting mines), 2023-24
  coal_state      - Ministry of Coal, Coal Directory 2024-25: raw coal and lignite production by state, 2024-25
  oilgas_state    - MoPNG Monthly Production Report March 2026: crude oil and natural gas by state, FY2025-26
  minerals_points - Wikidata mines, quarries, oil fields in India
Run: .venv/bin/python -I pipeline/build_minerals.py"""
import re, sys, os, csv, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _resources_common import *
names = {x["id"]: x["name"] for x in csv.DictReader(open(f"{ROOT}/data/ref/states.csv"))}
GODL = "Government Open Data License - India (GODL) / Government of India publication"
def F(d): return {k: {"name": v[0], "unit": v[1], "type": v[2], "description": v[3], "higher_is": "neutral"} for k, v in d.items()}

# ---- minerals_state
I = open(f"{ROOT}/raw/minerals/imyb.txt").read().split("\n")
s = next(i for i, l in enumerate(I) if "Table – 1: Value* of Mineral Production, 2021-22 to 2023-24" in l)
val, mines = {}, {}
for l in I[s:s + 40]:
    if "Table – 2" in l: break
    sr = split_row(l)
    if sr and len(sr[1]) == 3 and sr[0] != "India":
        sid = state_id(sr[0]); val[sid] = num(sr[1][2]) if sr[1][2] != "-" else None
s2 = next(i for i, l in enumerate(I) if "Table – 2: Number of Reporting Mines*, 2021-22 to 2023-24" in l)
for l in I[s2:s2 + 45]:
    if "Table- 2 (Concld.)" in l or "Table – 3" in l: pass
    sr = split_row(l)
    if sr and len(sr[1]) == 3 and sr[0] != "India":
        sid = state_id(sr[0]); mines[sid] = num(sr[1][2])
rows = []
for sid, nm in names.items():
    v = val.get(sid)
    rows.append({"key": sid, "name": nm, "state": sid, "value_rs_thousand": v, "value_rs_crore": round(v / 10000, 1) if v else None,
                 "reporting_mines": mines.get(sid)})
tot = sum(r["value_rs_thousand"] or 0 for r in rows); print("minerals_state sum", tot, "(India 1418034586)")
write("minerals_state", {"name": "Value of mineral production and reporting mines by state (excl. fuel, atomic, minor minerals)", "source_org": "Indian Bureau of Mines, Ministry of Mines",
  "url": "https://ibm.gov.in/writereaddata/files/177426215469c1178a48453IMYB_2024_EBookFinal.pdf", "landing_url": "https://ibm.gov.in/?c=pages&id=77&m=index", "published": "2025", "reference_year": "2023-24 (provisional)",
  "resolution": "state", "license": GODL, "update_frequency": "annual", "kind": "official",
  "limitations": "Excludes fuel minerals (coal, lignite, oil, gas), atomic minerals and minor minerals such as sand and stone. A null value means the state is not in the IBM table (no reported MCDR production). Goa 2023-24 value is small because of the mining ban period.",
  "method": "pdftotext -layout, then rows of tables 1 and 2 of the State Reviews chapter. Rs crore = Rs thousand / 10,000 (computed here)."},
  F({"value_rs_thousand": ("Value of mineral production 2023-24", "Rs thousand", "count", "Source unit."), "value_rs_crore": ("Value of mineral production 2023-24", "Rs crore", "count", "Rs thousand / 10000."),
     "reporting_mines": ("Reporting mines 2023-24", "mines", "count", "Mines that reported production or developmental work.")}), rows)

# ---- coal_state
C = open(f"{ROOT}/raw/minerals/coal.txt").read().split("\n")
def block(title_idx, lo_hi):
    out = {}
    lines = C[lo_hi[0]:lo_hi[1]]
    names_ = None
    for i, l in enumerate(lines):
        if re.match(r"\s{10,}\S", l) and not l.strip().startswith(("Year", "Quantity", "(", "Table", "Office", "Coal Directory", "Contd")) and "Qty" not in l and re.search(r"[A-Za-z]{3}", l) and not re.search(r"\d{4}-\d{2}", l) and not re.search(r"\d\.\d", l):
            nm = [x.strip() for x in re.split(r"\s{3,}", l.strip()) if x.strip()]
            if all(re.match(r"^[A-Za-z &]+$", x) for x in nm): names_ = nm
        if l.strip().startswith("2024-25") and names_:
            toks = re.sub(r"[▲▼]\s*[\d.]+%", " ", l.strip()[7:]).split()
            nums = [num(t) for t in toks]
            # states: (qty, share) pairs; 'All India': qty only
            n = len(names_)
            has_all = names_[-1] == "All India"
            ns = n - (1 if has_all else 0)
            pairs = []
            body = nums[:]
            if has_all: allq = body.pop()
            pairs = [(body[k], body[k + 1]) for k in range(0, len(body) - 1, 2)]
            sn = names_[:ns]
            for nm, p in zip(sn[len(sn) - len(pairs):], pairs): out[nm] = p[0]
            if has_all: out["All India"] = allq
            names_ = None
    return out
t39 = next(i for i, l in enumerate(C) if "Table 3.9 : State Wise Raw Coal Production in last Ten Years" in l and i > 3000)
coal = block(None, (t39, t39 + 90))
t310 = next(i for i, l in enumerate(C) if "Table 3.10 : State Wise Lignite Production in last Ten Years" in l and i > 3000)
lig = block(None, (t310, t310 + 40))
print("coal", coal); print("lignite", lig)
rows = []
for sid, nm in names.items():
    c = lig_ = None
    for k, v in coal.items():
        if k != "All India" and state_id(k) == sid: c = v
    for k, v in lig.items():
        if k != "All India" and state_id(k) == sid: lig_ = v
    rows.append({"key": sid, "name": nm, "state": sid, "raw_coal_mt": c, "lignite_mt": lig_})
print("coal sum", sum(r["raw_coal_mt"] or 0 for r in rows), coal.get("All India"), "lig", sum(r["lignite_mt"] or 0 for r in rows), lig.get("All India"))
write("coal_state", {"name": "Raw coal and lignite production by state", "source_org": "Ministry of Coal, Coal Controller's Organisation (Coal Directory of India 2024-25, provisional)",
  "url": "https://coal.gov.in/sites/default/files/2024-03/28-11-2025a-stc.pdf", "landing_url": "https://coal.gov.in/", "published": "2025-11-28", "reference_year": "2024-25 (provisional)",
  "resolution": "state", "license": GODL, "update_frequency": "annual", "kind": "official",
  "limitations": "Null means the source gives no production for the state in 2024-25 (not necessarily zero reserves). Coalfield polygons and coal mine points were not available as a download without login.",
  "method": "pdftotext -layout; 2024-25 row of tables 3.9 (raw coal) and 3.10 (lignite). Units kept in million tonnes."},
  F({"raw_coal_mt": ("Raw coal production 2024-25", "million tonnes", "count", "Table 3.9."), "lignite_mt": ("Lignite production 2024-25", "million tonnes", "count", "Table 3.10.")}), rows)

# ---- oilgas_state
P = open(f"{ROOT}/raw/energy/mpr.txt").read().split("\n")
a1 = next(i for i, l in enumerate(P) if "Annexure-I (Par" in l)
a2 = next(i for i, l in enumerate(P) if "Annexure-II (Par" in l)
a3 = next(i for i, l in enumerate(P) if "Annexure-III (Par" in l)
def agg(lo, hi):
    on, off, cbm = {}, {}, {}
    for l in P[lo:hi]:
        sr = split_row(l.replace("(CBM)", "").strip())
        if not sr or len(sr[1]) < 7: continue
        nm = sr[0]; v = num(sr[1][5])
        if nm.startswith(("Eastern", "Western", "Gujarat Offshore", "ONSHORE", "OFFSHORE", "GRAND", "TOTAL", "CBM")): 
            if nm in ("Eastern Offshore", "Western Offshore", "Gujarat Offshore"): off[nm] = off.get(nm, 0) + v
            continue
        sid = state_id(nm)
        if not sid: print("oilgas unmatched", nm); continue
        is_cbm = "CBM" in l and "(CBM)" in l
        (cbm if is_cbm else on)[sid] = (cbm if is_cbm else on).get(sid, 0) + v
    return on, off, cbm
oil, oiloff, _ = agg(a1, a2)
gas, gasoff, cbm = agg(a2, a3)
print("oil", oil, oiloff, "\ngas", gas, gasoff, cbm)
rows = []
for sid, nm in names.items():
    rows.append({"key": sid, "name": nm, "state": sid, "crude_onshore_tmt": round(oil[sid], 2) if sid in oil else None,
                 "gas_onshore_mmscm": round(gas[sid], 2) if sid in gas else None, "cbm_mmscm": round(cbm[sid], 2) if sid in cbm else None})
write("oilgas_state", {"name": "Onshore crude oil and natural gas production by state", "source_org": "Ministry of Petroleum & Natural Gas, Economic & Statistics Division (Monthly Production Report, March 2026)",
  "url": "https://mopng.gov.in/files/petroleumStatistics/monthlyProduction/MPR-March-26.pdf", "landing_url": "https://mopng.gov.in/en/petroleum-statistics/monthly-production", "published": "2026-04-15", "reference_year": "2025-26 (April-March, provisional)",
  "resolution": "state", "license": GODL, "update_frequency": "monthly", "kind": "official",
  "limitations": "Offshore production is not split by state, so it is not in the rows. Offshore crude 2025-26 (TMT): " + json.dumps({k: round(v, 2) for k, v in oiloff.items()}) + ". Offshore gas (MMSCM): " + json.dumps({k: round(v, 2) for k, v in gasoff.items()}) + ". Crude includes condensate. Null means no onshore production listed for the state. PPAC annual Indian Petroleum & Natural Gas Statistics was not used.",
  "method": "pdftotext -layout; cumulative April-March 2025-26 column of Annexure I (crude) and II (gas); ONGC, OIL and private/JV rows are summed per state. CBM is shown separately."},
  F({"crude_onshore_tmt": ("Onshore crude oil and condensate 2025-26", "thousand tonnes", "count", "Sum of ONGC, OIL, private/JV."), "gas_onshore_mmscm": ("Onshore natural gas 2025-26", "million standard cubic metres", "count", "Sum of ONGC, OIL, private/JV, excludes CBM."),
     "cbm_mmscm": ("Coal bed methane 2025-26", "million standard cubic metres", "count", "Jharkhand, Madhya Pradesh, West Bengal.")}), rows)

# ---- minerals_points (Wikidata)
import shapefile
from shapely.geometry import shape, Point
sf = shapefile.Reader(f"{ROOT}/raw/boundaries/states_Admin2.shp")
polys = [(rec[0], shape(sh.__geo_interface__)) for sh, rec in zip(sf.shapes(), sf.records())]
def st_of(lon, lat):
    p = Point(lon, lat)
    for nm, g in polys:
        if g.contains(p): return state_id(nm)
    return None
pts, seen = [], set()
for r in csv.DictReader(open(f"{ROOT}/raw/minerals/wd_fields.csv")):
    qid = r["i"].rsplit("/", 1)[1]
    if qid in seen: continue
    seen.add(qid)
    m = re.match(r"Point\(([-\d.]+) ([-\d.]+)\)", r["c"])
    if not m: continue
    lon, lat = float(m.group(1)), float(m.group(2))
    nm = r["iLabel"]
    pts.append({"key": qid, "name": None if re.fullmatch(r"Q\d+", nm) else nm, "lat": lat, "lon": lon, "category": r["tLabel"], "state": st_of(lon, lat), "wikidata_state": r["stLabel"] or None})
print("points", len(pts), "no state", sum(1 for x in pts if not x["state"]))
write("minerals_points", {"name": "Mines, quarries and oil fields in India (Wikidata)", "source_org": "Wikidata (community, CC0)",
  "url": "https://query.wikidata.org/sparql (instances of mine Q820477, quarry Q188040, oil field Q211748, coal deposit Q12091026, natural gas field Q1349255, coal mine Q959309; country India; with coordinates)",
  "landing_url": "https://www.wikidata.org/", "published": "2026-11-26", "reference_year": "2026 (snapshot)", "resolution": "point", "license": "CC0", "update_frequency": "continuous", "kind": "curated",
  "limitations": "Sparse and uneven. Only about 135 items have coordinates. Wikidata has no commodity field for most of them. Many items have no name (name is null). It is not a complete list of Indian mines. The Global Energy Monitor tracker was not used (needs request form).",
  "method": "SPARQL query with P31 in the type list and P17=India and P625 present. State comes from point-in-polygon on the project state boundary file (raw/boundaries/states_Admin2.shp), not from Wikidata."},
  {"category": {"name": "Wikidata type", "unit": "", "type": "text", "description": "mine, quarry, oil field or coal deposit", "higher_is": "neutral"},
   "wikidata_state": {"name": "State label in Wikidata", "unit": "", "type": "text", "description": "P131 label where present", "higher_is": "neutral"}}, pts)
