"""Build data/normalized/census_state_series.json (state/UT, census years 1901-2011).
Inputs:
  raw/census_series/a2_xlsx/        Census 2011 Table A-2 (population, males, females; 2011 boundaries)
  raw/census_series/es_pages/page621.html   Economic Survey 2021-22, Table 8.5 (literacy rate, 1951-2011)
  data/normalized/census2011_district.json  2011 district counts (urban population, literacy, children 0-6)
  URBAN_TABLE below: urban share 1991, 2001, 2011, transcribed by hand from the image of
      MoSPI "Selected Socio-Economic Statistics India 2017", Table 1.7 (PDF page 20).
Run: ../.venv/bin/python build_census_state_series.py
"""
import re, os, html, collections
from common import *
import build_census_series as B

STATES, ALIAS = load_states()
SID = [s["id"] for s in STATES]
SC2ID = {s["lgd_code"]: s["id"] for s in STATES}
SC2ID.update({"1": "JK", "28": "AP", "25": "DH", "26": "DH"})
YEARS = B.SLOTS

# MoSPI SSES 2017 Table 1.7: percent urban, 1991 / 2001 / 2011. States of the time (AP includes Telangana, JK includes Ladakh).
URBAN_TABLE = {
    "Andaman & Nicobar Islands": (26.71, 32.63, 37.7), "Andhra Pradesh": (26.89, 27.3, 33.36),
    "Arunachal Pradesh": (12.8, 20.75, 22.94), "Assam": (11.1, 12.9, 14.1), "Bihar": (13.14, 10.46, 11.29),
    "Chandigarh": (89.69, 89.77, 97.25), "Chhattisgarh": (17.4, 20.09, 23.24),
    "Dadra & Nagar Haveli": (8.47, 22.89, 46.72), "Daman & Diu": (46.8, 36.25, 75.17), "Delhi": (89.93, 93.18, 97.5),
    "Goa": (41.01, 49.76, 62.17), "Gujarat": (34.49, 37.36, 42.6), "Haryana": (24.63, 28.92, 34.88),
    "Himachal Pradesh": (8.69, 9.8, 10.03), "Jammu & Kashmir": (22.89, 24.81, 27.38), "Jharkhand": (21.25, 22.24, 24.05),
    "Karnataka": (30.92, 33.99, 38.67), "Kerala": (26.39, 25.96, 47.7), "Lakshadweep": (56.31, 44.46, 78.07),
    "Madhya Pradesh": (23.18, 26.46, 27.63), "Maharashtra": (38.69, 42.43, 45.22), "Manipur": (27.52, 26.58, 29.21),
    "Meghalaya": (18.6, 19.58, 20.07), "Mizoram": (46.1, 49.63, 52.11), "Nagaland": (17.21, 17.23, 28.86),
    "Odisha": (13.38, 14.99, 16.69), "Puducherry": (64.0, 66.57, 68.33), "Punjab": (29.55, 33.92, 37.48),
    "Rajasthan": (22.88, 23.39, 24.87), "Sikkim": (9.1, 11.07, 25.15), "Tamil Nadu": (34.15, 44.04, 48.4),
    "Tripura": (15.3, 17.06, 26.17), "Uttar Pradesh": (19.84, 20.78, 22.27), "Uttrakhand": (22.97, 25.67, 30.23),
    "West Bengal": (27.48, 27.97, 31.87),
}
# States whose pre-2011 boundary differs from the present boundary. Urban and literacy tables stay null for them before 2011.
SPLIT = {"AP", "TG", "JK", "LA", "DH"}
ES_ALIAS = {"a & n islands": "AN", "d & n haveli": "DH_N", "daman & diu": "DH_D", "uttrakhand": "UT"}


def sid(name):
    n = re.sub(r"\s+[a-z]$", "", name.strip().lower())
    return ES_ALIAS.get(n) or ALIAS.get(n)


def parse_literacy():
    t = open(os.path.join(RAW, "census_series", "es_pages", "page621.html"), encoding="utf-8-sig").read()
    t = html.unescape(re.sub(r"<[^>]*>", "\n", t))
    out = {}
    for line in t.splitlines():
        m = re.fullmatch(r"\s*([A-Za-z&\. ]+?)\s+((?:(?:na|\d+\.\d)\s+){6}(?:na|\d+\.\d))\s*", line)
        if not m or m.group(1).startswith("All India"):
            continue
        s = sid(m.group(1))
        assert s, m.group(1)
        out[s] = [None if v == "na" else float(v) for v in m.group(2).split()]
    return out


def main():
    rows_d = read_json(os.path.join(DATA, "normalized", "census_district_series.json"))["rows"]
    c11 = read_json(os.path.join(DATA, "normalized", "census2011_district.json"))["rows"]
    lit = parse_literacy()
    # official state rows of Table A-2
    off = {}
    for sc, units in B.parse_file_all().items():
        if sc == 0:
            continue
        u = [x for x in units if x["dcode"] == 0][0]
        off[sc] = u["years"]
    # district sums
    dsum = collections.defaultdict(lambda: collections.defaultdict(lambda: {"n": 0, "pop": 0, "male": 0, "female": 0, "sexn": 0}))
    ndist = collections.Counter(r["state"] for r in rows_d if r["year"] == 2011)
    for r in rows_d:
        if r["population"] is None:
            continue
        a = dsum[r["state"]][r["year"]]
        a["n"] += 1; a["pop"] += r["population"]
        if r["male"] is not None and r["female"] is not None:
            a["sexn"] += 1; a["male"] += r["male"]; a["female"] += r["female"]

    # 2011 derived values from district counts
    d11 = collections.defaultdict(lambda: collections.Counter())
    for r in c11:
        c = d11[r["state"]]
        c["pop"] += r["population"]; c["urban"] += r["urban_population"]
        c["lit"] += r["literate"]; c["p06"] += r["pop_0_6"]
    urban_t = {sid(k): v for k, v in URBAN_TABLE.items()}
    checks = []
    rows = []
    for st in SID:
        for y in YEARS:
            row = {"key": f"{st}|{y}", "name": next(s["name"] for s in STATES if s["id"] == st), "state": st, "year": y,
                   "year_actual": None, "population": None, "male": None, "female": None, "sex_ratio": None,
                   "population_basis": None, "urban_population": None, "urban_share": None, "urban_basis": None,
                   "literacy_rate": None, "literacy_age_basis": None, "literacy_basis": None, "flag": None}
            sc = next((k for k, v in SC2ID.items() if v == st and k != "25" and k != "26"), None)
            # population
            if st in ("DH",):
                a, b = off[25].get(y), off[26].get(y)
                if a and b and a["population"] is not None and b["population"] is not None:
                    row["population"] = a["population"] + b["population"]
                    if a["male"] is not None and b["male"] is not None:
                        row["male"], row["female"] = a["male"] + b["male"], a["female"] + b["female"]
                    row["population_basis"] = "A-2 rows of Daman & Diu + Dadra & Nagar Haveli (sum)"
                    row["year_actual"] = a["year_actual"] or b["year_actual"]
            elif st in ("AP", "TG", "JK", "LA"):
                d = dsum[st].get(y)
                if d and d["n"] == ndist[st]:
                    row["population"] = d["pop"]; row["population_basis"] = "A-2 district sum (all districts present)"
                    if d["sexn"] == d["n"]:
                        row["male"], row["female"] = d["male"], d["female"]
            else:
                o = off[int(sc)].get(y)
                if o:
                    row["population"], row["male"], row["female"] = o["population"], o["male"], o["female"]
                    row["year_actual"] = o["year_actual"]
                    row["population_basis"] = "A-2 state row"
                    # check vs district sums
                    d = dsum[st].get(y)
                    if d and d["n"] == ndist[st] and o["population"] is not None:
                        checks.append((st, y, o["population"] - d["pop"]))
            if row["male"] is not None and row["female"] is not None and row["male"] > 0:
                row["sex_ratio"] = round(1000 * row["female"] / row["male"])
            if y == 1981 and st == "AS":
                row["flag"] = "1981 census not held in Assam; Census state value is interpolated"
            if y == 1901 and st == "MP":
                row["flag"] = "state male/female for 1901 are estimates in the Census table"
            if y == 1948 or row["year_actual"] == 1948:
                pass
            # urban share
            if y == 2011 and st in d11:
                c = d11[st]
                row["urban_population"] = c["urban"]
                row["urban_share"] = round(100 * c["urban"] / c["pop"], 2)
                row["urban_basis"] = "2011 district counts (census2011_district), present boundaries"
                if st in urban_t:
                    checks.append(("urban2011", st, row["urban_share"], urban_t[st][2]))
            elif y in (1991, 2001) and st in urban_t and st not in SPLIT:
                row["urban_share"] = urban_t[st][(1991, 2001).index(y)]
                row["urban_basis"] = "MoSPI SSES 2017 Table 1.7 (ORGI), boundaries of the census year"
                if st == "AS" or st == "JK":
                    pass
            # literacy
            if y == 2011 and st in d11:
                c = d11[st]
                row["literacy_rate"] = round(100 * c["lit"] / (c["pop"] - c["p06"]), 2)
                row["literacy_age_basis"] = "7+"
                row["literacy_basis"] = "2011 district counts: literate / (population - age 0-6), present boundaries"
                if st in lit:
                    checks.append(("lit2011", st, row["literacy_rate"], lit[st][6]))
            elif y in (1951, 1961, 1971, 1981, 1991, 2001) and st in lit and st not in SPLIT:
                v = lit[st][(1951, 1961, 1971, 1981, 1991, 2001).index(y)]
                if v is not None:
                    row["literacy_rate"] = v
                    row["literacy_age_basis"] = "5+" if y <= 1971 else "7+"
                    row["literacy_basis"] = "Economic Survey 2021-22 Table 8.5 (ORGI), boundaries of the census year"
                    if y == 1951 and st == "WB":
                        row["literacy_age_basis"] = "all ages (West Bengal 1951 includes age 0-4)"
                    if y == 1951 and st in ("CT", "MP", "MN"):
                        row["flag"] = "1951 literacy rate is based on a sample population"
            rows.append(row)
    return rows, checks, lit


if __name__ == "__main__":
    rows, checks, lit = main()
    bad = [c for c in checks if (c[0] != "urban2011" and c[0] != "lit2011" and c[2] != 0)]
    print("state-vs-district population mismatches:", bad)
    for c in checks:
        if c[0] == "urban2011" and abs(c[2] - c[3]) > 0.06: print("URBAN2011 differs", c)
        if c[0] == "lit2011" and abs(c[2] - c[3]) > 0.06: print("LIT2011 differs", c)
    tot = collections.Counter()
    for r in rows:
        if r["population"] is not None:
            tot[r["year"]] += r["population"]
    print("national sums", dict(tot))
    print("rows", len(rows))
    meta = {
        "id": "census_state_series",
        "name": "Census of India - state and UT series 1901-2011 (population, sex ratio, urban share, literacy)",
        "source_org": "Office of the Registrar General & Census Commissioner, India (Census of India); Ministry of Finance (Economic Survey 2021-22); MoSPI (SSES 2017)",
        "url": "https://censusindia.gov.in/nada/index.php/catalog/43333 (Table A-2, one catalog page per state)",
        "landing_url": "https://censusindia.gov.in/nada/index.php/catalog/43333",
        "published": "2013 (A-2); 2022 (Economic Survey); 2017 (SSES)",
        "reference_year": "1901-2011",
        "resolution": "state_year",
        "license": "Government of India open data",
        "update_frequency": "decennial",
        "kind": "official",
        "limitations": "Population, males and females are on 2011 boundaries (Table A-2). Urban share and literacy for 1951-2001 are on the state boundaries of each census year (states formed in 2000 are recast by the Census). They stay null for AP, TG, JK, LA and DH before 2011 because these boundaries changed. Urban share exists for 1991, 2001 and 2011 only. 2011 urban share and literacy come from district counts on present boundaries. Literacy age basis changes: 1951-1971 age 5+, 1981 onward age 7+. Assam 1981 and J&K 1991 values in the Census are interpolated by the Census. No value is estimated by this pipeline.",
        "method": "Population: official state row of Table A-2, except AP, TG, JK, LA (sum of districts when every district has a value) and DH (sum of the two UT rows). Sex ratio = females per 1000 males from the same rows. Urban share 2011 = urban population / population from census2011_district. Literacy 2011 = literate / (population - age 0-6) from census2011_district. Literacy 1951-2001 and urban share 1991-2001: published tables as listed in the coverage note.",
        "accessed": "2026-11-26",
        "redistributed_via": "Economic Survey 2021-22 and SSES 2017 are Government of India publications that republish Census tables.",
    }
    F = lambda n, u, t, d, h="neutral": {"name": n, "unit": u, "type": t, "description": d, "higher_is": h}
    fields = {
        "year": F("Census year", "year", "value", "Nominal census year."),
        "year_actual": F("Actual census year", "year", "value", "Set when the census was in another year (Puducherry 1948; Goa, Daman, Diu 1900, 1910, 1940, 1950, 1960; DNH 1962)."),
        "population": F("Population", "persons", "count", "Population on 2011 boundaries."),
        "male": F("Male population", "persons", "count", "Males."),
        "female": F("Female population", "persons", "count", "Females."),
        "sex_ratio": F("Sex ratio", "females per 1000 males", "rate", "Females per 1000 males.", "better"),
        "population_basis": F("Population basis", "", "text", "Which rows give the population."),
        "urban_population": F("Urban population", "persons", "count", "2011 only."),
        "urban_share": F("Urban share", "percent", "rate", "Urban population as percent of total population."),
        "urban_basis": F("Urban basis", "", "text", "Source and boundary of the urban share."),
        "literacy_rate": F("Literacy rate", "percent", "rate", "Literate persons as percent of the population in the age basis.", "better"),
        "literacy_age_basis": F("Literacy age basis", "", "text", "5+ (1951-1971), 7+ (1981 onward), with exceptions."),
        "literacy_basis": F("Literacy source", "", "text", "Source and boundary of the literacy rate."),
        "flag": F("Flag", "", "text", "Known quality note for the row."),
    }
    write_json(os.path.join(DATA, "normalized", "census_state_series.json"), {"meta": meta, "fields": fields, "rows": rows})
    for f in ("population", "sex_ratio", "urban_share", "literacy_rate"):
        miss = collections.defaultdict(list)
        for r in rows:
            if r[f] is None and r["year"] >= (1951 if f in ("urban_share", "literacy_rate") else 1951):
                miss[r["state"]].append(r["year"])
        print(f, "non-null", sum(r[f] is not None for r in rows), {k: v for k, v in miss.items()})
