"""Advisor observations. Each one is computed from a normalized dataset; the text holds the
numbers, and `evidence` names the dataset, field and year so the UI can link to the data."""
import math
import numpy as np


def fnum(v, d=0):
    if v is None:
        return "—"
    if abs(v) >= 1e7 and d == 0:
        return f"{v / 1e7:,.1f} crore"
    if abs(v) >= 1e5 and d == 0:
        return f"{v / 1e5:,.1f} lakh"
    return f"{v:,.{d}f}"


class A:
    def __init__(self, ctx):
        self.ctx = ctx
        self.sname = {s["id"]: s["name"] for s in ctx.states}

    def rows(self, ds, field, res=None):
        d = self.ctx.ds.get(ds)
        if not d:
            return []
        return [r for r in d["rows"] if isinstance(r.get(field), (int, float))]

    def meta(self, ds):
        return self.ctx.ds[ds]["meta"]

    def ev(self, ds, field, sel=None):
        m = self.meta(ds)
        return {"dataset": ds, "field": field, "year": m.get("reference_year"), "source": m.get("source_org"), "kind": m.get("kind"),
                "table": m.get("resolution"), "select": sel or []}

    def name(self, r, ds):
        if self.meta(ds)["resolution"] == "state":
            return self.sname.get(r["state"], r.get("name"))
        return f"{r.get('name')} ({self.sname.get(r.get('state'), r.get('state'))})"


def corr(x, y):
    x, y = np.array(x, float), np.array(y, float)
    return float(np.corrcoef(x, y)[0, 1])


def build(ctx):
    a = A(ctx)
    adv = {k: [] for k in ("economy", "science", "agriculture", "infrastructure", "population", "environment", "health", "culture", "history")}

    def add(k, text, *evs):
        adv[k].append({"text": text, "evidence": list(evs)})

    def top(ds, f, n=3, rev=True):
        rs = sorted(a.rows(ds, f), key=lambda r: -r[f] if rev else r[f])
        return rs[:n], rs

    # ---------------- economy
    if "gsdp_state" in ctx.ds:
        t, allr = top("gsdp_state", "gsdp_current", 3)
        tot = sum(r["gsdp_current"] for r in allr)
        share = sum(r["gsdp_current"] for r in t) / tot * 100
        add("economy", f"{', '.join(a.sname[r['state']] for r in t)} produce {share:.0f}% of the GSDP of the {len(allr)} states and UTs with 2023-24 data.",
            a.ev("gsdp_state", "gsdp_current", [r["state"] for r in t]))
        t, allr = top("gsdp_state", "pc_nsdp_current", 1); b = sorted(allr, key=lambda r: r["pc_nsdp_current"])[0]
        add("economy", f"Income per person is {t[0]['pc_nsdp_current'] / b['pc_nsdp_current']:.1f}× higher in {a.sname[t[0]['state']]} (₹{fnum(t[0]['pc_nsdp_current'])}) than in {a.sname[b['state']]} (₹{fnum(b['pc_nsdp_current'])}), per-capita NSDP 2023-24.",
            a.ev("gsdp_state", "pc_nsdp_current", [t[0]["state"], b["state"]]))
    if "gsva_sector_state" in ctx.ds:
        rs = a.rows("gsva_sector_state", "share_mfg")
        nat = sum(r["gsva_mfg"] for r in rs if r.get("gsva_mfg")) / sum(r["gsva_total"] for r in rs if r.get("gsva_total") and r.get("gsva_mfg")) * 100
        t = sorted([r for r in rs if (r.get("gsva_total") or 0) > 5e6], key=lambda r: -r["share_mfg"])[:3]
        add("economy", f"Manufacturing is {t[0]['share_mfg']:.0f}% of {a.sname[t[0]['state']]}'s economy, against {nat:.0f}% for all states together. {a.sname[t[1]['state']]} ({t[1]['share_mfg']:.0f}%) and {a.sname[t[2]['state']]} ({t[2]['share_mfg']:.0f}%) follow (larger states only).",
            a.ev("gsva_sector_state", "share_mfg", [r["state"] for r in t]))
        tf = sorted([r for r in rs if (r.get("gsva_total") or 0) > 5e6 and r.get("share_finance") is not None], key=lambda r: -r["share_finance"])[:1]
        if tf:
            add("economy", f"{a.sname[tf[0]['state']]} has the largest financial-services share of GSVA among the larger states: {tf[0]['share_finance']:.1f}%.", a.ev("gsva_sector_state", "share_finance", [tf[0]["state"]]))
    if "exports_state" in ctx.ds:
        t, allr = top("exports_state", "exports_usd_mn", 3)
        share = sum(r["exports_usd_mn"] for r in t) / sum(r["exports_usd_mn"] for r in allr) * 100
        add("economy", f"{share:.0f}% of merchandise exports leave from three states: {', '.join(a.sname[r['state']] for r in t)}.", a.ev("exports_state", "exports_usd_mn", [r["state"] for r in t]))
    if "district_gdp" in ctx.ds:
        rs = a.rows("district_gdp", "gddp_current")
        t = sorted(rs, key=lambda r: -r["gddp_current"])[:2]
        sh = sum(r["gddp_current"] for r in t) / sum(r["gddp_current"] for r in rs) * 100
        add("economy", f"In Maharashtra, {t[0]['name']} and {t[1]['name']} produce {sh:.0f}% of the gross district product of the districts with data (2022-23). Only Maharashtra publishes this table in a machine-readable form here.",
            a.ev("district_gdp", "gddp_current", [r["key"] for r in t]))
    if "plfs_state" in ctx.ds:
        rs = [r for r in a.rows("plfs_state", "ur")]
        t = sorted(rs, key=lambda r: -r["ur"])[:3]
        add("economy", f"The highest unemployment rates (PLFS 2025, age 15+) are in {', '.join(f'{a.sname[r['state']]} ({r['ur']:.1f}%)' for r in t)}. Small states have small samples.", a.ev("plfs_state", "ur", [r["state"] for r in t]))

    # ---------------- science / education
    if "census2011_district" in ctx.ds:
        rs = a.rows("census2011_district", "edu_graduate")
        t = sorted(rs, key=lambda r: -r["edu_graduate"])
        sh = sum(r["edu_graduate"] for r in t[:10]) / sum(r["edu_graduate"] for r in t) * 100
        add("science", f"The 10 districts with the most graduates hold {sh:.0f}% of India's graduates (Census 2011) — {', '.join(r['name'] for r in t[:4])} lead.", a.ev("census2011_district", "edu_graduate", [r["key"] for r in t[:10]]))
        rs = [dict(r, literacy_rate=r["literacy_rate_7plus"]) for r in a.rows("census2011_district", "literacy_rate_7plus")]
        hi, lo = max(rs, key=lambda r: r["literacy_rate"]), min(rs, key=lambda r: r["literacy_rate"])
        add("science", f"The literacy rate (age 7+) ranges from {lo['literacy_rate']:.1f}% in {a.name(lo, 'census2011_district')} to {hi['literacy_rate']:.1f}% in {a.name(hi, 'census2011_district')} (Census 2011).",
            a.ev("census2011_district", "literacy_rate_7plus", [lo["key"], hi["key"]]))
    if "universities" in ctx.ds:
        rs = [r for r in ctx.ds["universities"]["rows"] if r.get("lat")]
        by = {}
        for r in rs:
            by.setdefault(r.get("state"), []).append(r)
        t = sorted(by.items(), key=lambda kv: -len(kv[1]))[:3]
        add("science", f"Of {len(rs)} mapped national institutes, ranked universities and research centres, {sum(len(v) for _, v in t)} are in three states: {', '.join(f'{a.sname.get(k, k)} ({len(v)})' for k, v in t)}.",
            a.ev("universities", "category", [k for k, _ in t]))
    if "nfhs5_district" in ctx.ds:
        rs = [r for r in ctx.ds["nfhs5_district"]["rows"] if isinstance(r.get("women_10yr_school"), (int, float)) and isinstance(r.get("stunting"), (int, float))]
        c = corr([r["women_10yr_school"] for r in rs], [r["stunting"] for r in rs])
        add("science", f"Across {len(rs)} districts, more schooling for women goes with less child stunting: correlation r = {c:.2f} between women with 10+ years of school and stunted children (NFHS-5, same survey). Correlation does not show cause.",
            a.ev("nfhs5_district", "women_10yr_school"), a.ev("nfhs5_district", "stunting"))

    # ---------------- agriculture
    if "crop_state" in ctx.ds:
        t, allr = top("crop_state", "foodgrains_prod_mt", 3)
        sh = sum(r["foodgrains_prod_mt"] for r in t) / sum(r["foodgrains_prod_mt"] for r in allr) * 100
        add("agriculture", f"{', '.join(a.sname[r['state']] for r in t)} grow {sh:.0f}% of the foodgrains of the {len(allr)} leading producer states listed for 2023-24 (the source lists only major producers).", a.ev("crop_state", "foodgrains_prod_mt", [r["state"] for r in t]))
        rs = [r for r in a.rows("crop_state", "foodgrains_yield_all_kgha") if (r.get("foodgrains_area_mha") or 0) > 0.5]
        hi, lo = max(rs, key=lambda r: r["foodgrains_yield_all_kgha"]), min(rs, key=lambda r: r["foodgrains_yield_all_kgha"])
        add("agriculture", f"A hectare of foodgrain land gives {fnum(hi['foodgrains_yield_all_kgha'])} kg in {a.sname[hi['state']]} but {fnum(lo['foodgrains_yield_all_kgha'])} kg in {a.sname[lo['state']]} (states with > 0.5 million ha of foodgrains).",
            a.ev("crop_state", "foodgrains_yield_all_kgha", [hi["state"], lo["state"]]))
        rs = a.rows("crop_state", "irrigation_share_pct")
        t = sorted([r for r in rs if (r.get("net_sown_kha") or 0) > 500], key=lambda r: -r["irrigation_share_pct"])
        if t:
            add("agriculture", f"{a.sname[t[0]['state']]} irrigates {t[0]['irrigation_share_pct']:.0f}% of its net sown area; {a.sname[t[-1]['state']]} irrigates {t[-1]['irrigation_share_pct']:.0f}% (Land Use Statistics 2022-23, states with > 0.5 Mha sown).",
                a.ev("crop_state", "irrigation_share_pct", [t[0]["state"], t[-1]["state"]]))
    if "fisheries_state" in ctx.ds:
        t, allr = top("fisheries_state", "total_lakh_t", 1)
        sh = t[0]["total_lakh_t"] / sum(r["total_lakh_t"] for r in allr) * 100
        inl = t[0].get("inland_lakh_t") or 0
        add("agriculture", f"{a.sname[t[0]['state']]} lands {sh:.0f}% of India's fish ({t[0]['total_lakh_t']:.1f} lakh t in 2023-24), {inl / t[0]['total_lakh_t'] * 100:.0f}% of it from inland waters.", a.ev("fisheries_state", "total_lakh_t", [t[0]["state"]]))
    if "livestock_state" in ctx.ds:
        t, allr = top("livestock_state", "milk_kt", 3)
        sh = sum(r["milk_kt"] for r in t) / sum(r["milk_kt"] for r in allr) * 100
        add("agriculture", f"{', '.join(a.sname[r['state']] for r in t)} produce {sh:.0f}% of India's milk (2023-24).", a.ev("livestock_state", "milk_kt", [r["state"] for r in t]))

    # ---------------- infrastructure / energy
    if "seaports" in ctx.ds:
        rs = sorted(a.rows("seaports", "cargo_tonnes"), key=lambda r: -r["cargo_tonnes"])
        if rs:
            sh = sum(r["cargo_tonnes"] for r in rs[:3]) / sum(r["cargo_tonnes"] for r in rs) * 100
            add("infrastructure", f"The three busiest ports with cargo data — {', '.join(r['name'].split(',')[0] for r in rs[:3])} — handle {sh:.0f}% of the cargo of the {len(rs)} ports listed ({rs[0].get('cargo_year')}).", a.ev("seaports", "cargo_tonnes", [r["key"] for r in rs[:3]]))
    if "airports" in ctx.ds:
        rs = sorted(a.rows("airports", "passengers"), key=lambda r: -r["passengers"])
        if rs:
            sh = sum(r["passengers"] for r in rs[:2]) / sum(r["passengers"] for r in rs) * 100
            add("infrastructure", f"{rs[0]['name']} and {rs[1]['name']} carry {sh:.0f}% of passengers at the {len(rs)} airports with AAI traffic data ({rs[0].get('passengers_year')}).", a.ev("airports", "passengers", [r["key"] for r in rs[:2]]))
    if "power_plants" in ctx.ds:
        rs = a.rows("power_plants", "capacity_mw")
        tot = sum(r["capacity_mw"] for r in rs)
        by = {}
        for r in rs:
            by[r.get("category")] = by.get(r.get("category"), 0) + r["capacity_mw"]
        t = sorted(by.items(), key=lambda kv: -kv[1])
        add("infrastructure", f"In the WRI Global Power Plant Database (2019), {t[0][0].lower()} plants hold {t[0][1] / tot * 100:.0f}% of the {fnum(tot / 1000)} GW listed for India; {t[1][0].lower()} {t[1][1] / tot * 100:.0f}%, {t[2][0].lower()} {t[2][1] / tot * 100:.0f}%.", a.ev("power_plants", "capacity_mw"))
    if "renewable_potential_state" in ctx.ds:
        t, allr = top("renewable_potential_state", "solar_mw", 3)
        sh = sum(r["solar_mw"] for r in t) / sum(r["solar_mw"] for r in allr) * 100
        add("infrastructure", f"{', '.join(a.sname[r['state']] for r in t)} have {sh:.0f}% of India's installed solar capacity ({a.meta('renewable_potential_state').get('reference_year', '').split(' ')[0]}).", a.ev("renewable_potential_state", "solar_mw", [r["state"] for r in t]))

    # ---------------- population
    if "census2011_district" in ctx.ds:
        t = sorted(a.rows("census2011_district", "density"), key=lambda r: -r["density"])
        add("population", f"{t[0]['name']} ({a.sname.get(t[0]['state'])}) is the densest district: {fnum(t[0]['density'])} people per km² in 2011. {t[-1]['name']} ({a.sname.get(t[-1]['state'])}) has {t[-1]['density']:.1f}.", a.ev("census2011_district", "density", [t[0]["key"], t[-1]["key"]]))
        rs = a.rows("census2011_district", "sex_ratio")
        lo = sorted(rs, key=lambda r: r["sex_ratio"])[:3]
        add("population", f"The lowest sex ratios in 2011 were in {', '.join(f'{r['name']} ({r['sex_ratio']:.0f})' for r in lo)} females per 1,000 males; the national figure was 943.", a.ev("census2011_district", "sex_ratio", [r["key"] for r in lo]))
        rs = a.rows("census2011_district", "urban_share")
        n50 = [r for r in rs if r["urban_share"] >= 50]
        add("population", f"In 2011 only {len(n50)} of {len(rs)} districts had an urban majority; India as a whole was 31.1% urban.", a.ev("census2011_district", "urban_share", [r["key"] for r in n50]))
        rs = a.rows("census2011_district", "child_sex_ratio")
        lo = sorted(rs, key=lambda r: r["child_sex_ratio"])[:3]
        add("population", f"The lowest child sex ratios (age 0–6) in 2011: {', '.join(f'{r['name']} ({r['child_sex_ratio']:.0f})' for r in lo)} girls per 1,000 boys; the national figure was 918.", a.ev("census2011_district", "child_sex_ratio", [r["key"] for r in lo]))
    if "srs_state" in ctx.ds:
        rs = a.rows("srs_state", "birth_rate")
        hi, lo = max(rs, key=lambda r: r["birth_rate"]), min(rs, key=lambda r: r["birth_rate"])
        add("population", f"Birth rates (SRS 2024) run from {lo['birth_rate']:.1f} per 1,000 people in {a.sname[lo['state']]} to {hi['birth_rate']:.1f} in {a.sname[hi['state']]}.", a.ev("srs_state", "birth_rate", [lo["state"], hi["state"]]))

    # ---------------- environment (hex-level satellite data)
    t = ctx.t; land = [i for i in ctx.land if ctx.disputed[i] < 0]
    rain = [(t["precip"][i], i) for i in land if t["precip"][i] is not None]
    wet = max(rain); dry = min(rain)
    dname = lambda i: ctx.world["districts"][ctx.world["district"][i]]["name"] if ctx.world["district"][i] >= 0 else "?"
    add("environment", f"Annual rain on a hex ranges from {fnum(dry[0])} mm near {dname(dry[1])} to {fnum(wet[0])} mm near {dname(wet[1])} (WorldClim 2.1 normals, 1970–2000).", {"dataset": "worldclim", "field": "precip", "lens": "rainfall", "cells": [dry[1], wet[1]]})
    fl = [i for i in land if (t["flood"][i] or 0) >= 4]
    by = {}
    for i in fl:
        sid = ctx.states[ctx.g["state"][i]]["id"]; by[sid] = by.get(sid, 0) + 1
    tops = sorted(by.items(), key=lambda kv: -kv[1])[:4]
    add("environment", f"{len(fl) / len(land) * 100:.0f}% of India's land hexes had 4 or more large floods in 1985–2003 (SEDAC flood hotspots). {', '.join(a.sname[k] for k, _ in tops)} hold {sum(v for _, v in tops) / len(fl) * 100:.0f}% of those hexes.", {"dataset": "sedac_ndh", "field": "flood", "lens": "flood", "cells": []})
    if "forest_state" in ctx.ds:
        rs = a.rows("forest_state", "forest_cover_pct")
        big = [r for r in rs if (r.get("geo_area_km2") or 0) > 20000]
        t2 = sorted(big, key=lambda r: -r["forest_cover_pct"])[:3]
        add("environment", f"Forest cover (ISFR 2023) is highest in {', '.join(f'{a.sname[r['state']]} ({r['forest_cover_pct']:.0f}%)' for r in t2)} among states larger than 20,000 km².", a.ev("forest_state", "forest_cover_pct", [r["state"] for r in t2]))
        ch = sorted(a.rows("forest_state", "forest_cover_change_km2"), key=lambda r: r["forest_cover_change_km2"])
        if ch:
            add("environment", f"From ISFR 2013 to 2023, forest cover fell most in {a.sname[ch[0]['state']]} ({ch[0]['forest_cover_change_km2']:,.0f} km²) and grew most in {a.sname[ch[-1]['state']]} (+{ch[-1]['forest_cover_change_km2']:,.0f} km²).", a.ev("forest_state", "forest_cover_change_km2", [ch[0]["state"], ch[-1]["state"]]))
        rs = a.rows("forest_state", "mangrove_km2")
        t3 = sorted(rs, key=lambda r: -r["mangrove_km2"])[:1]
        if t3:
            sh = t3[0]["mangrove_km2"] / sum(r["mangrove_km2"] for r in rs) * 100
            add("environment", f"{a.sname[t3[0]['state']]} holds {sh:.0f}% of India's mangroves (the Sundarbans), {fnum(t3[0]['mangrove_km2'])} km² in ISFR 2023.", a.ev("forest_state", "mangrove_km2", [t3[0]["state"]]))

    # ---------------- health
    if "nfhs5_district" in ctx.ds:
        rs = a.rows("nfhs5_district", "stunting")
        hi = sorted(rs, key=lambda r: -r["stunting"])[:3]; lo = sorted(rs, key=lambda r: r["stunting"])[:1]
        add("health", f"Child stunting (NFHS-5) is highest in {', '.join(f'{r['name']} ({r['stunting']:.0f}%)' for r in hi)} and lowest in {lo[0]['name']} ({lo[0]['stunting']:.0f}%).", a.ev("nfhs5_district", "stunting", [r["key"] for r in hi + lo]))
        rs = a.rows("nfhs5_district", "institutional_births")
        n90 = sum(1 for r in rs if r["institutional_births"] >= 90)
        add("health", f"In {n90} of {len(rs)} districts, at least 90% of births took place in a health facility (NFHS-5, 2019–21).", a.ev("nfhs5_district", "institutional_births"))
        rs = a.rows("nfhs5_district", "health_insurance")
        lo = sorted(rs, key=lambda r: r["health_insurance"])[:3]
        add("health", f"Health insurance coverage is lowest in {', '.join(f'{r['name']} ({r['health_insurance']:.0f}% of households)' for r in lo)}.", a.ev("nfhs5_district", "health_insurance", [r["key"] for r in lo]))
    if "srs_state" in ctx.ds:
        rs = a.rows("srs_state", "life_exp")
        if rs:
            hi, lo = max(rs, key=lambda r: r["life_exp"]), min(rs, key=lambda r: r["life_exp"])
            add("health", f"A baby born in {a.sname[hi['state']]} can expect to live {hi['life_exp'] - lo['life_exp']:.1f} years longer than one born in {a.sname[lo['state']]} ({hi['life_exp']:.1f} v {lo['life_exp']:.1f}, SRS 2020–24).", a.ev("srs_state", "life_exp", [hi["state"], lo["state"]]))
        rs = a.rows("srs_state", "imr")
        hi, lo = max(rs, key=lambda r: r["imr"]), min(rs, key=lambda r: r["imr"])
        add("health", f"Infant mortality (SRS 2024) is {hi['imr']:.0f} per 1,000 live births in {a.sname[hi['state']]} and {lo['imr']:.0f} in {a.sname[lo['state']]}.", a.ev("srs_state", "imr", [hi["state"], lo["state"]]))

    # ---------------- culture
    if "unesco_whs" in ctx.ds:
        rs = [r for r in ctx.ds["unesco_whs"]["rows"] if not r.get("tentative")]
        by = {}
        for r in rs:
            by[r.get("state")] = by.get(r.get("state"), 0) + 1
        t = sorted([kv for kv in by.items() if kv[0]], key=lambda kv: -kv[1])[:3]
        add("culture", f"India has {len(rs)} UNESCO World Heritage Sites on this map. {', '.join(f'{a.sname.get(k, k)} ({v})' for k, v in t)} have the most.", a.ev("unesco_whs", "category", [k for k, _ in t]))
    if "asi_monuments" in ctx.ds:
        rs = ctx.ds["asi_monuments"]["rows"]
        by = {}
        for r in rs:
            by[r.get("state")] = by.get(r.get("state"), 0) + 1
        t = sorted([kv for kv in by.items() if kv[0]], key=lambda kv: -kv[1])[:3]
        add("culture", f"Of {len(rs)} ASI-protected monuments with coordinates in Wikidata, {', '.join(f'{a.sname.get(k, k)} has {v}' for k, v in t)}.", a.ev("asi_monuments", "category", [k for k, _ in t]))

    # ---------------- history
    h = ctx.ds.get("history")
    if h:
        caps = {}
        for e in h["eras"]:
            for p in e.get("polities", []):
                for c in p.get("capitals", []):
                    caps.setdefault(c["name"].split(" (")[0], set()).add(p["name"])
        multi = sorted(caps.items(), key=lambda kv: -len(kv[1]))[:3]
        for name, ps in multi:
            if len(ps) >= 2:
                add("history", f"{name} served as a capital of {len(ps)} polities in this timeline: {', '.join(sorted(ps))}.", {"dataset": "history", "field": "capitals", "mode": "history"})
        n_ext = sum(1 for e in h["eras"] for p in e.get("polities", []) if (p.get("extent") or {}).get("geometry"))
        n_pol = sum(len(e.get("polities", [])) for e in h["eras"])
        add("history", f"Only {n_ext} of {n_pol} polities have a mapped extent, and every extent is a single-year snapshot from the historical-basemaps project. Treat outlines as approximate.", {"dataset": "history", "field": "extent", "mode": "history"})
        ind = next((e for e in h["eras"] if e["id"].startswith("indus")), None)
        if ind:
            add("history", f"The timeline maps {len(ind.get('places', []))} Indus Valley sites, from {min((p['lat'] for p in ind['places']), default=0):.1f}°N to {max((p['lat'] for p in ind['places']), default=0):.1f}°N; several lie outside India's present borders.", {"dataset": "history", "field": "places", "mode": "history", "era": ind["id"]})

    meta = {
        "economy": ("Economic Advisor", "💰", "GDP, sectors, trade and work"),
        "science": ("Science Advisor", "🔬", "Education and research"),
        "agriculture": ("Agriculture Advisor", "🌾", "Crops, irrigation, fish and milk"),
        "infrastructure": ("Infrastructure Advisor", "🛤️", "Ports, airports and power"),
        "population": ("Population Advisor", "👥", "Density, cities and demography"),
        "environment": ("Environment Advisor", "🌳", "Forests, rain and hazards"),
        "health": ("Health Advisor", "❤️", "Nutrition, care and survival"),
        "culture": ("Culture Advisor", "🎭", "Heritage and monuments"),
        "history": ("Historical Advisor", "📜", "Empires, capitals and uncertainty"),
    }
    return [{"id": k, "name": meta[k][0], "face": meta[k][1], "role": meta[k][2], "insights": v} for k, v in adv.items() if v]
