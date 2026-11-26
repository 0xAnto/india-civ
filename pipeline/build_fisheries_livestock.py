"""Build fisheries_state (ASG 2024-25 table 2.57) and livestock_state (table 2.55). Run: .venv/bin/python -I pipeline/build_fisheries_livestock.py"""
import re, sys, os, csv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _resources_common import *
A = open(f"{ROOT}/raw/agri/asg2024-25.txt").read().split("\n")
names = {x["id"]: x["name"] for x in csv.DictReader(open(f"{ROOT}/data/ref/states.csv"))}

def table(title_re, ncols, endre):
    start = next(i for i, l in enumerate(A) if re.match(title_re, l.strip()) and "Contd" not in l)
    out, bad = {}, set()
    for l in A[start:start + 260]:
        if re.match(r"\s*All India", l): break
        l2 = re.sub(r"^\s*\d{1,2}\s+(?=[A-Za-z])", "", l)
        sr = split_row(l2)
        if not sr or len(sr[1]) != ncols: continue
        sid = state_id(sr[0])
        if not sid: bad.add(sr[0]); continue
        out[sid] = [None if t in ("-", "NA") else num(t) for t in sr[1]]
    return out, bad

# fisheries: 2019-20..2023-24 x (inland, marine, total) lakh tonnes
fish, bad = table(r"Table 2\.57:", 15, None)
print("fish", len(fish), "unmatched", bad)
rows = []
for sid in names:
    v = fish.get(sid)
    rows.append({"key": sid, "name": names[sid], "state": sid,
      "inland_lakh_t": v[12] if v else None, "marine_lakh_t": v[13] if v else None, "total_lakh_t": v[14] if v else None,
      "total_series": {y: v[3*k+2] for k, y in enumerate(["2019-20","2020-21","2021-22","2022-23","2023-24"])} if v else None})
F = {"inland_lakh_t": {"name": "Inland fish production 2023-24", "unit": "lakh tonnes", "type": "count", "description": "Inland capture and culture fisheries.", "higher_is": "better"},
     "marine_lakh_t": {"name": "Marine fish production 2023-24", "unit": "lakh tonnes", "type": "count", "description": "Marine capture. Landlocked states have 0.", "higher_is": "better"},
     "total_lakh_t": {"name": "Total fish production 2023-24", "unit": "lakh tonnes", "type": "count", "description": "Inland plus marine, as printed in the source.", "higher_is": "better"},
     "total_series": {"name": "Total fish production, 2019-20 to 2023-24", "unit": "lakh tonnes", "type": "value", "description": "Series keyed by agricultural year.", "higher_is": "better"}}
meta = {"name": "State-wise fish production, inland and marine", "source_org": "Department of Fisheries, MoFAH&D (printed in DA&FW Agricultural Statistics at a Glance 2024-25, table 2.57)",
 "url": "https://nccd.gov.in/uploads/Agricultural_Statisitcs_at_a_Glance_2024_25_11da3cd37d.pdf", "landing_url": "https://dof.gov.in/", "published": "2025", "reference_year": "2023-24", "resolution": "state",
 "license": "Government Open Data License - India (GODL)", "update_frequency": "annual", "kind": "official",
 "limitations": "2023-24 values are provisional. The Handbook on Fisheries Statistics (dof.gov.in) was not reachable, so the table in Agricultural Statistics at a Glance is used. The source rounds to 0.01 lakh tonnes, so small values show 0.00.",
 "method": "pdftotext -layout, row parsing, no unit change. 1 lakh tonnes = 100,000 tonnes."}
write("fisheries_state", meta, F, rows)

# livestock: milk (kt), eggs (lakh), meat (kt), wool (000 kg), 2023-24
def tab_idx(title):
    return [i for i, l in enumerate(A) if l.strip().startswith(title)]
bad1, res = set(), {}
st = next(i for i, l in enumerate(A) if l.strip().startswith("Table 2.55:"))
kind = None
for l in A[st:st + 400]:
    if l.strip().startswith("Table 2.56"): break
    if "Milk" in l and "Egg" in l: kind = "me"
    if "Meat" in l and "Wool" in l: kind = "mw"
    if re.match(r"\s*All India", l): continue
    sr = split_row(l)
    if not sr or len(sr[1]) != 18 or not kind: continue
    sid = state_id(sr[0])
    if not sid: bad1.add(sr[0]); continue
    v = [None if t in ("-", "NA") else num(t) for t in sr[1]]
    new = (v[8], v[17])
    old = res.setdefault(sid, {}).get(kind)
    if old:  # DNH and Daman and Diu are two source rows for one state id: sum the non-null values
        new = tuple(a if b is None else (b if a is None else a + b) for a, b in zip(old, new))
    res[sid][kind] = new
print("livestock", len(res), "unmatched", bad1)
rows = []
for sid in names:
    r = res.get(sid, {})
    rows.append({"key": sid, "name": names[sid], "state": sid, "milk_kt": r.get("me", (None, None))[0], "eggs_lakh": r.get("me", (None, None))[1],
                 "meat_kt": r.get("mw", (None, None))[0], "wool_kkg": r.get("mw", (None, None))[1]})
F = {"milk_kt": {"name": "Milk production 2023-24", "unit": "thousand tonnes", "type": "count", "description": "", "higher_is": "better"},
     "eggs_lakh": {"name": "Egg production 2023-24", "unit": "lakh numbers", "type": "count", "description": "", "higher_is": "better"},
     "meat_kt": {"name": "Meat production 2023-24", "unit": "thousand tonnes", "type": "count", "description": "", "higher_is": "better"},
     "wool_kkg": {"name": "Wool production 2023-24", "unit": "thousand kg", "type": "count", "description": "", "higher_is": "better"}}
meta = {"name": "State-wise production of milk, eggs, meat and wool (livestock products)", "source_org": "Department of Animal Husbandry & Dairying (printed in Agricultural Statistics at a Glance 2024-25, table 2.55)",
 "url": "https://nccd.gov.in/uploads/Agricultural_Statisitcs_at_a_Glance_2024_25_11da3cd37d.pdf", "landing_url": "https://desagri.gov.in/", "published": "2025", "reference_year": "2023-24", "resolution": "state",
 "license": "Government Open Data License - India (GODL)", "update_frequency": "annual", "kind": "official",
 "limitations": "This file holds livestock PRODUCTS, not animal counts. State totals of the 20th Livestock Census (2019) were not downloaded. Only the all-India census total is in the source. A dash in the source is null.",
 "method": "pdftotext -layout, row parsing, no unit change."}
write("livestock_state", meta, F, rows)
