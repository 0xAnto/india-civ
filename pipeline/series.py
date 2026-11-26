"""Time-series lenses ("Change over time").

A series lens has one hex array per year. Each year goes through the normal aggregation
(Ctx.hex_values) on its own: the pipeline never mixes years inside one array.
The lens file keeps the newest year as `values` (so tables, checks and tooltips work as for
any lens) and adds `years` and `series`. The colour domain spans all years, so change shows.

A change lens is a normal one-year lens: the value per unit is the change between two years,
computed on the source units before aggregation.
"""
import numpy as np
from common import *

# id, name, emoji, source, ramp, unit, scale, higher_is, description
# source: (dataset, field, how) for *_year datasets, or (dataset, "series:<key>", how) for a state dataset with a `series` dict.
SERIES = [
    ("ts_pop_density", "Population density over time", "👥", ("census_district_series", "population", "count", ["flag"]), "people", "people / km²", "log", "neutral",
     "Census population of each district for each census year, on 2011 district boundaries (Census 2011 Table A-2), divided by the 2011 district area."),
    ("ts_urban", "Urbanisation over time", "🏙️", ("census_state_series", "urban_share", None, ["urban_basis"]), "people", "% of population", "linear", "neutral",
     "Urban population as a share of state population, census years, on present state boundaries. State level."),
    ("ts_literacy", "Literacy over time", "📖", ("census_state_series", "literacy_rate", None, ["literacy_age_basis", "literacy_basis"]), "knowledge", "%", "linear", "better",
     "Census literacy rate by state. The definition changes: 1951–1971 use the population aged 5+, 1981 onwards the population aged 7+. Values before 2011 are on the state boundaries of the census year, so states that changed shape (for example Kerala before 1956) do not compare exactly. State level."),
    ("ts_sex_ratio", "Sex ratio over time", "⚖️", ("census_state_series", "sex_ratio", None, []), "diverge", "females per 1,000 males", "linear", "neutral",
     "Census females per 1,000 males by state, census years. State level."),
    ("ts_income", "Income per person over time", "💰", ("gsdp_state", "series:pc_nsdp_constant", None, []), "wealth", "₹ per person, 2011-12 prices", "log", "neutral",
     "Per-capita Net State Domestic Product at constant 2011-12 prices (MoSPI), every year from 2011-12. Constant prices remove inflation, so the years compare. State level."),
]

QUICK = {"ts_pop_density": {"quick": True, "short": "Since 1901"}}  # one time lens on the dock, so the slider is easy to find

# id, name, emoji, source, (year0, year1), mode, ramp, unit, higher_is, description
CHANGES = [
    ("chg_pop_1951_2011", "Population growth 1951–2011", "📈", ("census_district_series", "population"), (1951, 2011), "ratio", "people", "× the 1951 population", "neutral",
     "Census 2011 population divided by the 1951 population of the same area (2011 district boundaries, Census Table A-2)."),
    ("chg_pop_2001_2011", "Population growth 2001–2011", "📈", ("census_district_series", "population"), (2001, 2011), "pct", "diverge", "% in ten years", "neutral",
     "Decadal population growth 2001–2011 on 2011 district boundaries (Census Table A-2). National value 17.7%."),
    ("chg_income_growth", "Real income growth since 2011-12", "🚀", ("gsdp_state", "series:pc_nsdp_constant"), ("2011-12", "2024-25"), "cagr", "wealth", "% a year", "neutral",
     "Compound annual growth of per-capita NSDP at constant 2011-12 prices, 2011-12 to 2024-25 (or the latest year a state reports). State level."),
]


def _years_rows(ctx, ds, field):
    """{year: [rows with a unit key and the value]} and the base resolution."""
    d = ctx.ds[ds]; res = d["meta"]["resolution"]
    out = {}
    if field.startswith("series:"):
        key = field.split(":", 1)[1]
        for r in d["rows"]:
            for y, v in ((r.get("series") or {}).get(key) or {}).items():
                out.setdefault(y, []).append({"key": r["key"], "state": r.get("state"), "v": v})
        return out, res
    base = res.replace("_year", "")
    area = {}
    if base == "district2011" and "census2011_district" in ctx.ds:
        area = {str(r["key"]): r.get("area_km2") for r in ctx.ds["census2011_district"]["rows"]}
    for r in d["rows"]:
        k = str(r.get("censuscode") if base == "district2011" else r.get("state"))
        out.setdefault(r["year"], []).append({"key": k, "state": r.get("state"), "v": r.get(field), "area_km2": area.get(k)})
    return out, base


def _hex(ctx, rows, res, how):
    ctx.ds["_tmp"] = {"meta": {"resolution": res}, "fields": {"v": {"type": how or "rate"}}, "rows": rows}
    try:
        return ctx.hex_values("_tmp", "v", how)
    finally:
        del ctx.ds["_tmp"]


def _meta_of(ctx, ds):
    m = ctx.ds[ds]["meta"]
    return m.get("kind", "official"), m["resolution"].replace("_year", "")


def build(ctx, RAMPS, stats, rnd):
    lenses = []
    for lid, name, emoji, (ds, field, how, basis), ramp, unit, scale, hib, desc in SERIES:
        if ds not in ctx.ds:
            print("skip series lens (no data)", lid); continue
        by_year, res = _years_rows(ctx, ds, field)
        years = sorted(by_year, key=lambda y: str(y))
        arrs = [_hex(ctx, [r for r in by_year[y] if r["v"] is not None], res, how) for y in years]
        keep = [k for k, a in enumerate(arrs) if sum(v is not None for v in a) >= 50]
        if len(keep) < 2:
            print("skip series lens (fewer than 2 usable years)", lid); continue
        years = [years[k] for k in keep]; arrs = [arrs[k] for k in keep]
        st = stats([v for a in arrs for v in a])
        if scale == "log" and st["p2"] is not None and st["p2"] <= 0:
            pos = [v for a in arrs for v in a if v and v > 0]; st["p2"] = rnd(float(np.percentile(pos, 2)))
        kind, _ = _meta_of(ctx, ds)
        n_admin = sum(1 for i in ctx.land if ctx.disputed[i] < 0)
        lenses.append({"id": lid, "group": "change", "name": name, "emoji": emoji, "ramp": RAMPS[ramp], "unit": unit, "scale": scale, "higher_is": hib,
                       "description": desc + " Colours use one scale for all years.", "source": ds, "kind": kind, "year": f"{years[0]}–{years[-1]}",
                       "resolution": res, "stats": st, "coverage": round(sum(v is not None for v in arrs[-1]) / n_admin, 3),
                       "series": {"years": [str(y) for y in years], "national": _national(ctx, *NATIONAL_FROM.get(ds, (ds,)), field, years, how), "notes": _notes(ctx, ds, field, basis, years)},
                       **({"domain": [800, 943, 1050]} if ramp == "diverge" else {}), **QUICK.get(lid, {})})
        write_json(f"{SITE_DATA}/lens/{lid}.json", {"values": [rnd(v) for v in arrs[-1]], "years": [str(y) for y in years], "series": [[rnd(v) for v in a] for a in arrs]})
    for lid, name, emoji, (ds, field), (y0, y1), mode, ramp, unit, hib, desc in CHANGES:
        if ds not in ctx.ds:
            print("skip change lens (no data)", lid); continue
        by_year, res = _years_rows(ctx, ds, field)
        a = {r["key"]: r for r in by_year.get(y0, [])}
        latest = {}  # for cagr: the latest year a unit reports, up to y1
        ys = sorted(by_year, key=str)
        rows = []
        for r1 in by_year.get(y1, []) if mode != "cagr" else []:
            r0 = a.get(r1["key"])
            if r0 and r0["v"] and r1["v"] is not None:
                v = r1["v"] / r0["v"] if mode == "ratio" else (r1["v"] / r0["v"] - 1) * 100
                rows.append({"key": r1["key"], "state": r1["state"], "v": v})
        if mode == "cagr":
            for k, r0 in a.items():
                last = max((y for y in ys if str(y) <= str(y1) and any(r["key"] == k and r["v"] for r in by_year[y])), key=str, default=None)
                if not last or last == y0 or not r0["v"]:
                    continue
                v1 = next(r["v"] for r in by_year[last] if r["key"] == k)
                n = int(str(last)[:4]) - int(str(y0)[:4])
                rows.append({"key": k, "state": r0["state"], "v": ((v1 / r0["v"]) ** (1 / n) - 1) * 100})
        vals = _hex(ctx, rows, res, None)
        st = stats(vals)
        if not st or st["n"] < 50:
            print("skip change lens (too few values)", lid); continue
        kind, _ = _meta_of(ctx, ds)
        dom = {"pct": [0, 17.7, 40]}.get(mode) if ramp == "diverge" else None
        lenses.append({"id": lid, "group": "change", "name": name, "emoji": emoji, "ramp": RAMPS[ramp], "unit": unit, "scale": "linear", "higher_is": hib,
                       "description": desc, "source": ds, "kind": kind, "year": f"{y0}–{y1}", "resolution": res, "stats": st,
                       "coverage": round(st["n"] / sum(1 for i in ctx.land if ctx.disputed[i] < 0), 3), **({"domain": dom} if dom else {})})
        write_json(f"{SITE_DATA}/lens/{lid}.json", {"values": [rnd(v) for v in vals]})
    return lenses


NATIONAL_FROM = {"census_district_series": ("census_state_series",)}  # state rows add up to the official India totals (checked in the coverage note)


def _national(ctx, ds, field, years, how):
    """India value per year: the dataset's own India row, or for counts the sum of the units that report.
    A sum is given only when at least 95% of the units report; `cov` says how many did."""
    by_year, _ = _years_rows(ctx, ds, field)
    by_year = {str(k): v for k, v in by_year.items()}
    vals, cov = [], []
    for y in map(str, years):
        rows = by_year.get(y, [])
        nat = next((r["v"] for r in rows if r["key"] in ("IN", "India")), None)
        n = len([r for r in rows if r["v"] is not None])
        if nat is None and how == "count" and n >= 0.95 * len(rows):
            nat = sum(r["v"] for r in rows if r["v"] is not None)
        vals.append(nat); cov.append(f"{n} of {len(rows)}" if nat is not None and n < len(rows) else None)
    if not any(v is not None for v in vals):
        return None
    return {"values": vals, "coverage": cov, "label": "India population (sum of states)" if how == "count" else "India"}


def _notes(ctx, ds, field, basis, years):
    """Per-year text from the dataset's basis and flag columns, for rows that have a value."""
    out = {}
    for y in years:
        seen = collections.Counter()
        for r in ctx.ds[ds]["rows"]:
            if r.get("year") == y and r.get(field) is not None:
                for b in basis:
                    if r.get(b):
                        seen[f"{r.get('state')}: {r[b]}" if b == "flag" else r[b]] += 1
        if seen:
            out[str(y)] = "; ".join(t for t, _ in seen.most_common(3))
    return out or None


import collections  # noqa: E402
