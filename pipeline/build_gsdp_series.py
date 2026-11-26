"""Build data/normalized/gsdp_state_series.json: GSDP, NSDP, per-capita (constant and current prices), 2011-12 base, per state and year.
Inputs: raw/economy_series/mospi_nas_series/*.json (MoSPI), raw/economy_series/rbi_dbie_hub_series/*.html (RBI DBIE hub, extra columns *_rbi).
Run: ../.venv/bin/python build_gsdp_series.py
"""
import json, os, sys, collections
from common import *
import _hub

STATES, ALIAS = load_states()
NAME = {s["id"]: s["name"] for s in STATES}
M = os.path.join(RAW, "economy_series", "mospi_nas_series")
H = os.path.join(RAW, "economy_series", "rbi_dbie_hub_series")


def num(v):
    try:
        return None if v in (None, "", "NA", "-") else float(v) if "." in str(v) else int(v)
    except ValueError:
        return None


cells = collections.defaultdict(dict)   # (state, fy) -> {field: value}
unmatched = set()
for name, f_cur, f_con in [("gsdp", "gsdp_current", "gsdp_constant"), ("nsdp", "nsdp_current", "nsdp_constant"),
                           ("pc_nsdp", "pc_nsdp_current", "pc_nsdp_constant"), ("pc_gsdp", "pc_gsdp_current", "pc_gsdp_constant")]:
    for r in json.load(open(os.path.join(M, name + ".json")))["data"]:
        s = ALIAS.get(r["state"].lower())
        if not s:
            unmatched.add(r["state"]); continue
        cells[(s, r["year"])][f_cur] = num(r["current_price"])
        cells[(s, r["year"])][f_con] = num(r["constant_price"])

for slug, fld in [("net-state-domestic-product-state-wise-at-constant-prices", "nsdp_constant_rbi"),
                  ("net-state-domestic-product-state-wise-at-current-prices", "nsdp_current_rbi"),
                  ("per-capita-net-state-domestic-product-state-wise-at-constant-prices", "pc_nsdp_constant_rbi"),
                  ("per-capita-net-state-domestic-product-state-wise-at-current-prices", "pc_nsdp_current_rbi")]:
    d = _hub.load(os.path.join(H, slug + ".html"))
    assert d["baseYear"] == "2011-12", d["baseYear"]
    for st in d["states"]:
        s = ALIAS.get(st.lower())
        if not s:
            unmatched.add(st); continue
        for fy, v in zip(d["years"], d["data"][st]):
            cells[(s, fy)][fld] = num(v)

FIELDS = ["gsdp_constant", "gsdp_current", "nsdp_constant", "nsdp_current", "pc_nsdp_constant", "pc_nsdp_current",
          "pc_gsdp_constant", "pc_gsdp_current", "nsdp_constant_rbi", "nsdp_current_rbi", "pc_nsdp_constant_rbi", "pc_nsdp_current_rbi"]
rows = []
for (s, fy), c in sorted(cells.items(), key=lambda kv: (kv[0][0], kv[0][1])):
    y = int(fy[:4])
    row = {"key": f"{s}|{y}", "name": NAME[s], "state": s, "year": y, "fy": fy}
    for f in FIELDS:
        row[f] = c.get(f)
    row["flag"] = None
    if fy == "2025-26":
        row["flag"] = "latest year; only some states published; release type (advance or provisional) is not in the source"
    elif fy == "2024-25":
        row["flag"] = "recent year; the estimate can be advance or provisional and can change; the source gives no release type"
    if all(row[f] is None for f in FIELDS):
        continue
    rows.append(row)

# checks
def over(a, b):
    diffs = [(r["state"], r["fy"], r[a], r[b]) for r in rows if r[a] is not None and r[b] is not None and r[a] != r[b]]
    return diffs
print("unmatched names:", unmatched)
print("MoSPI vs RBI NSDP constant, cells that differ:", len(over("nsdp_constant", "nsdp_constant_rbi")), over("nsdp_constant", "nsdp_constant_rbi")[:5])
print("MoSPI vs RBI pc NSDP constant, cells that differ:", len(over("pc_nsdp_constant", "pc_nsdp_constant_rbi")), over("pc_nsdp_constant", "pc_nsdp_constant_rbi")[:5])
bad = [(r["state"], r["fy"]) for r in rows if r["gsdp_constant"] and r["nsdp_constant"] and r["nsdp_constant"] > r["gsdp_constant"]]
print("NSDP > GSDP (constant):", bad)
print("rows", len(rows), "states", len({r["state"] for r in rows}))
cov = collections.defaultdict(set)
for r in rows:
    if r["gsdp_constant"] is not None:
        cov[r["state"]].add(r["fy"])
allfy = sorted({r["fy"] for r in rows})
for s in NAME:
    miss = [fy for fy in allfy if fy not in cov[s]]
    if miss:
        print("GSDP constant missing", s, miss if len(miss) < 15 else "all")
    nm = [fy for fy in allfy if not any(r["state"] == s and r["fy"] == fy and (r["nsdp_constant"] is not None or r["nsdp_constant_rbi"] is not None) for r in rows)]
    if nm and len(nm) < 15:
        print("NSDP constant (either source) missing", s, nm)

F = lambda n, u, t, d, h="neutral": {"name": n, "unit": u, "type": t, "description": d, "higher_is": h}
meta = {
    "id": "gsdp_state_series", "name": "State GSDP and NSDP, 2011-12 base, series 2011-12 onward",
    "source_org": "Ministry of Statistics and Programme Implementation (MoSPI), National Accounts Statistics; RBI Handbook of Statistics on Indian States (via dbie.rbihub.in)",
    "url": "https://api.mospi.gov.in/api/nas/getNASData?base_year=2011-12&series=Current&frequency_code=Annually&indicator_code=23,24,25,31",
    "landing_url": "https://esankhyiki.mospi.gov.in/",
    "published": "see data/meta/gsdp_state_series.md", "reference_year": "2011-12 to 2025-26", "resolution": "state_year",
    "license": "Government of India open data", "update_frequency": "annual", "kind": "official",
    "limitations": "Base year 2011-12. Constant-price fields are at 2011-12 prices. The MoSPI API has no GSDP or NSDP for Assam, Haryana, Nagaland, Ladakh, Dadra and Nagar Haveli and Daman and Diu, and Lakshadweep; RBI fills NSDP (not GSDP) for Assam, Haryana, Nagaland in separate *_rbi fields. Latest years are advance estimates and later years can change. Telangana exists from 2014 but the source gives it for 2011-12 on (back-cast). Series before 2011-12 use another base (2004-05) and are not included.",
    "method": "Rows are (state, financial year). year = first calendar year of the financial year (2011 = 2011-12). Values are copied from the source without change. MoSPI fields and RBI fields stay in separate columns because the vintages differ.",
    "accessed": "2026-11-26",
    "redistributed_via": "RBI DBIE hub web pages for the *_rbi columns",
}
fields = {
    "year": F("Financial year (start)", "year", "value", "First calendar year of the financial year; see fy."),
    "fy": F("Financial year", "", "text", "For example 2011-12."),
    "gsdp_constant": F("GSDP, constant 2011-12 prices", "INR crore", "value", "Gross State Domestic Product at constant (2011-12) prices.", "better"),
    "gsdp_current": F("GSDP, current prices", "INR crore", "value", "Gross State Domestic Product at current prices.", "better"),
    "nsdp_constant": F("NSDP, constant 2011-12 prices", "INR crore", "value", "Net State Domestic Product at constant prices (MoSPI).", "better"),
    "nsdp_current": F("NSDP, current prices", "INR crore", "value", "Net State Domestic Product at current prices (MoSPI).", "better"),
    "pc_nsdp_constant": F("Per-capita NSDP, constant 2011-12 prices", "INR", "rate", "Per-capita NSDP at constant prices (MoSPI).", "better"),
    "pc_nsdp_current": F("Per-capita NSDP, current prices", "INR", "rate", "Per-capita NSDP at current prices (MoSPI).", "better"),
    "pc_gsdp_constant": F("Per-capita GSDP, constant 2011-12 prices", "INR", "rate", "Per-capita GSDP at constant prices (MoSPI).", "better"),
    "pc_gsdp_current": F("Per-capita GSDP, current prices", "INR", "rate", "Per-capita GSDP at current prices (MoSPI).", "better"),
    "nsdp_constant_rbi": F("NSDP, constant prices (RBI)", "INR crore", "value", "RBI DBIE handbook value; fills states that MoSPI does not give.", "better"),
    "nsdp_current_rbi": F("NSDP, current prices (RBI)", "INR crore", "value", "RBI DBIE handbook value.", "better"),
    "pc_nsdp_constant_rbi": F("Per-capita NSDP, constant prices (RBI)", "INR", "rate", "RBI DBIE handbook value.", "better"),
    "pc_nsdp_current_rbi": F("Per-capita NSDP, current prices (RBI)", "INR", "rate", "RBI DBIE handbook value.", "better"),
    "flag": F("Flag", "", "text", "Quality note for the row."),
}
write_json(os.path.join(DATA, "normalized", "gsdp_state_series.json"), {"meta": meta, "fields": fields, "rows": rows})
