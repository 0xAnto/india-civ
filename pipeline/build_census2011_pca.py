"""Correct and extend census2011_district / census2011_state with the official Primary Census
Abstract (PCA) district table (Total / Urban / Rural rows), as scraped from censusindia.gov.in by
github.com/pigshell/india-census-2011.

Why: the first mirror's `households` column sums to 330.8 million, which is the number of census
houses, not households (official PCA: 249,501,663). Its amenity counts are correct, so every
per-household share used the wrong denominator. This step:
  - renames the mirror column to `census_houses` and sets `households` = PCA No_HH,
  - recomputes every pct_hh_* share with PCA households as the denominator,
  - adds pop_0_6, the official literacy rate (literates / population aged 7+),
    urban population and urban share of population, and the PCA district area (TRU1, km²).
Run after build_census2011.py.
"""
import csv, os
from common import *

SRC = f"{RAW}/census_pigshell"
URL = "https://raw.githubusercontent.com/pigshell/india-census-2011/master/pca-full.csv"


def fetch():
    if not os.path.exists(f"{SRC}/pca-full.csv"):
        import requests
        os.makedirs(SRC, exist_ok=True)
        open(f"{SRC}/pca-full.csv", "wb").write(requests.get(URL, timeout=120).content)


def main():
    fetch()
    rows = list(csv.DictReader(open(f"{SRC}/pca-full.csv")))
    pca = {}
    for r in rows:
        if r["Level"] != "DISTRICT":
            continue
        k = str(int(r["District"]))
        pca.setdefault(k, {})[r["TRU"]] = r
    p = f"{DATA}/normalized/census2011_district.json"
    d = read_json(p)
    F = d["fields"]
    hh_fields = [f for f in F if f.startswith("pct_hh_")]
    if "census_houses" not in F:
        F["census_houses"] = dict(F["households"], name="Census houses (mirror column)", description="Mirror column named 'Households'. Its sum (330.8 million) equals the number of census houses, not households. Kept for reference only.")
    F["households"] = {"name": "Households", "unit": "households", "type": "count", "description": "Number of households, PCA No_HH (official).", "higher_is": "neutral"}
    F["pop_0_6"] = {"name": "Population aged 0–6", "unit": "persons", "type": "count", "description": "PCA P_06.", "higher_is": "neutral"}
    F["urban_population"] = {"name": "Urban population", "unit": "persons", "type": "count", "description": "PCA TOT_P of the Urban row.", "higher_is": "neutral"}
    F["area_km2"] = {"name": "Area", "unit": "km²", "type": "value", "description": "PCA district area (TRU1).", "higher_is": "neutral"}
    F["literacy_rate_7plus"] = {"name": "Literacy rate (official, age 7+)", "unit": "percent", "type": "rate", "description": "Literates / (population − population aged 0–6) × 100, the official Census definition.", "higher_is": "better"}
    F["literacy_rate_7plus_female"] = {"name": "Female literacy rate (age 7+)", "unit": "percent", "type": "rate", "description": "Female literates / (female population − females aged 0–6) × 100.", "higher_is": "better"}
    F["urban_share"] = {"name": "Urban population share", "unit": "percent", "type": "rate", "description": "Urban population / total population × 100 (PCA).", "higher_is": "neutral"}
    F["child_sex_ratio"] = {"name": "Child sex ratio (0–6)", "unit": "females per 1,000 males", "type": "rate", "description": "F_06 / M_06 × 1000 (PCA).", "higher_is": "neutral"}
    F["density"] = {"name": "Population density", "unit": "persons per km²", "type": "rate", "description": "Population / PCA area.", "higher_is": "neutral"}
    for f in hh_fields:
        F[f]["description"] = (F[f].get("description", "") + " Denominator: PCA households (No_HH).").strip()
    miss = 0
    for r in d["rows"]:
        t = pca.get(str(r["key"]), {})
        tot, urb = t.get("Total"), t.get("Urban")
        if not tot:
            miss += 1; continue
        if "census_houses" not in r:
            r["census_houses"] = r.get("households")
        hh = int(tot["No_HH"]); P = int(tot["TOT_P"]); P6 = int(tot["P_06"]); F6 = int(tot["F_06"]); M6 = int(tot["M_06"])
        r["households"] = hh; r["pop_0_6"] = P6
        r["urban_population"] = int(urb["TOT_P"]) if urb else 0
        r["area_km2"] = float(tot["TRU1"]) if tot.get("TRU1") else None
        r["literacy_rate_7plus"] = round(int(tot["P_LIT"]) / (P - P6) * 100, 2)
        r["literacy_rate_7plus_female"] = round(int(tot["F_LIT"]) / (int(tot["TOT_F"]) - F6) * 100, 2)
        r["urban_share"] = round(r["urban_population"] / P * 100, 2)
        r["child_sex_ratio"] = round(F6 / M6 * 1000, 1) if M6 else None
        r["density"] = round(P / r["area_km2"], 1) if r["area_km2"] else None
        for f in hh_fields:
            c = r.get(f[len("pct_"):])
            r[f] = round(c / hh * 100, 2) if c is not None and hh else None
    m = d["meta"]
    note = " PCA correction (pipeline/build_census2011_pca.py): households, 0–6 population, urban population, area and official literacy from the PCA district table scraped from censusindia.gov.in (github.com/pigshell/india-census-2011); every pct_hh_* share now uses PCA households."
    if "PCA correction" not in m.get("method", ""):
        m["method"] = m.get("method", "") + note
        m["redistributed_via"] = (m.get("redistributed_via") or "") + "; PCA: github.com/pigshell/india-census-2011 (pca-full.csv)"
    write_json(p, d, compact=False)
    print("districts patched", len(d["rows"]) - miss, "missing", miss)
    # states: sum counts, recompute rates
    ps = f"{DATA}/normalized/census2011_state.json"
    s = read_json(ps)
    for f in ("households", "pop_0_6", "urban_population", "area_km2", "census_houses", "literacy_rate_7plus", "literacy_rate_7plus_female", "urban_share", "child_sex_ratio", "density"):
        s["fields"][f] = F[f]
    by = {}
    for r in d["rows"]:
        by.setdefault(r["state"], []).append(r)
    female06 = {str(int(t["District"])): int(t["F_06"]) for t in rows if t["Level"] == "DISTRICT" and t["TRU"] == "Total"}
    for r in s["rows"]:
        ds = by.get(r["key"], [])
        if not ds:
            continue
        sm = lambda k: sum(x.get(k) or 0 for x in ds)
        r["census_houses"] = r.get("census_houses", r.get("households"))
        r["households"] = sm("households"); r["pop_0_6"] = sm("pop_0_6"); r["urban_population"] = sm("urban_population"); r["area_km2"] = round(sm("area_km2"), 1)
        P, P6 = sm("population"), sm("pop_0_6")
        r["literacy_rate_7plus"] = round(sm("literate") / (P - P6) * 100, 2)
        f6 = sum(female06.get(str(x["key"]), 0) for x in ds)
        r["literacy_rate_7plus_female"] = round(sm("literate_female") / (sm("female") - f6) * 100, 2)
        r["child_sex_ratio"] = round(f6 / (P6 - f6) * 1000, 1) if P6 > f6 else None
        r["urban_share"] = round(r["urban_population"] / P * 100, 2)
        r["density"] = round(P / r["area_km2"], 1) if r["area_km2"] else None
        for f in [f for f in F if f.startswith("pct_hh_")]:
            c = sm(f[len("pct_"):]); r[f] = round(c / r["households"] * 100, 2) if r["households"] else None
    if "PCA correction" not in s["meta"].get("method", ""):
        s["meta"]["method"] = s["meta"].get("method", "") + note
    write_json(ps, s, compact=False)
    nat_lit = sum(r["literate"] for r in d["rows"]) / (sum(r["population"] for r in d["rows"]) - sum(r["pop_0_6"] for r in d["rows"])) * 100
    nat_urb = sum(r["urban_population"] for r in d["rows"]) / sum(r["population"] for r in d["rows"]) * 100
    assert 72.9 < nat_lit < 73.1, nat_lit      # official 2011 literacy rate: 72.98 %
    assert 31.0 < nat_urb < 31.3, nat_urb      # official urban share: 31.14 %
    print(f"check: national literacy {nat_lit:.2f}% (official 72.98), urban {nat_urb:.2f}% (official 31.14)")


if __name__ == "__main__":
    main()
