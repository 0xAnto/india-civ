"""Build crop_state from Agricultural Statistics at a Glance 2024-25 (tables 2.3b-2.21b, 2.30, 2.35, 2.38) and
Land Use Statistics at a Glance 2022-23 (tables 1.1, 1.2). Run: .venv/bin/python -I pipeline/build_crop_state.py"""
import re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _resources_common import *

A = open(f"{ROOT}/raw/agri/asg2024-25.txt").read().split("\n")
LUS = open(f"{ROOT}/raw/agri/lus.txt").read().split("\n")
NUMTOK = r"(?:NA|-|\d[\d,]*\.?\d*)"
rows = {}
def row(sid):
    return rows.setdefault(sid, {"key": sid, "name": None, "state": sid})
unmatched = set()

# (b) tables: area (Mha), production (Mt; cotton Mbales), yield, irrigation % for 2023-24
CROPS = {"3": "foodgrains", "4": "rice", "5": "wheat", "9": "maize", "10": "pulses", "14": "oilseeds", "19": "cotton", "21": "sugarcane"}
for i, l in enumerate(A):
    m = re.match(r"\s*Table 2\.(\d+) ?\(b\):", l)
    if not m or m.group(1) not in CROPS: continue
    crop = CROPS[m.group(1)]
    for j in range(i + 1, i + 80):
        L = A[j]
        if re.match(r"\s*Table 2\.\d+", L) and j > i + 3 and "Contd" not in L: break
        sr = split_row(L)
        if not sr or len(sr[1]) < 10: continue
        name, t = sr
        if name == "All India": break
        if name == "Others": continue
        sid = state_id(name)
        if not sid: unmatched.add((crop, name)); continue
        v = [num(x) for x in t]
        r = row(sid)
        r[f"{crop}_area_mha"] = v[0]; r[f"{crop}_prod_mt"] = v[2]; r[f"{crop}_yield_kgha"] = v[4]
        r[f"{crop}_irrigated_pct"] = v[10] if len(v) >= 11 else None

# yield tables for all states (2023-24 = second last of 20 columns)
YT = {"2.30": "foodgrains", "2.35": "pulses", "2.38": "oilseeds"}
for i, l in enumerate(A):
    m = re.match(r"\s*Table (2\.\d+) ?:", l)
    if not m or m.group(1) not in YT or "Contd" in l: continue
    crop = YT[m.group(1)]
    pend = ""
    for j in range(i + 1, i + 120):
        L = A[j]
        if re.match(r"\s*Table 2\.\d+", L) and j > i + 3 and "Contd" not in L: break
        if re.match(r"\s*All India", L): break
        sr = split_row(L)
        if not sr or len(sr[1]) != 20: continue
        sid = state_id(sr[0])
        if not sid: unmatched.add((crop + "_yield", sr[0])); continue
        v = sr[1]
        r = row(sid)
        y = num(v[18])
        r.setdefault(f"{crop}_yield_kgha", y if y else None)
        r[f"{crop}_yield_all_kgha"] = y if y else None
# A&N Islands name wraps over two lines in the foodgrain table
# (first line 'Andaman & Nicobar' maps through alias).

# Land use: net sown (Table 1.1 col 15) and net irrigated (Table 1.2 col 2), 2022-23, thousand ha
def lus_block(lo, hi, idx):
    out = {}
    cur = None
    for L in LUS[lo:hi]:
        s = L.strip()
        if re.match(r"^[A-Z][A-Z &\.\*]+$", s) and not s.startswith("TABLE"):
            cur = s.rstrip("*").strip()
        elif cur and s.startswith("2022-23"):
            toks = s.split()[1:]
            out[cur] = [num(x) for x in toks]
    return out
sown = lus_block(2890, 3401, 3)
irrg = lus_block(3427, 3950, 0)
for nm, v in sown.items():
    sid = state_id(nm)
    if not sid: unmatched.add(("lus_sown", nm)); continue
    row(sid)["net_sown_kha"] = v[3]
for nm, v in irrg.items():
    sid = state_id(nm)
    if not sid: unmatched.add(("lus_irr", nm)); continue
    row(sid)["net_irrigated_kha"] = v[0]
for r in rows.values():
    ns, ni = r.get("net_sown_kha"), r.get("net_irrigated_kha")
    r["irrigation_share_pct"] = round(100 * ni / ns, 1) if ns and ni is not None else None

import csv as _c
names = {x["id"]: x["name"] for x in _c.DictReader(open(f"{ROOT}/data/ref/states.csv"))}
out = []
allf = set()
for sid in names:
    r = rows.get(sid, {"key": sid, "state": sid})
    r["name"] = names[sid]; out.append(r); allf |= set(r)
out = [{**{k: r.get(k) for k in sorted(allf - {"key", "name", "state"})}, "key": r["key"], "name": r["name"], "state": r["state"]} for r in out]

F = {}
for c, lab in [("foodgrains", "Total foodgrains"), ("rice", "Rice"), ("wheat", "Wheat"), ("maize", "Maize"), ("pulses", "Total pulses"),
               ("oilseeds", "Nine oilseeds"), ("cotton", "Cotton"), ("sugarcane", "Sugarcane")]:
    pu = "million bales of 170 kg" if c == "cotton" else "million tonnes"
    F[f"{c}_area_mha"] = {"name": f"{lab} area 2023-24", "unit": "million hectares", "type": "count", "description": "Only the major producing states are listed in the source; others are null.", "higher_is": "neutral"}
    F[f"{c}_prod_mt"] = {"name": f"{lab} production 2023-24", "unit": pu, "type": "count", "description": "Only the major producing states are listed in the source; others are null.", "higher_is": "better"}
    F[f"{c}_yield_kgha"] = {"name": f"{lab} yield 2023-24", "unit": "kg/hectare" if c != "cotton" else "kg lint/hectare", "type": "rate", "description": "From the major-states table where available; for foodgrains, pulses and oilseeds also from the all-state yield table.", "higher_is": "better"}
    F[f"{c}_irrigated_pct"] = {"name": f"{lab} area under irrigation", "unit": "percent", "type": "rate", "description": "Share of the crop area that is irrigated (source year 2023-24 or the latest provisional year).", "higher_is": "better"}
for c in ("foodgrains", "pulses", "oilseeds"):
    F[f"{c}_yield_all_kgha"] = {"name": f"{c.title()} yield 2023-24, all states", "unit": "kg/hectare", "type": "rate", "description": "From the all-state yield table 2.30, 2.35 or 2.38.", "higher_is": "better"}
F["net_sown_kha"] = {"name": "Net area sown 2022-23", "unit": "thousand hectares", "type": "count", "description": "Land Use Statistics at a Glance, table 1.1.", "higher_is": "neutral"}
F["net_irrigated_kha"] = {"name": "Net irrigated area 2022-23", "unit": "thousand hectares", "type": "count", "description": "Land Use Statistics, table 1.2.", "higher_is": "neutral"}
F["irrigation_share_pct"] = {"name": "Irrigation share (net irrigated / net sown)", "unit": "percent", "type": "rate", "description": "100 x net irrigated area / net area sown, 2022-23. Computed by the build script.", "higher_is": "better"}
F = {k: v for k, v in F.items() if k in allf}
meta = {"name": "State-level major crop production 2023-24 and irrigation share", "source_org": "Ministry of Agriculture & Farmers Welfare, DA&FW, Economics & Statistics Division",
 "url": "https://nccd.gov.in/uploads/Agricultural_Statisitcs_at_a_Glance_2024_25_11da3cd37d.pdf; https://desagri.gov.in/wp-content/uploads/2024/09/Final-file-of-LUS-2022-23-for-uploading.pdf",
 "landing_url": "https://desagri.gov.in/", "published": "2025", "reference_year": "2023-24 (crops); 2022-23 (land use)", "resolution": "state",
 "license": "Government Open Data License - India (GODL)", "update_frequency": "annual", "kind": "official",
 "limitations": "The source lists only the major producing states for each crop, so other states are null. It does not mean zero. Yield rows for foodgrains, pulses and oilseeds cover all states. 2023-24 values come from the 2024-25 edition and can differ from earlier advance estimates. Cotton is in million bales of 170 kg.",
 "method": "pdftotext -layout on the PDFs, then regex row parsing. Area, production, yield and irrigation % are copied unchanged. Irrigation share = net irrigated area / net area sown (2022-23) x 100."}
write("crop_state", meta, F, out)
print("rows", len(out), "unmatched", sorted(unmatched))
for r in out:
    if r["state"] in ("UP", "PB", "MH", "KL"): print({k: v for k, v in r.items() if v is not None})
