"""Civilization mechanics: yields, city footprints and specialisations, resources, wonders,
history pass-through and advisor observations. Every number traces to a normalized dataset.

YIELD MODEL (also written into nation.json for the Almanac)
Each yield has one primary real-world indicator with real units (state and national totals)
and a hex model that spreads it across hexes with a documented weight:
  food        foodgrain production (crop_state)         weight: hex cropland share (MODIS 2023)
  production  industrial GSVA: mining+mfg+elec+constr   weight: Census 2011 non-farm workers in the hex
  gold        GSDP current prices (gsdp_state)          weight: Census 2011 non-farm workers (validated on Maharashtra district GDP)
  science     graduates (Census 2011)                   direct: district counts spread by area
  culture     heritage sites (UNESCO + ASI + museums)   direct: points in the hex
  faith       religious heritage sites                  direct: points in the hex
  health      public hospital beds (RHS 2025)           hex pips use the NFHS-5 health index instead
  infrastructure power capacity, airports, ports        direct: points in the hex
Hex pips (0–4) are quintiles of the hex value per km² among land hexes with data (0 = no data or
bottom 20 %). Pips compare hexes; they are not units.
"""
import math, os, collections
import numpy as np
from common import *

YIELDS = [
    {"id": "food", "name": "Food", "emoji": "🌾", "color": "#8bc34a"},
    {"id": "production", "name": "Production", "emoji": "⚙️", "color": "#e0884a"},
    {"id": "gold", "name": "Gold", "emoji": "💰", "color": "#f2c94c"},
    {"id": "science", "name": "Science", "emoji": "🔬", "color": "#5ab0f0"},
    {"id": "culture", "name": "Culture", "emoji": "🎭", "color": "#c58af0"},
    {"id": "faith", "name": "Faith", "emoji": "🛕", "color": "#f3efe0"},
    {"id": "health", "name": "Health", "emoji": "❤️", "color": "#ef6f7a"},
    {"id": "infra", "name": "Infrastructure", "emoji": "🛤️", "color": "#9fb4c8"},
]


def _hex_area(ctx):
    fr = ctx.g["india_frac"]
    return np.array([fr[i] * HEX_AREA for i in ctx.land])


def _state_of_land(ctx):
    return [ctx.states[ctx.g["state"][i]]["id"] if ctx.g["state"][i] >= 0 else None for i in ctx.land]


def _arr(v):
    return np.array([np.nan if x is None else x for x in v], float)


def _alloc(ctx, total_by_state, weight):
    """Spread each state's total over its hexes in proportion to weight (nan/neg = 0)."""
    st = _state_of_land(ctx); w = np.nan_to_num(np.clip(weight, 0, None))
    out = np.full(len(st), np.nan)
    disp = np.array([ctx.disputed[i] >= 0 for i in ctx.land])
    for s, tot in total_by_state.items():
        if tot is None:
            continue
        m = np.array([x == s for x in st]) & ~disp
        ws = w[m].sum()
        if ws > 0:
            out[m] = tot * w[m] / ws
    return out


def _alloc_district(ctx, ds, field, weight):
    """Spread each district value over the hexes that hold its sample points, by weight × share."""
    rows = ctx.rows_by_key(ds)
    keys = ctx.g["d20_keys"] if ctx.ds[ds]["meta"]["resolution"] == "district2020" else ctx.g["d11_keys"]
    W = ctx.g["w20"] if ctx.ds[ds]["meta"]["resolution"] == "district2020" else ctx.g["w11"]
    pos = {c: k for k, c in enumerate(ctx.land)}
    parts = collections.defaultdict(list)
    for c, lst in W.items():
        k = pos.get(int(c))
        if k is None or ctx.disputed[int(c)] >= 0:
            continue
        for d, cnt in lst:
            parts[d].append((k, weight[k] * cnt))
    out = np.full(len(ctx.land), np.nan)
    for d, lst in parts.items():
        r = rows.get(keys[d]); v = None if r is None else r.get(field)
        if v is None:
            continue
        tw = sum(w for _, w in lst)
        for k, w in lst:
            out[k] = (0 if np.isnan(out[k]) else out[k]) + (v * w / tw if tw > 0 else 0)
    return out


def points(ctx, ds, filt=None):
    d = ctx.ds.get(ds)
    if not d:
        return []
    return [r for r in d["rows"] if r.get("lat") is not None and r.get("lon") is not None and (filt is None or filt(r))]


def point_cells(ctx, rows):
    """Land-index (position in world.land) of each point, or -1."""
    g = ctx.g; cols, rows_n = g["cols"], g["rows"]
    pos = {c: k for k, c in enumerate(ctx.land)}
    out = []
    for r in rows:
        x, y = project(r["lon"], r["lat"])
        rr = int(round((float(y) - g["y0"]) / (1.5 * HEX_R)))
        best, bd = -1, 1e18
        for R in (rr - 1, rr, rr + 1):
            if not 0 <= R < rows_n:
                continue
            c0 = int(round((float(x) - g["x0"]) / HEX_W - 0.5 * (R & 1)))
            for C in (c0 - 1, c0, c0 + 1):
                if 0 <= C < cols:
                    cx = g["x0"] + HEX_W * (C + 0.5 * (R & 1)); cy = g["y0"] + 1.5 * HEX_R * R
                    d = (cx - x) ** 2 + (cy - y) ** 2
                    if d < bd and R * cols + C in pos:  # nearest land hex, so coastal points do not fall in the sea
                        bd, best = d, R * cols + C
        out.append(pos.get(best, -1))  # ponytail: 3x3 window (~35 km); points further offshore stay -1
    return out


def validate_gold(ctx, nonfarm):
    """Compare allocation weights with Maharashtra's official district GDP (district_gdp)."""
    dg = {r["key"]: r.get("gddp_current") for r in ctx.ds.get("district_gdp", {"rows": []})["rows"]}
    keys = ctx.g["d20_keys"]
    lights = np.nan_to_num(_arr(ctx.raster("nightlights"))) * _hex_area(ctx)
    out = {"n": 0, "r_nonfarm": float("nan"), "err_nonfarm": float("nan"), "r_lights": float("nan"), "err_lights": float("nan")}
    for name, w in (("nonfarm", nonfarm), ("lights", lights)):
        tot = collections.Counter()
        for k, i in enumerate(ctx.land):
            d = ctx.g["d20"][i]
            if d >= 0 and dg.get(keys[d]):
                tot[keys[d]] += w[k]
        ks = [k for k in tot if dg.get(k)]
        if len(ks) < 5:
            return out
        o = np.array([dg[k] for k in ks]); m = np.array([tot[k] for k in ks]); m = m / m.sum() * o.sum()
        out["n"] = len(ks); out[f"r_{name}"] = float(np.corrcoef(np.log(o), np.log(m))[0, 1]); out[f"err_{name}"] = float(np.median(np.abs(m - o) / o) * 100)
    return out


def heritage_points(ctx):
    """(culture_points, faith_points) from the heritage datasets that exist."""
    cult, faith = [], []
    for r in points(ctx, "unesco_whs"):
        if r.get("tentative"):
            continue
        cult.append((r, 10 if r.get("category", "").lower().startswith("cult") or r.get("category", "").lower() == "mixed" else 5))
    for r in points(ctx, "asi_monuments"):
        rel = (r.get("category") or "").lower()
        if r.get("religious") or any(k in rel for k in ("temple", "mosque", "church", "gurdwara", "monastery", "stupa", "dargah", "tomb", "religious")):
            faith.append((r, 1))
        cult.append((r, 1))
    for r in points(ctx, "museums"):
        cult.append((r, 2))
    return cult, faith


def build(ctx, lenses):
    n = len(ctx.land)
    area = _hex_area(ctx)
    hexv = {}  # yield -> absolute amount per hex (np array)
    state_tot = {}  # yield -> {state: amount}
    units = {}
    notes = {}

    def sval(ds, f):
        d = ctx.ds.get(ds)
        return {r["state"]: r.get(f) for r in d["rows"]} if d else {}

    # FOOD: district foodgrain production spread inside each district by cropland
    crop = np.nan_to_num(_arr([(a or 0) + (b or 0) if (a is not None or b is not None) else None for a, b in zip(ctx.raster("lc_frac", "12"), ctx.raster("lc_frac", "14"))])) / 100
    if "crop_district" in ctx.ds:
        hexv["food"] = _alloc_district(ctx, "crop_district", "foodgrains_prod", crop * area + 1e-6 * area)
        tot = collections.Counter()
        for r in ctx.ds["crop_district"]["rows"]:
            if r.get("foodgrains_prod") is not None:
                tot[r["state"]] += r["foodgrains_prod"]
        state_tot["food"] = dict(tot); units["food"] = "tonnes of foodgrain (district statistics 2022-23)"
        notes["food"] = "District foodgrain production 2022-23 (DES crop production statistics; rice, wheat, coarse cereals, pulses), spread inside each district by hex cropland area (MODIS 2023). District sums run above the national estimate (for example rice 148.6 Mt against 135.8 Mt), so compare places, not totals."
    elif "crop_state" in ctx.ds:
        tot = {k: (v * 1e6 if v is not None else None) for k, v in sval("crop_state", "foodgrains_prod_mt").items()}
        hexv["food"] = _alloc(ctx, tot, crop * area)
        state_tot["food"] = tot; units["food"] = "tonnes of foodgrain (2023-24)"
        notes["food"] = "Foodgrain production 2023-24 for the major producer states, spread by cropland."
    # census non-farm workers per hex
    nonfarm = None
    if "census2011_district" in ctx.ds:
        a = _arr(ctx.hex_values("census2011_district", "other_workers", "count"))
        b = _arr(ctx.hex_values("census2011_district", "household_industry_workers", "count"))
        nonfarm = (np.nan_to_num(a) + np.nan_to_num(b)) * area
        grads = _arr(ctx.hex_values("census2011_district", "edu_graduate", "count")) * area
        hexv["science"] = grads
        state_tot["science"] = {r["state"]: r.get("edu_graduate") for r in ctx.ds["census2011_state"]["rows"]} if "census2011_state" in ctx.ds else {}
        units["science"] = "graduates (Census 2011)"
        notes["science"] = "Graduates and above in the Census 2011 education table, spread over each district's hexes by area. Universities and research institutes appear as campus resources on the map."
    if "gsva_sector_state" in ctx.ds and nonfarm is not None:
        tot = {}
        for r in ctx.ds["gsva_sector_state"]["rows"]:
            parts = [r.get(k) for k in ("gsva_mining", "gsva_mfg", "gsva_elec", "gsva_constr")]
            tot[r["state"]] = None if any(p is None for p in parts) else sum(parts) * 1e5  # INR lakh -> INR
        hexv["production"] = _alloc(ctx, tot, nonfarm)
        state_tot["production"] = tot; units["production"] = "₹ industrial GSVA (2023-24, current prices)"
        notes["production"] = "Industrial GSVA (mining, manufacturing, electricity/gas/water, construction), 2023-24, MoSPI. Spread inside each state by Census 2011 non-farm workers (household industry + other workers). The spread is a model."
    if "gsdp_state" in ctx.ds and nonfarm is not None:
        tot = {k: (v * 1e7 if v is not None else None) for k, v in sval("gsdp_state", "gsdp_current").items()}
        hexv["gold"] = _alloc(ctx, tot, nonfarm)
        state_tot["gold"] = tot; units["gold"] = "₹ GSDP (2023-24, current prices)"
        val = validate_gold(ctx, nonfarm)
        notes["gold"] = ("Gross State Domestic Product 2023-24 at current prices (MoSPI), spread inside each state by Census 2011 non-farm workers. "
                         f"Check against Maharashtra's official district GDP 2022-23 ({val['n']} districts): log correlation r = {val['r_nonfarm']:.2f}, median error {val['err_nonfarm']:.0f}%. "
                         f"Night lights as the weight did worse (r = {val['r_lights']:.2f}, median error {val['err_lights']:.0f}%), because the Black Marble image saturates in big cities.")
        ctx.validation = val
    # CULTURE / FAITH from heritage points
    cult, faith = heritage_points(ctx)
    for yid, pts, unit, note in (("culture", cult, "heritage points (UNESCO site = 10, natural = 5, museum = 2, ASI monument = 1)", "UNESCO World Heritage Sites and protected monuments with an ASI monument ID in Wikidata (2,913 centrally protected of about 3,700, plus 1,571 state-protected) located in the hex. Wikidata coverage differs between states, so low counts can mean missing records."),
                                  ("faith", faith, "religious heritage monuments", "Protected monuments (ASI monument ID in Wikidata) whose Wikidata class is a place of worship, stupa, monastery or dargah (P31/P279*), located in the hex. This counts protected religious heritage buildings; it does not measure religious practice or belief. Wikidata coverage differs between states.")):
        if not pts:
            continue
        v = np.zeros(n)
        for (r, wgt), c in zip(pts, point_cells(ctx, [p for p, _ in pts])):
            if c >= 0:
                v[c] += wgt
        hexv[yid] = v
        st = _state_of_land(ctx); tot = collections.Counter()
        for k in range(n):
            if st[k]:
                tot[st[k]] += v[k]
        state_tot[yid] = dict(tot); units[yid] = unit; notes[yid] = note
    # HEALTH: state = public hospital beds; hex = NFHS-5 index
    if "nfhs5_district" in ctx.ds:
        comps = [("institutional_births", 1), ("full_immunisation", 1), ("stunting", -1), ("improved_sanitation", 1), ("health_insurance", 1), ("women_anaemia", -1)]
        mats = []
        for f, sgn in comps:
            a = _arr(ctx.hex_values("nfhs5_district", f))
            ok = ~np.isnan(a)
            rank = np.full(n, np.nan)
            rank[ok] = (np.argsort(np.argsort(sgn * a[ok])) + 0.5) / ok.sum()
            mats.append(rank)
        idx = np.nanmean(np.stack(mats), 0) if mats else None
        hexv["health"] = idx * area  # index per km² -> uniform; pips use density
        notes["health"] = "Hex pips: mean percentile of six NFHS-5 (2019–21) district indicators — institutional births, full immunisation, sanitation, insurance (higher is better) and stunting, anaemia in women (lower is better). State totals: public hospital beds (district, sub-district hospitals and medical colleges, RHS 2025)."
    if "health_infra_state" in ctx.ds:
        tot = {}
        for r in ctx.ds["health_infra_state"]["rows"]:
            parts = [r.get(k) for k in ("beds_dh", "beds_sdh", "beds_medical_colleges")]
            tot[r["state"]] = sum(p or 0 for p in parts) if any(p is not None for p in parts) else None
        state_tot["health"] = tot; units["health"] = "public hospital beds (31 March 2025)"
    # INFRASTRUCTURE: points (power MW, airport passengers, port cargo)
    v = np.zeros(n); have = False
    for ds, key, scale in (("power_plants", "capacity_mw", 1 / 1000), ("airports", "passengers", 1 / 1e6), ("seaports", "cargo_tonnes", 1 / 1e7)):
        pts = points(ctx, ds)
        for r, c in zip(pts, point_cells(ctx, pts)):
            if c >= 0 and r.get(key):
                v[c] += r[key] * scale; have = True
    if have:
        # rail and road length if present
        hexv["infra"] = v
        st = _state_of_land(ctx); tot = collections.Counter()
        pp = points(ctx, "power_plants")
        for r, c in zip(pp, point_cells(ctx, pp)):
            if c >= 0 and st[c] and r.get("capacity_mw"):
                tot[st[c]] += r["capacity_mw"]
        state_tot["infra"] = dict(tot); units["infra"] = "MW power capacity (WRI GPPD, 2019)"
        notes["infra"] = "Hex score: power capacity (GW) + airport passengers (millions) + port cargo (10 Mt units) in the hex. State totals: installed power-plant capacity in the WRI Global Power Plant Database (2019)."

    # pips
    pips = {}
    ylenses = []
    for y in YIELDS:
        yid = y["id"]
        if yid not in hexv:
            continue
        dens = hexv[yid] / np.where(area > 0, area, np.nan)
        dens[[ctx.disputed[i] >= 0 for i in ctx.land]] = np.nan  # no statistics for areas India does not administer
        ok = ~np.isnan(dens)
        p = np.zeros(n, int)
        if yid in ("culture", "faith", "infra"):
            nz = ok & (dens > 0)
            if nz.sum() > 4:
                q = np.percentile(dens[nz], [25, 50, 75])
                p[nz] = 1 + np.searchsorted(q, dens[nz], side="right")
        else:
            q = np.percentile(dens[ok], [20, 40, 60, 80])
            p[ok] = np.searchsorted(q, dens[ok], side="right")
        pips[yid] = p.tolist()
        vals = [None if not ok[k] else float(dens[k]) for k in range(n)]
        st = {"n": int(ok.sum()), "p2": float(np.nanpercentile(dens, 2)), "p98": float(np.nanpercentile(dens, 98)), "median": float(np.nanmedian(dens))}
        if yid in ("culture", "faith", "infra"):
            vals = [None if not ok[k] else float(p[k]) for k in range(n)]
            st = {"n": int(ok.sum()), "p2": 0, "p98": 4, "median": float(np.median(p[ok]))}
        ylenses.append({"id": f"y_{yid}", "group": "yields", "name": f"{y['name']} yield", "emoji": y["emoji"],
                        "ramp": ["#141a22", "#2b3442", y["color"] + "66", y["color"] + "bb", y["color"]] if False else _yramp(y["color"]),
                        "unit": (units.get(yid, "") + " per km²") if yid not in ("culture", "faith", "infra") else "pips (0–4)",
                        "scale": "log" if yid in ("gold", "production", "food", "science") else "linear",
                        "higher_is": "neutral", "description": notes.get(yid, ""), "source": "mechanics", "kind": "modelled",
                        "year": "see description", "resolution": "hex model", "stats": st, "quick": False})
        write_json(f"{SITE_DATA}/lens/y_{yid}.json", {"values": [None if v is None else float(f"{v:.4g}") for v in vals]})
    write_json(f"{SITE_DATA}/hexyields.json", {"yields": [y["id"] for y in YIELDS if y["id"] in pips], "pips": pips})

    # absolute per-hex amounts kept for city footprints
    ctx.hexv = hexv

    # nation and states
    nation = {"yields": {}, "yields_meta": [], "model_note": __doc__, "validation": getattr(ctx, "validation", None)}
    for y in YIELDS:
        yid = y["id"]
        if yid not in state_tot:
            continue
        vals = [v for v in state_tot[yid].values() if v is not None]
        missing = [s["id"] for s in ctx.states if state_tot[yid].get(s["id"]) is None]
        nation["yields"][yid] = sum(vals)
        nation["yields_meta"].append({**y, "unit": units.get(yid, ""), "note": notes.get(yid, ""), "missing_states": missing})
    pop = ctx.ds.get("census2011_state")
    nation["population_2011"] = sum(r["population"] for r in pop["rows"]) if pop else None
    states_out = []
    for s in ctx.states:
        row = {"id": s["id"], "name": s["name"], "type": s["type"], "yields": {y: state_tot[y].get(s["id"]) for y in state_tot}}
        states_out.append(row)
    for y in nation["yields_meta"]:
        ranked = sorted([r for r in states_out if r["yields"].get(y["id"])], key=lambda r: -r["yields"][y["id"]])
        for k, r in enumerate(ranked):
            r.setdefault("rank", {})[y["id"]] = k + 1
    return ylenses, nation, states_out


def _yramp(c):
    return ["#141a22", "#26303c", _mix(c, "#26303c", 0.6), _mix(c, "#26303c", 0.3), c, _mix(c, "#ffffff", 0.45)]


def _mix(a, b, t):
    pa = [int(a[i:i + 2], 16) for i in (1, 3, 5)]; pb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{int(x + (y - x) * t):02x}" for x, y in zip(pa, pb))


# ---------------------------------------------------------------- cities
SPECIALS = {
    "food": ("Breadbasket", "🌾"), "production": ("Industry", "🏭"), "gold": ("Commerce", "💰"),
    "science": ("Knowledge", "🔬"), "culture": ("Heritage", "🎭"), "faith": ("Pilgrimage", "🛕"), "infra": ("Logistics & energy", "⚡"),
}


def footprint(ctx, land_k):
    """land index of a city's hex plus its 6 neighbours that are Indian land."""
    pos = {c: k for k, c in enumerate(ctx.land)}
    i = ctx.land[land_k]
    out = [land_k]
    for j in neighbors(i, ctx.g["cols"], ctx.g["rows"]):
        if j in pos:
            out.append(pos[j])
    return out


def _dist2(ctx, i, x, y):
    g = ctx.g; R, C = divmod(i, g["cols"])
    return (g["x0"] + HEX_W * (C + 0.5 * (R & 1)) - x) ** 2 + (g["y0"] + 1.5 * HEX_R * R - y) ** 2


def build_cities(ctx):
    d = ctx.ds.get("cities")
    if not d:
        return
    rows = d["rows"]
    cells = point_cells(ctx, rows)
    c11 = ctx.rows_by_key("census2011_district") if "census2011_district" in ctx.ds else {}
    n20 = ctx.rows_by_key("nfhs5_district") if "nfhs5_district" in ctx.ds else {}
    hexv = getattr(ctx, "hexv", {})
    nat_pop = sum(r["population"] for r in ctx.ds["census2011_state"]["rows"])
    # national yield per person (2011 population as denominator for every yield: a fixed reference)
    nat = {y: float(np.nansum(v)) for y, v in hexv.items()}
    pop_hex = np.nan_to_num(_arr(ctx.hex_values("census2011_district", "population", "count"))) * _hex_area(ctx)
    # institutions and other point features near each city (footprint)
    feats = collections.defaultdict(list)
    for ds, label in (("universities", "campus"), ("unesco_whs", "unesco"), ("seaports", "port"), ("airports", "airport"), ("power_plants", "power"), ("medical_colleges", "medical"), ("defence_public", "defence")):
        pts = points(ctx, ds)
        for r, c in zip(pts, point_cells(ctx, pts)):
            if c >= 0:
                feats[c].append((label, r))
    out = []
    for r, k in zip(rows, cells):
        pop = r.get("ua_population_2011") or r.get("city_population_2011")
        x, y = project(r["lon"], r["lat"])
        city = {"id": r["key"], "name": r["name"], "state": r["state"], "lat": r["lat"], "lon": r["lon"], "x": round(float(x), 2), "y": round(float(y), 2),
                "population": pop, "population_kind": "Urban agglomeration (Census 2011)" if r.get("ua_population_2011") else ("City (Census 2011)" if r.get("city_population_2011") else None),
                "capital": "national" if r.get("capital_type") == "national" else ("state" if r.get("is_capital") else None),
                "capital_note": r.get("capital_note"), "wikidata": r.get("wikidata"), "wikipedia": r.get("wikipedia_title"),
                "district2011": r.get("census2011_district"), "district2020": r.get("district2020")}
        if k < 0:  # small island: the nearest land hex of the same state stands in for the city
            st = _state_of_land(ctx)
            same = [j for j in range(len(ctx.land)) if st[j] == r["state"]]
            if same:
                k = min(same, key=lambda j: _dist2(ctx, ctx.land[j], x, y))
                city["hex_offset_km"] = round(_dist2(ctx, ctx.land[k], x, y) ** 0.5)
        if k >= 0:
            fp = footprint(ctx, k)
            city["cells"] = [ctx.land[j] for j in fp]
            fpop = float(sum(pop_hex[j] for j in fp))
            city["footprint_pop_2011"] = round(fpop)
            ys, lq = {}, {}
            for y_, v in hexv.items():
                if y_ == "health":
                    continue
                fv = [v[j] for j in fp]
                if all(np.isnan(fv)):
                    continue  # the state has no source total for this yield: missing, not zero
                s = float(np.nansum(fv))
                ys[y_] = s
                if fpop > 0 and nat.get(y_):
                    lq[y_] = (s / fpop) / (nat[y_] / nat_pop)
            city["yields"] = {k_: float(f"{v:.4g}") for k_, v in ys.items()}
            city["lq"] = {k_: round(v, 2) for k_, v in lq.items()}
            nearby = collections.defaultdict(list)
            for j in fp:
                for lab, pr in feats.get(j, []):
                    nearby[lab].append(pr)
            city["_nearby"] = nearby
            city["nearby"] = {lab: [{"name": p["name"], "category": p.get("category"), "key": p.get("key"),
                                     **{f: p.get(f) for f in ("capacity_mw", "passengers", "cargo_tonnes", "nirf_rank", "year_inscribed") if p.get(f) is not None}} for p in v[:12]]
                              for lab, v in nearby.items()}
            city["_pc"] = {y_: (ys[y_] / fpop if fpop > 0 else None) for y_ in ys}
        cd = c11.get(str(r.get("census2011_district")))
        if cd:
            city["district_2011"] = {f: cd.get(f) for f in ("name", "population", "literacy_rate", "sex_ratio", "urban_household_share", "pct_graduate", "worker_participation",
                                                            "female_worker_participation", "cultivators", "agri_labourers", "household_industry_workers", "other_workers",
                                                            "pct_hh_internet", "pct_hh_car", "pct_hh_computer", "pct_hh_electric_lighting", "pct_hh_lpg_png")}
        nd = n20.get(str(r.get("district2020")))
        if nd:
            city["district_nfhs5"] = {f: nd.get(f) for f in ("name", "institutional_births", "full_immunisation", "stunting", "health_insurance", "improved_sanitation", "clean_cooking_fuel", "women_10yr_school", "women_anaemia")}
        out.append(city)
    # specialisation: per-resident footprint yield >= 1.6x the median city (top 2), plus facility hubs
    med = {}
    for y_ in ("food", "production", "gold", "science", "culture", "faith"):
        v = [c["_pc"][y_] for c in out if c.get("_pc", {}).get(y_)]
        if v:
            med[y_] = float(np.median(v))
    for c in out:
        specs = []
        pc = c.pop("_pc", {}) or {}
        nearby = c.pop("_nearby", {}) or {}
        rel = {y_: pc[y_] / med[y_] for y_ in med if pc.get(y_) and med[y_] > 0}
        c["vs_median_city"] = {k: round(v, 2) for k, v in rel.items()}
        for y_, q in sorted(rel.items(), key=lambda t: -t[1]):
            if q >= 1.6 and len(specs) < 2:
                specs.append({"id": y_, "name": SPECIALS[y_][0], "icon": SPECIALS[y_][1], "evidence": f"{y_.capitalize()} per resident in the footprint is {q:.1f}× the median Indian city on this map."})
        mw = sum(p.get("capacity_mw") or 0 for p in nearby.get("power", []))
        if mw >= 3000:
            specs.append({"id": "energy", "name": "Power hub", "icon": "⚡", "evidence": f"{mw:,.0f} MW of power stations in the footprint (WRI GPPD 2019)."})
        pax = sum(p.get("passengers") or 0 for p in nearby.get("airport", []))
        if pax >= 1e7:
            specs.append({"id": "aviation", "name": "Aviation hub", "icon": "✈️", "evidence": f"{pax / 1e6:,.1f} million airport passengers a year in the footprint (AAI)."})
        if any((p.get("category") or "").lower() == "major" for p in nearby.get("port", [])):
            specs.append({"id": "port", "name": "Major port", "icon": "⚓", "evidence": "A major port (Ministry of Ports list) is inside the city footprint."})
        elite = [p for p in nearby.get("campus", []) if (p.get("category") or "") in ("IIT", "IISc", "IIM", "IISER", "AIIMS", "research") or (p.get("nirf_rank") or 999) <= 25]
        if len(elite) >= 3:
            specs.append({"id": "campus", "name": "Research hub", "icon": "🎓", "evidence": f"{len(elite)} national institutes or NIRF top-25 institutions in the city footprint."})
        if nearby.get("unesco"):
            specs.append({"id": "wonder", "name": "World Heritage", "icon": "🏛️", "evidence": "UNESCO World Heritage Site(s): " + ", ".join(p["name"] for p in nearby["unesco"][:3])})
        c["specializations"] = specs
    out.sort(key=lambda c: -(c["population"] or 0))
    write_json(f"{SITE_DATA}/cities.json", out)
    print("cities", len(out), "with specialisations", sum(1 for c in out if c.get("specializations")))


# ---------------------------------------------------------------- map resources and wonders
RES_TYPES = [
    # id, dataset, filter, name, emoji, category, value field, unit
    ("coal_power", "power_plants", lambda r: r.get("category") == "Coal" and (r.get("capacity_mw") or 0) >= 500, "Coal power station", "🏭", "energy", "capacity_mw", "MW"),
    ("hydro", "power_plants", lambda r: r.get("category") == "Hydro" and (r.get("capacity_mw") or 0) >= 100, "Hydroelectric dam", "💧", "energy", "capacity_mw", "MW"),
    ("nuclear", "power_plants", lambda r: r.get("category") == "Nuclear", "Nuclear power station", "☢️", "energy", "capacity_mw", "MW"),
    ("solar", "power_plants", lambda r: r.get("category") == "Solar" and (r.get("capacity_mw") or 0) >= 50, "Solar park", "☀️", "energy", "capacity_mw", "MW"),
    ("wind", "power_plants", lambda r: r.get("category") == "Wind" and (r.get("capacity_mw") or 0) >= 50, "Wind farm", "🌬️", "energy", "capacity_mw", "MW"),
    ("gas_power", "power_plants", lambda r: r.get("category") in ("Gas", "Oil") and (r.get("capacity_mw") or 0) >= 300, "Gas/oil power station", "🔥", "energy", "capacity_mw", "MW"),
    ("airport", "airports", lambda r: r.get("scheduled_service") and r.get("category") in ("large_airport", "medium_airport"), "Airport", "✈️", "transport", "passengers", "passengers / year"),
    ("port", "seaports", None, "Seaport", "⚓", "transport", "cargo_tonnes", "tonnes / year"),
    ("campus", "universities", None, "Campus", "🎓", "knowledge", "nirf_rank", "NIRF rank"),
    ("medical", "medical_colleges", None, "Medical college / AIIMS", "⚕️", "health", "mbbs_seats", "MBBS seats"),
    ("park", "protected_areas", None, "National park / tiger reserve", "🐅", "nature", "area_km2", "km²"),
    ("monument", "asi_monuments", None, "ASI protected monument", "🏯", "heritage", None, None),
    ("mine", "minerals_points", None, "Mine or mineral field (Wikidata)", "⛏️", "resources", None, None),
    ("defence", "defence_public", None, "Defence production / shipyard", "⚓", "strategic", None, None),
]


def build_lines(ctx):
    """Rail and road corridors (Natural Earth chains) in projected km for the map overlay."""
    out = []
    for ds, t, flag in (("highways", "road", "expressway"), ("railways", "rail", None)):
        for r in ctx.ds.get(ds, {"rows": []})["rows"]:
            pts = []
            for lon, lat in r["coords"]:
                x, y = project(lon, lat); pts += [round(float(x), 1), round(float(y), 1)]
            e = r.get(flag) if flag else r.get("category") == "electrified"
            out.append({"t": t, "e": bool(e), "pts": pts})
    if out:
        km = {t: round(sum(r["length_km"] for r in ctx.ds[ds]["rows"])) for ds, t in (("highways", "road"), ("railways", "rail")) if ds in ctx.ds}
        write_json(f"{SITE_DATA}/lines.json", {"km": km, "source": "Natural Earth 10m railroads and roads (major corridors only)", "lines": out})


def build_points(ctx):
    types, items = [], []
    for tid, ds, filt, name, emoji, cat, vf, unit in RES_TYPES:
        pts = points(ctx, ds, filt)
        if not pts:
            continue
        m = ctx.ds[ds]["meta"]
        types.append({"id": tid, "name": name, "emoji": emoji, "category": cat, "unit": unit, "source": ds, "year": m.get("reference_year"), "kind": m.get("kind"), "count": len(pts)})
        for r in pts:
            x, y = project(r["lon"], r["lat"])
            it = {"t": tid, "n": r["name"], "x": round(float(x), 1), "y": round(float(y), 1), "k": r.get("key"), "s": r.get("state")}
            if vf and r.get(vf) is not None:
                it["v"] = r[vf]
            if r.get("category"):
                it["c"] = r["category"]
            for f in ("iata", "year_inscribed", "commissioning_year", "wikidata", "nirf_rank"):
                if r.get(f):
                    it[f] = r[f]
            sid = r.get("source_ids") or {}
            if isinstance(sid, dict) and sid.get("wikidata"):
                it["wikidata"] = sid["wikidata"]
            items.append(it)
    # wonders: transparent rules
    wonders = []
    rules = []
    w = points(ctx, "unesco_whs", lambda r: not r.get("tentative"))
    if w:
        rules.append({"id": "unesco", "text": "Every UNESCO World Heritage Site in India (whc.unesco.org list), drawn at its listed coordinates."})
        for r in w:
            x, y = project(r["lon"], r["lat"])
            wonders.append({"rule": "unesco", "name": r["name"], "x": round(float(x), 1), "y": round(float(y), 1), "category": r.get("category"), "year": r.get("year_inscribed"), "key": r.get("key"), "url": r.get("url")})
    u = points(ctx, "universities", lambda r: (r.get("nirf_rank") or 999) <= 10)
    if u:
        rules.append({"id": "nirf10", "text": "The ten institutions at the top of the latest NIRF Overall ranking (Ministry of Education)."})
        for r in u:
            x, y = project(r["lon"], r["lat"])
            wonders.append({"rule": "nirf10", "name": r["name"], "x": round(float(x), 1), "y": round(float(y), 1), "category": "knowledge", "rank": r.get("nirf_rank"), "key": r.get("key")})
    big = sorted(points(ctx, "power_plants"), key=lambda r: -(r.get("capacity_mw") or 0))[:5]
    if big:
        rules.append({"id": "power5", "text": "The five largest power stations by capacity in the WRI Global Power Plant Database (2019)."})
        for r in big:
            x, y = project(r["lon"], r["lat"])
            wonders.append({"rule": "power5", "name": r["name"], "x": round(float(x), 1), "y": round(float(y), 1), "category": "energy", "capacity_mw": r.get("capacity_mw"), "key": r.get("key")})
    write_json(f"{SITE_DATA}/points.json", {"types": types, "items": items})
    write_json(f"{SITE_DATA}/wonders.json", {"rules": rules, "items": wonders})
    print("points", len(items), "types", [t["id"] for t in types], "wonders", len(wonders))


def build_history(ctx):
    h = ctx.ds.get("history")
    if h:
        write_json(f"{SITE_DATA}/history.json", h)


def build_advisors(ctx):
    import advisors
    write_json(f"{SITE_DATA}/advisors.json", advisors.build(ctx))
