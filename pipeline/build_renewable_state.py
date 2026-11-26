"""Build renewable_potential_state: MNRE installed capacity by state (31 Jan 2026) + NIWE wind potential at 150 m.
Run: .venv/bin/python -I pipeline/build_renewable_state.py   (needs raw/energy/b.html and res_b.html: pdftotext -bbox output of the two MNRE PDFs)"""
import re, sys, os, csv, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _resources_common import *
html = open(f"{ROOT}/raw/energy/b.html").read()
pages = html.split("<page ")[1:]
STATE_ORDER = ["Andhra Pradesh","Arunachal Pradesh","Assam","Bihar","Chhattisgarh","Goa","Gujarat","Haryana","Himachal Pradesh","Jammu & Kashmir","Jharkhand","Karnataka","Kerala","Ladakh","Madhya Pradesh","Maharashtra","Manipur","Meghalaya","Mizoram","Nagaland","Odisha","Punjab","Rajasthan","Sikkim","Tamil Nadu","Telangana","Tripura","Uttar Pradesh","Uttarakhand","West Bengal","Andaman & Nicobar Islands","Chandigarh","Dadra & Nagar Haveli and Daman & Diu","Delhi","Lakshadweep","Puducherry","Others"]
cols = {"small_hydro_mw": 140, "wind_mw": 193, "bio_mw": 430, "solar_mw": 682, "large_hydro_mw": 731, "total_mw": 781}
# values that the PDF splits over two text lines (decimal part on the next line); read from the text layout of the same PDF
FIX = {("Karnataka", "bio_mw"): 1917.05 + 0, ("Maharashtra", "bio_mw"): 2998.30, ("Tamil Nadu", "bio_mw"): 1046.62, ("Uttar Pradesh", "bio_mw"): 2310.39,
       ("Dadra & Nagar Haveli and Daman & Diu", "bio_mw"): 3.75, ("Dadra & Nagar Haveli and Daman & Diu", "solar_mw"): 134.90}
res = {}
for pi, pg in enumerate(pages):
    w = [(float(a), float(b), float(c), float(d), t) for a, b, c, d, t in re.findall(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>', pg)]
    for s in [x for x in w if x[2] < 30 and re.fullmatch(r"\d+", x[4])]:
        n = int(s[4]); r = {}
        for k, xm in cols.items():
            c = [x for x in w if abs(x[2] - xm) <= 4 and abs(x[1] - s[1]) < 6 and re.fullmatch(r"\d+\.\d\d", x[4])]
            r[k] = float(c[0][4]) if c else None
        res[STATE_ORDER[n - 1]] = r
# bio split values: Bio total for these four is a wrapped number. Check with the sum rule, else use the manual value.
for (st, k), v in FIX.items():
    res[st][k] = v
# State potential: table 7.1 of MNRE "Renewable Energy Statistics 2024-25" (MW), parsed from pdftotext -bbox of that PDF (page 45)
POT_STATES = [("Andhra","AP"),("Arunachal","AR"),("Assam","AS"),("Bihar","BR"),("Chhattisgarh","CT"),("Goa","GA"),("Gujarat","GJ"),("Haryana","HR"),("Himachal","HP"),("UT","JK"),("Ladakh","LA"),("Jharkhand","JH"),("Karnataka","KA"),("Kerala","KL"),("Madhya","MP"),("Maharashtra","MH"),("Manipur","MN"),("Meghalaya","ML"),("Mizoram","MZ"),("Nagaland","NL"),("Orissa","OR"),("Punjab","PB"),("Rajasthan","RJ"),("Sikkim","SK"),("Tamil","TN"),("Telangana","TG"),("Tripura","TR"),("Uttar","UP"),("Uttarakhand","UT"),("West","WB"),("Andaman","AN"),("Chandigarh","CH"),("Dadar","DH"),("Delhi","DL"),("Lakshadweep","LD"),("Pondicherry","PY"),("Others",None),("Total","TOTAL")]
POT_COLS = {"wind_potential_mw": 212, "small_hydro_potential_mw": 274, "biomass_potential_mw": 339, "bagasse_potential_mw": 411, "solar_potential_mw": 480, "large_hydro_potential_mw": 548.5}
rb = open(f"{ROOT}/raw/energy/res_b.html").read().split("<page ")[1:][44]
rw = [(float(a), float(b), float(c), float(d), t) for a, b, c, d, t in re.findall(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>', rb)]
starts = []
for tok, sid in POT_STATES:
    cand = [w for w in rw if w[0] < 50 and w[4] == tok and w[1] > 125 and (not starts or w[1] > starts[-1][1])]
    starts.append((sid, cand[0][1]))
pot = {}
for k, (sid, y0) in enumerate(starts):
    y1 = starts[k + 1][1] if k + 1 < len(starts) else 9999
    r = {}
    for col, xm in POT_COLS.items():
        c = [w for w in rw if abs(w[2] - xm) <= 3 and y0 - 2 <= w[1] < y1 - 2 and re.fullmatch(r"[\d.]+", w[4])]
        r[col] = float(c[0][4]) if c else None
    pot[sid] = r
for col in POT_COLS:
    ssum = sum((v[col] or 0) for k, v in pot.items() if k != "TOTAL")
    print("potential check", col, round(ssum, 1), pot["TOTAL"][col])
names = {x["id"]: x["name"] for x in csv.DictReader(open(f"{ROOT}/data/ref/states.csv"))}
byid = {}
for st, r in res.items():
    sid = state_id(st) if st != "Others" else None
    if not sid: continue
    chk = sum((r[k] or 0) for k in cols if k != "total_mw") - (r["total_mw"] or 0)
    if abs(chk) > 0.05: print("SUM CHECK FAIL", st, round(chk, 2), r)
    byid[sid] = r
rows = []
for sid, nm in names.items():
    r = byid.get(sid, {})
    rows.append({"key": sid, "name": nm, "state": sid, **{k: r.get(k) for k in cols},
                 **{k: pot.get(sid, {}).get(k) for k in POT_COLS}})
F = {"small_hydro_mw": ("Small hydro installed", "MW"), "wind_mw": ("Wind installed", "MW"), "bio_mw": ("Bio-power installed (biomass, bagasse, waste-to-energy)", "MW"),
     "solar_mw": ("Solar installed (ground, rooftop, hybrid, off-grid)", "MW"), "large_hydro_mw": ("Large hydro installed", "MW"), "total_mw": ("Total renewable installed (incl. large hydro)", "MW")}
F = {k: {"name": v[0], "unit": v[1], "type": "count", "description": "MNRE state-wise (location based) capacity as on 31.01.2026. Empty cells in the source are null.", "higher_is": "better"} for k, v in F.items()}
for k, lab in [("wind_potential_mw", "Wind potential at 150 m hub height (NIWE)"), ("small_hydro_potential_mw", "Small hydro potential (IIT Roorkee 2016)"), ("biomass_potential_mw", "Biomass power potential"), ("bagasse_potential_mw", "Bagasse cogeneration potential"), ("solar_potential_mw", "Ground-mounted solar PV potential (NISE, Sept 2025)"), ("large_hydro_potential_mw", "Large hydro potential (CEA exploitable capacity)")]:
    F[k] = {"name": lab, "unit": "MW", "type": "count", "description": "MNRE Renewable Energy Statistics 2024-25, table 7.1. Empty cell in the source is null.", "higher_is": "better"}
meta = {"name": "Installed renewable capacity by state (31 Jan 2026) and estimated RE potential by state", "source_org": "Ministry of New & Renewable Energy; National Institute of Wind Energy",
 "url": "https://cdnbbsr.s3waas.gov.in/s3716e1b8c6cd17b771da77391355749f3/uploads/2026/02/202602091660392380.pdf (capacity); https://cdnbbsr.s3waas.gov.in/s3716e1b8c6cd17b771da77391355749f3/uploads/2025/11/202511061627678782.pdf (potential)", "landing_url": "https://mnre.gov.in/en/physical-progress/", "published": "2026-02-09", "reference_year": "2026-01-31 (capacity); potential: wind NIWE 2023, solar NISE Sept 2025",
 "resolution": "state", "license": "Government Open Data License - India (GODL)", "update_frequency": "monthly", "kind": "official",
 "limitations": "Potential comes from a second file: MNRE Renewable Energy Statistics 2024-25, table 7.1 (https://cdnbbsr.s3waas.gov.in/s3716e1b8c6cd17b771da77391355749f3/uploads/2025/11/202511061627678782.pdf). Potential is a theoretical estimate, not a build plan. Solar potential is ground-mounted PV from NISE (Sept 2025), much larger than the older 748 GW figure. The Others rows of both tables are dropped. Empty source cells are null.",
 "method": "pdftotext -bbox, then columns assigned by x position of right-aligned numbers. Sum check: components equal total within 0.05 MW. Four numbers that the PDF wraps over two lines are typed from the text layout."}
write("renewable_potential_state", meta, F, rows)
print("rows", len(rows), "with data", len(byid))
