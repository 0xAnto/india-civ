"""Build census_district_series.json and the population part of census_state_series.json.
Input: raw/census_series/a2_xlsx/NN.xls(x), Census 2011 Table A-2 (one file per state, NN = state code).
Output: data/normalized/census_district_series.json (one row per district and census year).
Run: ../.venv/bin/python build_census_series.py
"""
import re, csv, os, glob, collections
import openpyxl, xlrd
from common import *

A2 = os.path.join(RAW, "census_series", "a2_xlsx")
SLOTS = [1901 + 10 * i for i in range(12)]


def sheet_rows(path):
    if path.endswith("xlsx"):
        return [list(r) for r in openpyxl.load_workbook(path, data_only=True).worksheets[0].iter_rows(values_only=True)]
    sh = xlrd.open_workbook(path).sheet_by_index(0)
    return [sh.row_values(i) for i in range(sh.nrows)]


def num(v):
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return int(round(v))
    return None


def parse_file(path):
    """Return list of units: dict(scode, dcode, name, years{slot: {...}})."""
    units, cur = [], None
    for r in sheet_rows(path):
        r = list(r) + [None] * 10
        ym = re.fullmatch(r"[^\w]*(1[89]\d\d|20\d\d)\.?0?[^\w]*", str(r[3]))
        if not ym:
            continue
        dc = str(r[1]).strip() if r[1] not in (None, "") else ""
        if dc:
            try:
                float(dc)
            except ValueError:
                continue
            cur = {"dcode": int(float(dc)), "name": str(r[2]).strip(), "years": {}}
            units.append(cur)
        if cur is None:
            continue
        y = int(ym.group(1))
        slot = 1901 + 10 * round((y - 1901) / 10)
        raw_pop = r[4]
        cur["years"][slot] = {
            "year_actual": y if y != slot else None,
            "population": num(raw_pop), "male": num(r[7]), "female": num(r[8]),
            "raw": None if num(raw_pop) is not None else str(raw_pop).strip(),
        }
    return units


def parse_file_all():
    return {int(os.path.basename(f)[:2]): parse_file(f) for f in sorted(glob.glob(os.path.join(A2, "*")))}


def main():
    dist = list(csv.DictReader(open(os.path.join(DATA, "ref", "districts2011.csv"), encoding="utf-8")))
    by_code = {int(d["censuscode"]): d for d in dist}
    by_sd = {(int(d["st_cen_cd"]), int(d["dt_cen_cd"])): int(d["censuscode"]) for d in dist}
    c11 = {int(r["key"]): r for r in read_json(os.path.join(DATA, "normalized", "census2011_district.json"))["rows"]}

    all_units = {}
    for f in sorted(glob.glob(os.path.join(A2, "*"))):
        sc = int(os.path.basename(f)[:2])
        all_units[sc] = parse_file(f)

    rows, unmatched, seen = [], [], set()
    state_units = {}
    for sc, units in all_units.items():
        for u in units:
            if sc == 0:
                continue
            if u["dcode"] == 0:
                state_units[sc] = u
                continue
            cc = u["dcode"] if (u["dcode"] in by_code and by_code[u["dcode"]]["state"] and int(by_code[u["dcode"]]["st_cen_cd"]) == sc) else by_sd.get((sc, u["dcode"]))
            if cc is None or cc not in c11 or cc in seen:
                unmatched.append((sc, u["dcode"], u["name"])); continue
            seen.add(cc)
            st = c11[cc]["state"]
            for slot in SLOTS:
                v = u["years"].get(slot)
                if v is None:
                    continue
                flag = None
                if v["population"] is None:
                    flag = "source value is '%s'" % v["raw"]
                if sc == 18 and slot == 1981:
                    flag = "1981 census not held in Assam; source has no district value ('---')"
                rows.append({"key": f"{cc}|{slot}", "name": c11[cc]["name"], "state": st, "censuscode": cc, "year": slot,
                             "year_actual": v["year_actual"], "population": v["population"], "male": v["male"],
                             "female": v["female"], "flag": flag})
    return rows, unmatched, state_units, all_units, c11, seen


def write_district(rows):
    meta = {
        "id": "census_district_series",
        "name": "Census of India - district population 1901-2011 on 2011 district boundaries (Table A-2)",
        "source_org": "Office of the Registrar General & Census Commissioner, India (Census of India 2011)",
        "url": "https://censusindia.gov.in/nada/index.php/catalog/43333 (India) to /43368 (one catalog page per state; the build reads the xlsx/xls file linked on each page)",
        "landing_url": "https://censusindia.gov.in/nada/index.php/catalog/43333",
        "published": "2013",
        "reference_year": "1901-2011",
        "resolution": "district2011_year",
        "license": "Government of India open data (Census of India)",
        "update_frequency": "decennial",
        "kind": "official",
        "limitations": "Past populations are adjusted by the Census to the 2011 district boundaries. Some cells are N.A. in the source (new districts without past data) and stay null here. The 1981 census was not held in Assam: the source has no district value for 1981 and an interpolated state value. Goa, Daman, Diu, Dadra and Nagar Haveli and Puducherry used other actual census years in some decades: column year_actual holds the actual year. Census of 1951 in Puducherry was in 1948. No value is interpolated or estimated by this pipeline.",
        "method": "build_census_series.py reads column Persons/Males/Females of each state file of Table A-2. Row key = '<censuscode>|<year>'. A district joins to data/ref/districts2011.csv by the district code of the file (equal to censuscode); state = state id from data/normalized/census2011_district.json. The year slot is the nominal decade year (1901 + 10 n). year_actual is set when the source year differs.",
        "accessed": "2026-11-26",
    }
    fields = {
        "year": {"name": "Census year (nominal decade slot)", "unit": "year", "type": "value", "description": "Nominal census year. See year_actual for exceptions.", "higher_is": "neutral"},
        "year_actual": {"name": "Actual census year if different", "unit": "year", "type": "value", "description": "Set only when the census was held in another year (for example 1948 for Puducherry).", "higher_is": "neutral"},
        "censuscode": {"name": "Census 2011 district code", "unit": "code", "type": "value", "description": "Join key to data/ref/districts2011.csv.", "higher_is": "neutral"},
        "population": {"name": "Population", "unit": "persons", "type": "count", "description": "Total population on 2011 district boundaries.", "higher_is": "neutral"},
        "male": {"name": "Male population", "unit": "persons", "type": "count", "description": "Males. Null when the source has N.A.", "higher_is": "neutral"},
        "female": {"name": "Female population", "unit": "persons", "type": "count", "description": "Females. Null when the source has N.A.", "higher_is": "neutral"},
        "flag": {"name": "Source flag", "unit": "", "type": "text", "description": "Reason for a null population.", "higher_is": "neutral"},
    }
    write_json(os.path.join(DATA, "normalized", "census_district_series.json"), {"meta": meta, "fields": fields, "rows": rows})


if __name__ == "__main__":
    rows, unmatched, state_units, all_units, c11, seen = main()
    print("rows", len(rows), "districts", len(seen), "unmatched", unmatched)
    print("missing codes", sorted(set(c11) - seen))
    tot = collections.Counter()
    for r in rows:
        if r["population"] is not None:
            tot[r["year"]] += r["population"]
    ind = all_units[0][0]["years"]
    for y in SLOTS:
        print(y, "district sum", tot[y], "India row", ind[y]["population"], "diff", ind[y]["population"] - tot[y])
    write_district(rows)
