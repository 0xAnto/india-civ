"""Hidden strengths: districts and states that do better than their conditions predict.

Each model fits an ordinary least-squares line: outcome ~ conditions (all standardised).
The residual, divided by the residual standard deviation, is the score:
+1.5 means "1.5 standard deviations better than places with the same conditions".
The sign is flipped for outcomes where lower is better (stunting), so a positive score is always good.

The scores go into derived datasets (strengths_district2011, strengths_district2020,
strengths_state) that the normal lens, table and source code then publishes.
"""
import math
import numpy as np
from common import *

Z_FLAG = 1.5  # score at or above this counts as a strength
MAX_YIELD = 7  # t/ha milled rice or wheat; Punjab averages ~4-5, so a district above 7 is a source error (Goa rice 2022-23: 16.15); the row is left out

# id, emoji, name, question, resolution, outcome (dataset, field, label, unit, higher_is), conditions [(source, field or fn, label, transform)]
MODELS = [
    ("nonfarm", "🧰", "Non-farm jobs beyond urbanisation",
     "Which mostly rural districts still give many people non-farm work?", "district2011",
     ("census2011_district", "pct_other_workers", "Non-farm workers", "% of workers", "better"),
     [("census2011_district", "urban_share", "Urban share", None), ("census2011_district", "density", "Population density (log)", "log")]),
    ("graduates", "🎓", "Graduates beyond wealth",
     "Which districts produce more graduates than their wealth and urbanisation predict?", "district2011",
     ("census2011_district", "pct_graduate", "Graduates", "% of persons in education table", "better"),
     [("census2011_district", "urban_share", "Urban share", None), ("census2011_district", "density", "Population density (log)", "log"),
      ("census2011_district", "pct_hh_two_wheeler", "Households with a two-wheeler", None), ("census2011_district", "pct_hh_electric_lighting", "Households with electric light", None)]),
    ("female_literacy", "📚", "Female literacy beyond wealth",
     "Where are women more literate than household wealth predicts?", "district2011",
     ("census2011_district", "literacy_rate_7plus_female", "Female literacy (7+)", "% of females aged 7+", "better"),
     [("census2011_district", "urban_share", "Urban share", None), ("census2011_district", "pct_hh_two_wheeler", "Households with a two-wheeler", None),
      ("census2011_district", "pct_hh_electric_lighting", "Households with electric light", None)]),
    ("grain_yield", "🌾", "Grain yield beyond climate",
     "Which districts harvest more grain per hectare than their rain and heat predict?", "district2020",
     ("crop_district", "foodgrains_yield", "Foodgrain yield", "t/ha", "better"),
     [("raster", "precip", "Annual rainfall (log)", "log"), ("raster", "temp", "Mean temperature", None), ("raster", "elev", "Elevation", None),
      ("crop_share", "maize", "Maize share of grain area", None), ("crop_share", "pulses", "Pulses share of grain area", None)]),
    ("child_growth", "📏", "Child growth beyond living standards",
     "Where do fewer children suffer stunting than household living standards predict?", "district2020",
     ("nfhs5_district", "stunting", "Child stunting", "% of children <5", "worse"),
     [("nfhs5_district", "clean_cooking_fuel", "Clean cooking fuel", None), ("nfhs5_district", "improved_sanitation", "Improved sanitation", None),
      ("nfhs5_district", "electricity", "Electricity", None), ("nfhs5_district", "women_10yr_school", "Women with 10+ years of school", None)]),
    ("girls_school", "🏫", "Women's schooling beyond wealth",
     "Where do women complete 10 years of school more often than living standards predict?", "district2020",
     ("nfhs5_district", "women_10yr_school", "Women with 10+ years of school", "% of women 15–49", "better"),
     [("nfhs5_district", "clean_cooking_fuel", "Clean cooking fuel", None), ("nfhs5_district", "electricity", "Electricity", None),
      ("nfhs5_district", "improved_sanitation", "Improved sanitation", None)]),
    ("exports", "🚢", "Exports beyond economy size",
     "Which states export more than the size of their economy predicts?", "state",
     ("exports_state", "exports_usd_mn", "Merchandise exports (log)", "US$ million, FY 2024-25", "better"),
     [("gsdp_state", "gsdp_current", "GSDP (log)", "log")]),
    ("research", "🔬", "Top institutions beyond population",
     "Which states hold more NIRF-ranked institutions than their population predicts?", "state",
     ("derived", "nirf_ranked", "NIRF 2025 ranked institutions (log 1+n)", "institutions", "better"),
     [("census2011_state", "population", "Population 2011 (log)", "log")]),
]


NOTES = {
    "nonfarm": "Census 2011 counts plantation, mining, forestry and defence workers as 'other workers'. Plantation districts (Kodagu: coffee) and districts with many government staff (Nicobar, Kargil) therefore score high.",
    "grain_yield": "Irrigation is not a condition here, so irrigated districts (Hoshangabad and Harda on the Tawa canal) score high. District crop data come from APY 2022-23; some district values are implausible.",
    "exports": "Small UTs with almost no exports make the fitted line steep. Goa (iron ore, pharmaceuticals) and Puducherry stand out.",
    "research": "NIRF 2025 ranks institutions that applied. The count shows where top-ranked institutions are, not all research.",
}


def _district_raster_means(ctx, res):
    """Mean of each terrain raster over the sample points of each district."""
    W = ctx.g["w11"] if res == "district2011" else ctx.g["w20"]
    keys = ctx.g["d11_keys"] if res == "district2011" else ctx.g["d20_keys"]
    out = {}
    for name in ("precip", "temp", "elev"):
        arr = ctx.t[name]; s = collections.Counter(); n = collections.Counter()
        for c, lst in W.items():
            v = arr[int(c)]
            if v is None or (isinstance(v, float) and math.isnan(v)):
                continue
            for d, cnt in lst:
                s[d] += v * cnt; n[d] += cnt
        out[name] = {keys[d]: s[d] / n[d] for d in n}
    return out


def _value(ctx, src, field, key, res, cache):
    if src == "raster":
        if res not in cache:
            cache[res] = _district_raster_means(ctx, res)
        return cache[res][field].get(key)
    if src == "derived" and field == "nirf_ranked":
        if "nirf" not in cache:
            cache["nirf"] = collections.Counter(r["state"] for r in ctx.ds["universities"]["rows"] if r.get("nirf_rank"))
        return math.log1p(cache["nirf"].get(key, 0))
    if src == "crop_share":
        r = cache.setdefault(("rows", "crop_district"), ctx.rows_by_key("crop_district")).get(key)
        tot = r and r.get("foodgrains_area_ha")
        return (r.get(f"{field}_area_ha") or 0) / tot if tot else None
    r = cache.setdefault(("rows", src), ctx.rows_by_key(src)).get(key)
    if r is None:
        return None
    if src == "gsdp_state" and field == "gsdp_current":  # match the exports year (FY 2024-25) when the series has it
        return ((r.get("series") or {}).get("gsdp_current") or {}).get("2024-25") or r.get(field)
    return r.get(field)


def fit(y, X):
    """OLS on standardised conditions. Returns (prediction, coefficients, r2)."""
    mu, sd = X.mean(0), X.std(0); sd[sd == 0] = 1
    A = np.column_stack([np.ones(len(y)), (X - mu) / sd])
    b, *_ = np.linalg.lstsq(A, y, rcond=None)
    pred = A @ b
    r2 = 1 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    return pred, b[1:], float(r2)


def build(ctx, L):
    """Add derived datasets to ctx.ds and return (lens specs, models for strengths.json)."""
    cache, models, lenses, derived = {}, [], [], {}
    for mid, emoji, name, question, res, (osrc, ofld, olabel, ounit, hib), conds in MODELS:
        if osrc != "derived" and osrc not in ctx.ds or any(s not in ("raster", "derived", "crop_share") and s not in ctx.ds for s, *_ in conds):
            print("skip strength model (no data)", mid); continue
        base = ctx.ds[osrc if osrc != "derived" else conds[0][0]]
        keys, names, states, ys, xs, excluded = [], {}, {}, [], [], []
        for r in base["rows"]:
            k = str(r["key"])
            yv = _value(ctx, osrc, ofld, k, res, cache)
            xv = [_value(ctx, s, f, k, res, cache) for s, f, _, _ in conds]
            if yv is None or any(v is None for v in xv):
                continue
            if osrc == "crop_district" and any((r.get(f) or 0) > MAX_YIELD for f in ("rice_yield", "wheat_yield")):
                excluded.append(r.get("name") or k); continue
            if any(t == "log" and (v is None or v <= 0) for (_, _, _, t), v in zip(conds, xv)):
                continue
            if osrc in ("exports_state", "crop_district"):  # multiplicative outcomes: fit on log, so expected values stay positive
                if yv <= 0:
                    continue
                yv = math.log(yv)
            xv = [math.log(v) if t == "log" else v for (_, _, _, t), v in zip(conds, xv)]
            keys.append(k); names[k] = r.get("name") or k; states[k] = r.get("state"); ys.append(yv); xs.append(xv)
        y, X = np.array(ys, float), np.array(xs, float)
        pred, coef, r2 = fit(y, X)
        resid = y - pred; sd = float(resid.std())
        z = (resid / sd) * (1 if hib == "better" else -1)
        dsid = f"strengths_{res}"
        d = derived.setdefault(dsid, {"meta": {"id": dsid, "name": f"Hidden strengths ({res})", "source_org": "India Civ model (pipeline/strengths.py)",
                                               "reference_year": "model", "resolution": res, "kind": "modelled", "license": "Derived from the input datasets",
                                               "method": __doc__.strip().replace("\n", " "),
                                               "limitations": "A residual is not a cause. Conditions that a model leaves out (irrigation, history, policy, data error) also give large residuals. Inputs of different years are named in each field."},
                                      "fields": {}, "rows": {}})
        pretty = lambda v: math.exp(v) if osrc in ("exports_state", "crop_district") or ofld == "nirf_ranked" else v
        for k, a, p, s in zip(keys, y, pred, z):
            row = d["rows"].setdefault(k, {"key": k, "name": names[k], "state": states[k]})
            row[f"{mid}_score"] = round(float(s), 2)
            row[f"{mid}_expected"] = round(float(pretty(p)) - (1 if ofld == "nirf_ranked" else 0), 2)
        cond_txt = ", ".join(c[2] for c in conds)
        excl_txt = f" Left out as source errors (rice or wheat yield above {MAX_YIELD} t/ha): {', '.join(excluded)}." if excluded else ""
        years = {osrc: ctx.ds[osrc]["meta"].get("reference_year") if osrc in ctx.ds else "2025"} | {s: ctx.ds[s]["meta"].get("reference_year") for s, *_ in conds if s in ctx.ds}
        d["fields"][f"{mid}_score"] = {"name": f"{name} (score)", "type": "rate", "unit": "standard deviations", "higher_is": "better",
                                       "description": f"{olabel}: residual of a least-squares fit on {cond_txt}, in standard deviations (n = {len(y)}, R² = {r2:.2f}). Positive = better than places with the same conditions."}
        d["fields"][f"{mid}_expected"] = {"name": f"{olabel}: expected", "type": "rate" if res != "state" else "value", "unit": ounit, "higher_is": hib,
                                          "description": f"Value that the fit on {cond_txt} predicts."}
        order = np.argsort(-z)
        pick = lambda idx: [{"key": keys[i], "name": names[keys[i]], "state": states[keys[i]], "actual": round(float(pretty(y[i])) - (1 if ofld == "nirf_ranked" else 0), 2),
                             "expected": round(float(pretty(pred[i])) - (1 if ofld == "nirf_ranked" else 0), 2), "score": round(float(z[i]), 2)} for i in idx]
        models.append({"id": mid, "emoji": emoji, "name": name, "question": question, "note": NOTES.get(mid), "table": res, "dataset": dsid,
                       "outcome": {"dataset": osrc if osrc != "derived" else "universities", "field": ofld, "name": olabel, "unit": ounit, "higher_is": hib},
                       "conditions": [{"dataset": s if s != "raster" else "worldclim" if f != "elev" else "terrain_tiles", "field": f, "name": lbl, "weight": round(float(c), 3)} for (s, f, lbl, _), c in zip(conds, coef)],
                       "years": years, "n": len(y), "excluded": excluded, "r2": round(r2, 3), "flagged": int((z >= Z_FLAG).sum()),
                       "top": pick(order[:12]), "bottom": pick(order[::-1][:6]),
                       "lens": f"hs_{mid}" if res != "state" else f"hs_{mid}",
                       "explorer": {"table": res, "x": f"{dsid}.{mid}_expected", "y": f"{osrc}.{ofld}" if osrc != "derived" else f"{dsid}.{mid}_score"}})
        lenses.append(L(f"hs_{mid}", "strengths", name, emoji, dsid, f"{mid}_score", "strength", "score (standard deviations)", domain=[-2.5, 0, 2.5], higher_is="better",
                        desc=f"{question} Score = how far the district is above (+) or below (−) the value that {cond_txt} predict, in standard deviations of the residual. "
                             f"Fit: ordinary least squares, n = {len(y)}, R² = {r2:.2f}. Outcome: {olabel} ({osrc if osrc != 'derived' else 'NIRF 2025'}). A score is not a cause: irrigation, policy, history and data error also move it.{excl_txt}"))
    for dsid, d in derived.items():
        d["rows"] = list(d["rows"].values())
        ctx.ds[dsid] = d
    return lenses, models


def advisor(models):
    """One advisor whose observations are the top over-performers of each model."""
    ins = []
    for m in models:
        t = m["top"][:3]
        if not t or t[0]["score"] < Z_FLAG:
            continue
        lead = "; ".join(f"{x['name']} ({x['state']}) {x['actual']:,} vs {x['expected']:,} expected" for x in t if x["score"] >= Z_FLAG)
        ins.append({"text": f"{m['name']}: {lead} ({m['outcome']['unit']}). Fit on {', '.join(c['name'] for c in m['conditions'])}, n = {m['n']}, R² = {m['r2']:.2f}.",
                    "evidence": [{"dataset": m["dataset"], "field": f"{m['id']}_score", "year": "model", "source": "India Civ model (pipeline/strengths.py)", "kind": "modelled",
                                  "table": m["table"], "select": [x["key"] for x in t if x["score"] >= Z_FLAG]},
                                 {"dataset": m["outcome"]["dataset"], "field": m["outcome"]["field"], "year": str(m["years"].get(m["outcome"]["dataset"], "")), "kind": "official", "table": m["table"], "select": []}]})
    return {"id": "strengths", "name": "Strengths Scout", "face": "🔭", "role": "Places that beat their conditions", "insights": ins}


def _selfcheck():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(200, 2)); y = 3 + 2 * X[:, 0] - X[:, 1] + rng.normal(scale=0.1, size=200)
    y[7] += 5  # a planted over-performer
    pred, coef, r2 = fit(y, X)
    z = (y - pred) / (y - pred).std()
    assert r2 > 0.9 and int(np.argmax(z)) == 7 and z[7] > 3, (r2, np.argmax(z))
    print("strengths self-check OK")


import collections  # noqa: E402

if __name__ == "__main__":
    _selfcheck()
