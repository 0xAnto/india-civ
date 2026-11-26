"""Join normalized datasets to the hex grid and write the frontend data files in site/data/.

Aggregation rules (also shown in the Almanac):
- count fields at district level -> density: value / district area, then the area-weighted
  mean of the densities of the districts that share the hex.
- rate fields at district level -> area-weighted mean of the district rates in the hex.
  The hex is missing if districts with data cover less than half of its sampled area.
- state fields -> every hex of the state takes the state value.
- raster fields -> mean of the hex's sample points.
Hexes in areas that India claims but does not administer are always missing.
"""
import glob, math, os, re, collections
import numpy as np
from common import *
import mechanics
import strengths
import series

NORM = f"{DATA}/normalized"


def load(ds):
    p = f"{NORM}/{ds}.json"
    return read_json(p) if os.path.exists(p) else None


class Ctx:
    def __init__(self):
        self.g = read_json(f"{DATA}/grid/grid.json")
        self.t = read_json(f"{DATA}/grid/terrain.json")
        self.world = read_json(f"{SITE_DATA}/world.json")
        self.land = self.world["land"]
        self.disputed = self.g["disputed"]
        self.S = self.g["samples_per_hex"]
        self.states, self.alias = load_states()
        self.ds = {os.path.basename(p)[:-5]: read_json(p) for p in glob.glob(f"{NORM}/*.json")}
        self.d11_idx = {k: i for i, k in enumerate(self.g["d11_keys"])}
        self.d20_idx = {k: i for i, k in enumerate(self.g["d20_keys"])}
        self.state_idx = {s["id"]: i for i, s in enumerate(self.states)}

    def rows_by_key(self, ds):
        return {str(r["key"]): r for r in self.ds[ds]["rows"]}

    def hex_values(self, ds, field, how=None):
        """Values aligned with world.land (None = missing)."""
        d = self.ds[ds]; meta = d["meta"]; f = d["fields"][field]
        res = meta["resolution"]; typ = how or f["type"]
        rows = self.rows_by_key(ds)
        out = []
        if res == "state":
            byst = {r["state"]: r.get(field) for r in d["rows"]}
            sarea = dict(zip([s["id"] for s in self.states], self.g["state_area_km2"]))
            for i in self.land:
                s = self.g["state"][i]
                v = None if self.disputed[i] >= 0 or s < 0 else byst.get(self.states[s]["id"])
                if v is not None and typ == "count":
                    v = v / sarea[self.states[s]["id"]]  # state total per km² of state
                out.append(v)
            return out
        keys = self.g["d11_keys"] if res == "district2011" else self.g["d20_keys"]
        area = self.g["d11_area_km2"] if res == "district2011" else self.g["d20_area_km2"]
        W = self.g["w11"] if res == "district2011" else self.g["w20"]
        vals = []
        for k, a in zip(keys, area):
            r = rows.get(k); v = None if r is None else r.get(field)
            if v is not None and typ == "count":
                a = (r.get("area_km2") or a) if r else a  # official area when the dataset has it
                v = v / a if a > 0 else None
            vals.append(v)
        for i in self.land:
            if self.disputed[i] >= 0:
                out.append(None); continue
            w = W.get(str(i)) or []
            tot = sum(c for _, c in w)
            num = den = 0.0
            for dd, c in w:
                v = vals[dd]
                if v is not None:
                    num += v * c; den += c
            out.append(num / den if tot and den >= 0.5 * tot else None)
        return out

    def raster(self, key, sub=None):
        arr = self.t[key] if sub is None else self.t[key][sub]
        return [None if self.disputed[i] >= 0 else arr[i] for i in self.land]


def rnd(v, sig=4):
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return None
    if v == 0:
        return 0
    d = max(0, sig - int(math.floor(math.log10(abs(v)))) - 1)
    return round(v, d) if d else int(round(v))


def stats(vals):
    a = np.array([v for v in vals if v is not None], float)
    if a.size == 0:
        return None
    q = np.percentile(a, [2, 25, 50, 75, 98])
    return {"n": int(a.size), "min": rnd(float(a.min())), "max": rnd(float(a.max())), "p2": rnd(q[0]), "q1": rnd(q[1]),
            "median": rnd(q[2]), "q3": rnd(q[3]), "p98": rnd(q[4])}


RAMPS = {
    "people": ["#1b1035", "#4b2377", "#9a3b8a", "#e0645e", "#f9b24a", "#fff3a8"],
    "wealth": ["#1a2a1f", "#29503a", "#3f7f4a", "#86a94a", "#d8c24f", "#fff0a0"],
    "knowledge": ["#101c3a", "#1d3f7a", "#2f6fb0", "#4fa3d8", "#9fd6ef", "#eefaff"],
    "health_good": ["#3b0f1a", "#7a1f2c", "#b8443a", "#e08a4a", "#e9d27a", "#c9eeb0"],
    "health_bad": ["#c9eeb0", "#e9d27a", "#e08a4a", "#b8443a", "#7a1f2c", "#3b0f1a"],
    "land": ["#2a2414", "#5a4a22", "#8a7a32", "#9faa45", "#5e9a3e", "#1f5e2e"],
    "water": ["#2a1a10", "#6a4a2a", "#a08a5a", "#7fb0c0", "#3f88c0", "#16407a"],
    "heat": ["#1d3557", "#457b9d", "#a8dadc", "#f1e3b0", "#e9a03b", "#c0392b"],
    "hazard": ["#1d2b22", "#3f4f2a", "#8a7a2a", "#d08a2a", "#e0502a", "#ff2a4a"],
    "elev": ["#2f5a2e", "#7f9a4a", "#c9b87a", "#a07a5a", "#8a8a8a", "#f4f6f8"],
    "lights": ["#05070f", "#1a1640", "#4a2a6a", "#a0508a", "#f0a060", "#fff6c0"],
    "strength": ["#a8432f", "#d98b62", "#e8dcc0", "#79b98a", "#1f7a4d"],  # below expectation = rust, above = green
    "diverge": ["#2c7bb6", "#88c0dd", "#e8ecd8", "#f4b06a", "#d7301f"],
}

GROUPS = [
    {"id": "people", "name": "People"}, {"id": "prosperity", "name": "Prosperity & work"},
    {"id": "knowledge", "name": "Knowledge"}, {"id": "health", "name": "Health & living"},
    {"id": "land", "name": "Land & resources"}, {"id": "climate", "name": "Climate & hazards"},
    {"id": "faith", "name": "Faith & society"}, {"id": "strengths", "name": "Hidden strengths"}, {"id": "change", "name": "Change over time"}, {"id": "yields", "name": "Civilization yields"},
]


def L(id, group, name, emoji, ds, field, ramp, unit, scale="linear", higher_is="neutral", desc="", how=None, fmt=None, domain=None, quick=False):
    return dict(id=id, group=group, name=name, emoji=emoji, ds=ds, field=field, ramp=RAMPS[ramp], unit=unit, scale=scale,
                higher_is=higher_is, description=desc, how=how, format=fmt, domain=domain, quick=quick)


LENSES = [
    L("population", "people", "Population density", "👥", "census2011_district", "population", "people", "people / km²", "log", desc="Census 2011 district population divided by the official PCA district area, then the area-weighted mean over the districts in the hex. Every hex of one district has the same density, so dense cities inside large districts are averaged out.", quick=True),
    L("settlement", "people", "Settlement density (modelled)", "🏘️", "raster:gpw2020", None, "people", "people / km²", "log", desc="Gridded Population of the World v4, 2020 (NASA SEDAC), sampled from the NASA GIBS colour-binned layer and averaged in the hex. The colour map stops at ≥ 1,000 people/km², so dense urban cores are capped at 1,000. This is a modelled estimate, not a census count."),
    L("urban", "people", "Urbanisation", "🏙️", "census2011_district", "urban_share", "people", "% of population", desc="Census 2011 urban population as a share of district population (PCA). National value 31.1%.", quick=False),
    L("sex_ratio", "people", "Sex ratio", "⚖️", "census2011_district", "sex_ratio", "diverge", "females per 1,000 males", desc="Census 2011 females per 1,000 males (all ages). The colour scale centres on the national value, 943.", domain=[850, 943, 1050], higher_is="neutral"),
    L("child_sex_ratio", "people", "Child sex ratio (0–6)", "🧒", "census2011_district", "child_sex_ratio", "diverge", "girls per 1,000 boys aged 0–6", desc="Census 2011 (PCA): girls per 1,000 boys aged 0–6. National value 918. The scale centres on 918.", domain=[800, 918, 1000]),
    L("sex_ratio_birth", "people", "Sex ratio at birth", "👶", "nfhs5_district", "sex_ratio_birth", "diverge", "females per 1,000 males", desc="NFHS-5 (2019–21): sex ratio at birth for children born in the last five years. Survey estimate; small districts have wide confidence intervals.", domain=[850, 950, 1050]),
    L("st_share", "people", "Scheduled Tribes", "🏔️", "census2011_district", "pct_st", "people", "% of population", desc="Census 2011 Scheduled Tribe population as a share of district population."),
    L("gsdp_pc", "prosperity", "Income per person", "💰", "gsdp_state", "pc_nsdp_current", "wealth", "₹ per person", desc="Per-capita Net State Domestic Product at current prices, 2023-24 (MoSPI). State level: every hex of a state has the state value.", quick=True),
    L("lights", "prosperity", "Night lights", "🌃", "raster:nightlights", None, "lights", "relative brightness (0–255)", "linear", desc="Brightness of the NASA Black Marble 2016 night-light composite (VIIRS), sampled from the GIBS image tiles. This is a relative visual index, not calibrated radiance. Night lights track electrification, settlement and economic activity.", higher_is="neutral", quick=True),
    L("unemployment", "prosperity", "Unemployment", "📉", "plfs_state", "ur", "health_bad", "% of labour force", desc="PLFS 2025 unemployment rate, usual status, age 15+. State level.", higher_is="worse"),
    L("wpr_female", "prosperity", "Women at work", "👩‍🔧", "plfs_state", "wpr_female", "wealth", "% of women 15+", desc="PLFS 2025 worker population ratio for women aged 15+, usual status. State level.", higher_is="better"),
    L("mfg_share", "prosperity", "Manufacturing share", "🏭", "gsva_sector_state", "share_mfg", "wealth", "% of GSVA", desc="Manufacturing share of Gross State Value Added, current prices, 2023-24 (MoSPI). State level.", quick=True),
    L("nonfarm", "prosperity", "Non-farm workers", "🧰", "census2011_district", "pct_other_workers", "wealth", "% of workers", desc="Census 2011 'other workers' (not cultivators, agricultural labourers or household industry) as a share of all workers: manufacturing, trade, services, government."),
    L("car", "prosperity", "Households with a car", "🚗", "census2011_district", "pct_hh_car", "wealth", "% of households", desc="Census 2011 households that own a car, jeep or van, per 100 households (PCA household count)."),
    L("literacy", "knowledge", "Literacy", "📖", "census2011_district", "literacy_rate_7plus", "knowledge", "% of people aged 7+", desc="Census 2011 literacy rate, official definition: literates divided by the population aged 7 and over (PCA). National value 72.98%.", higher_is="better", quick=True),
    L("literacy_f", "knowledge", "Female literacy", "📚", "census2011_district", "literacy_rate_7plus_female", "knowledge", "% of females aged 7+", desc="Census 2011 female literates divided by the female population aged 7 and over (PCA).", higher_is="better"),
    L("women_literate", "knowledge", "Women's literacy", "📚", "nfhs5_district", "women_literate", "knowledge", "% of women 15–49", desc="NFHS-5 (2019–21): literate women aged 15–49.", higher_is="better"),
    L("women_10yr", "knowledge", "Women with 10+ years of school", "🎓", "nfhs5_district", "women_10yr_school", "knowledge", "% of women 15–49", desc="NFHS-5 (2019–21): women aged 15–49 with 10 or more years of schooling.", higher_is="better"),
    L("graduates", "knowledge", "Graduates", "🧑‍🎓", "census2011_district", "pct_graduate", "knowledge", "% of persons in education table", desc="Census 2011 graduates and above as a share of the persons in the education-level table of the district.", higher_is="better"),
    L("internet", "knowledge", "Internet at home (2011)", "🌐", "census2011_district", "pct_hh_internet", "knowledge", "% of households", desc="Census 2011 households with an internet connection per 100 households. A 2011 baseline: access has grown very much since.", higher_is="better"),
    L("stunting", "health", "Child stunting", "📏", "nfhs5_district", "stunting", "health_bad", "% of children <5", desc="NFHS-5 (2019–21): children under five who are stunted (height-for-age).", higher_is="worse", quick=True),
    L("inst_births", "health", "Institutional births", "🏥", "nfhs5_district", "institutional_births", "health_good", "% of births", desc="NFHS-5 (2019–21): births in the 5 years before the survey that took place in a health facility.", higher_is="better"),
    L("immunisation", "health", "Full immunisation", "💉", "nfhs5_district", "full_immunisation", "health_good", "% of children 12–23 months", desc="NFHS-5 (2019–21): children aged 12–23 months fully vaccinated (based on card or mother's recall).", higher_is="better"),
    L("insurance", "health", "Health insurance", "🛡️", "nfhs5_district", "health_insurance", "health_good", "% of households", desc="NFHS-5 (2019–21): households with any member covered by a health insurance or financing scheme.", higher_is="better"),
    L("anaemia", "health", "Anaemia in women", "🩸", "nfhs5_district", "women_anaemia", "health_bad", "% of women 15–49", desc="NFHS-5 (2019–21): all women aged 15–49 who are anaemic.", higher_is="worse"),
    L("sanitation", "health", "Improved sanitation", "🚿", "nfhs5_district", "improved_sanitation", "health_good", "% of population", desc="NFHS-5 (2019–21): population in households that use an improved sanitation facility.", higher_is="better"),
    L("water_access", "health", "Improved drinking water", "🚰", "nfhs5_district", "improved_water", "water", "% of population", desc="NFHS-5 (2019–21): population in households with an improved drinking-water source.", higher_is="better"),
    L("clean_fuel", "health", "Clean cooking fuel", "🔥", "nfhs5_district", "clean_cooking_fuel", "health_good", "% of population", desc="NFHS-5 (2019–21): population in households that cook with clean fuel (electricity, LPG/natural gas, biogas).", higher_is="better"),
    L("imr", "health", "Infant mortality", "🍼", "srs_state", "imr", "health_bad", "deaths per 1,000 live births", desc="Sample Registration System 2024: infant mortality rate. State level; smaller states use a 3-year average.", higher_is="worse"),
    L("life_exp", "health", "Life expectancy", "⏳", "srs_state", "life_exp", "health_good", "years at birth", desc="SRS abridged life tables 2020–24: life expectancy at birth. State level; published for the larger states only.", higher_is="better"),
    L("elevation", "land", "Elevation", "⛰️", "raster:elev", None, "elev", "m above sea level", "linear", desc="Mean elevation of the hex from AWS Terrain Tiles (SRTM/GMTED-derived, zoom 7, ~1.2 km pixels).", domain=[0, 6000]),
    L("forest", "land", "Forest & woodland", "🌳", "raster:forest", None, "land", "% of hex", desc="MODIS land cover 2023 (IGBP classes 1–5 forest and 8 woody savanna) share of the hex sample points. Satellite classification at ~500 m; it differs from the Forest Survey of India definition of forest cover.", higher_is="neutral", quick=True),
    L("cropland", "land", "Cropland", "🌾", "raster:crop", None, "land", "% of hex", desc="MODIS land cover 2023: cropland (12) and cropland/natural mosaic (14) share of the hex sample points.", higher_is="neutral"),
    L("forest_isfr", "land", "Forest cover (ISFR)", "🌲", "forest_district", "forest_cover_pct", "land", "% of district area", desc="India State of Forest Report 2023 (Forest Survey of India): forest cover (very dense + moderately dense + open forest) as a share of district area. Official satellite-based assessment.", higher_is="neutral"),
    L("foodgrain_out", "land", "Foodgrain output", "🌾", "crop_district", "foodgrains_prod", "land", "tonnes per km²", "log", desc="District foodgrain production 2022-23 (Directorate of Economics & Statistics, crop production statistics) per km² of district. District sums run above the national estimate, so use this for the pattern, not totals.", higher_is="neutral", quick=False),
    L("rice_yield", "land", "Rice yield", "🍚", "crop_district", "rice_yield", "land", "tonnes per hectare", desc="District rice yield 2022-23 (DES crop production statistics). Districts with very small rice area can show unstable values.", higher_is="better"),
    L("wheat_yield", "land", "Wheat yield", "🌾", "crop_district", "wheat_yield", "land", "tonnes per hectare", desc="District wheat yield 2022-23 (DES crop production statistics).", higher_is="better"),
    L("sugarcane", "land", "Sugarcane output", "🎋", "crop_district", "sugarcane_prod", "land", "tonnes per km²", "log", desc="District sugarcane production 2022-23 per km² of district (DES).", higher_is="neutral"),
    L("cotton", "land", "Cotton output", "☁️", "crop_district", "cotton_prod", "land", "bales (170 kg) per km²", "log", desc="District cotton production 2022-23 per km² of district (DES).", higher_is="neutral"),
    L("minerals", "land", "Mineral production", "⛏️", "minerals_state", "value_rs_crore", "elev", "₹ crore per km² of state", "log", desc="Value of mineral production 2023-24 (provisional, Indian Bureau of Mines; excludes atomic minerals, fuel minerals and minor minerals as defined by IBM), divided by state area. State level.", higher_is="neutral"),
    L("coal", "land", "Coal production", "🪨", "coal_state", "raw_coal_mt", "elev", "million tonnes per km² of state", "log", desc="Raw coal production 2024-25 (provisional, Ministry of Coal Directory) divided by state area. State level; only coal-producing states have values.", higher_is="neutral"),
    L("irrigation", "land", "Irrigated farmland", "💧", "crop_state", "irrigation_share_pct", "water", "% of net sown area", desc="Net irrigated area as a share of net sown area, Land Use Statistics 2022-23. State level.", higher_is="neutral"),
    L("grain_yield", "land", "Foodgrain yield", "🌾", "crop_state", "foodgrains_yield_all_kgha", "land", "kg per hectare", desc="Foodgrain production per hectare of foodgrain area, 2023-24 (Ministry of Agriculture & Farmers Welfare). State level.", higher_is="better"),
    L("rainfall", "climate", "Annual rainfall", "🌧️", "raster:precip", None, "water", "mm per year", desc="WorldClim 2.1 (1970–2000 climate normals, 10 arc-minute) annual precipitation averaged in the hex.", quick=True),
    L("monsoon", "climate", "Monsoon dependence", "🌦️", "raster:monsoon_share", None, "water", "% of annual rain in Jun–Sep", desc="Share of annual rainfall that falls in June–September (WorldClim 2.1 monthly normals)."),
    L("heat", "climate", "Hottest month", "🌡️", "raster:temp_hot", None, "heat", "°C mean of hottest month", desc="Mean temperature of the hottest month, WorldClim 2.1 normals 1970–2000.", domain=[0, 37]),
    L("flood", "climate", "Flood frequency", "🌊", "raster:flood", None, "hazard", "flood events 1985–2003", desc="Number of large flood events 1985–2003 (Dartmouth Flood Observatory extents) from SEDAC Global Natural Disaster Hotspots, averaged in the hex. Old period; use only for broad patterns.", higher_is="worse"),
    L("drought", "climate", "Drought frequency", "🏜️", "raster:drought", None, "hazard", "drought events 1980–2000", desc="Number of drought events 1980–2000 (weighted anomaly of standardized precipitation) from SEDAC Global Natural Disaster Hotspots.", higher_is="worse"),
    L("cyclone", "climate", "Cyclone frequency", "🌀", "raster:cyclone", None, "hazard", "tropical cyclones 1980–2000", desc="Tropical cyclone frequency 1980–2000 from SEDAC Global Natural Disaster Hotspots (UNEP/GRID-Europe).", higher_is="worse"),
    L("landslide", "climate", "Landslide hazard", "🪨", "raster:landslide", None, "hazard", "hazard class (1–9)", desc="Landslide hazard class from SEDAC Global Natural Disaster Hotspots (NGI): combines slope, soil, precipitation and seismic triggers.", higher_is="worse"),
    L("faith_div", "faith", "Religious diversity", "🕉️", "derived:faith_div", None, "people", "diversity index (0–1)", desc="Census 2011 religion counts: 1 − Σ share², the probability that two random residents of the district report different religions. 0 means one religion only. This lens shows diversity, not any one religion.", higher_is="neutral"),
]


def raster_values(ctx, key):
    if key == "forest":
        return [None if v is None else v for v in _sum_frac(ctx, [1, 2, 3, 4, 5, 8])]
    if key == "crop":
        return _sum_frac(ctx, [12, 14])
    return ctx.raster(key)


def _sum_frac(ctx, classes):
    out = []
    for i in ctx.land:
        if ctx.disputed[i] >= 0:
            out.append(None); continue
        vs = [ctx.t["lc_frac"][str(c)][i] for c in classes]
        out.append(None if all(v is None for v in vs) else sum(v or 0 for v in vs))
    return out


def faith_div(ctx):
    rows = {}
    for r in ctx.ds["census2011_district"]["rows"]:
        parts = [r.get(k) for k in ("hindus", "muslims", "christians", "sikhs", "buddhists", "jains", "other_religions")]
        tot = sum(p or 0 for p in parts)
        rows[str(r["key"])] = None if not tot or any(p is None for p in parts) else 1 - sum((p / tot) ** 2 for p in parts)
    ds = {"meta": dict(ctx.ds["census2011_district"]["meta"]), "fields": {"v": {"type": "rate"}}, "rows": [{"key": k, "v": v} for k, v in rows.items()]}
    ctx.ds["_faith_div"] = ds
    return ctx.hex_values("_faith_div", "v")


def build_lenses(ctx, specs=LENSES):
    out = []
    os.makedirs(f"{SITE_DATA}/lens", exist_ok=True)
    for spec in specs:
        ds = spec["ds"]
        if ds.startswith("raster:"):
            vals = raster_values(ctx, ds.split(":")[1]); source = RASTER_SRC[ds.split(":")[1]]
            kind = "satellite" if source != "worldclim" and source != "sedac_ndh" and source != "gpw" else "modelled"
            year = RASTER_YEAR[ds.split(":")[1]]; res = "raster"
        elif ds == "derived:faith_div":
            vals = faith_div(ctx); source = "census2011_district"; kind = "official"; year = "2011"; res = "district2011"
        else:
            if ds not in ctx.ds:
                print("skip lens (no data)", spec["id"]); continue
            vals = ctx.hex_values(ds, spec["field"], spec["how"]); m = ctx.ds[ds]["meta"]
            source, kind, year, res = ds, m.get("kind", "official"), m.get("reference_year"), m["resolution"]
        st = stats(vals)
        if not st or st["n"] < 50:
            print("skip lens (too few values)", spec["id"], st and st["n"]); continue
        if spec["scale"] == "log" and st["p2"] is not None and st["p2"] <= 0:
            pos = [v for v in vals if v and v > 0]; st["p2"] = rnd(float(np.percentile(pos, 2)))
        lens = {k: v for k, v in spec.items() if k not in ("ds", "field", "how") and v is not None}
        lens.update(source=source, kind=kind, year=year, resolution=res, stats=st,
                    coverage=round(st["n"] / sum(1 for i in ctx.land if ctx.disputed[i] < 0), 3))
        out.append(lens)
        write_json(f"{SITE_DATA}/lens/{spec['id']}.json", {"values": [rnd(v) for v in vals]})
    return out


RASTER_SRC = {"gpw2020": "gpw", "nightlights": "black_marble", "elev": "terrain_tiles", "forest": "modis_lc", "crop": "modis_lc",
              "precip": "worldclim", "monsoon_share": "worldclim", "temp_hot": "worldclim", "flood": "sedac_ndh", "drought": "sedac_ndh",
              "cyclone": "sedac_ndh", "landslide": "sedac_ndh"}
RASTER_YEAR = {"gpw2020": "2020", "nightlights": "2016", "elev": "—", "forest": "2023", "crop": "2023", "precip": "1970–2000",
               "monsoon_share": "1970–2000", "temp_hot": "1970–2000", "flood": "1985–2003", "drought": "1980–2000", "cyclone": "1980–2000", "landslide": "2000"}


def build_tables(ctx):
    """Explorer tables: one per resolution."""
    tables = {}
    for res, label in (("district2011", "Districts (Census 2011 boundaries)"), ("district2020", "Districts (2019–21 boundaries)"), ("state", "States & UTs"), ("city", "Cities")):
        dsets = [k for k, d in ctx.ds.items() if not k.startswith("_") and d["meta"].get("resolution") == res and d.get("rows")]
        if not dsets:
            continue
        fields, rows = {}, {}
        for ds in sorted(dsets):
            d = ctx.ds[ds]
            for fk, f in d["fields"].items():
                if f.get("type") not in ("count", "rate", "value"):
                    continue
                if any(isinstance(r.get(fk), (dict, list)) for r in d["rows"][:5]):
                    continue
                fields[f"{ds}.{fk}"] = {"name": f.get("name", fk), "unit": f.get("unit", ""), "type": f["type"], "ds": ds,
                                        "higher_is": f.get("higher_is", "neutral"), "description": f.get("description", "")}
            for r in d["rows"]:
                k = str(r["key"])
                row = rows.setdefault(k, {"key": k, "name": r.get("name") or k, "state": r.get("state")})
                for fk in d["fields"]:
                    if f"{ds}.{fk}" in fields:
                        row[f"{ds}.{fk}"] = rnd(r.get(fk)) if isinstance(r.get(fk), (int, float)) else r.get(fk)
        if res == "city":
            for r in rows.values():
                c = ctx.rows_by_key("cities")[r["key"]]
                r["lat"], r["lon"] = c["lat"], c["lon"]
        rl = list(rows.values())
        tables[res] = {"id": res, "name": label, "datasets": sorted(dsets), "fields": fields, "rows": rl}
        base = {"key": [r["key"] for r in rl], "name": [r["name"] for r in rl], "state": [r.get("state") for r in rl]}
        if res == "city":
            base.update(lat=[r["lat"] for r in rl], lon=[r["lon"] for r in rl])
        cols = {f: [r.get(f) for r in rl] for f in fields}
        write_json(f"{SITE_DATA}/table_{res}.json", {"id": res, "name": label, "datasets": sorted(dsets), "fields": fields, "base": base, "cols": cols})
    return [{"id": t["id"], "name": t["name"], "datasets": t["datasets"], "n": len(t["rows"]), "nfields": len(t["fields"])} for t in tables.values()]


def build_sources(ctx):
    core = read_json(f"{DATA}/meta/core_sources.json")
    out = list(core)
    for k, d in sorted(ctx.ds.items()):
        if k.startswith("_"):
            continue
        m = dict(d["meta"]); m["fields"] = len(d.get("fields", {})); m["rows"] = len(d.get("rows", []))
        note = f"{DATA}/meta/{k}.md"
        if os.path.exists(note):
            m["coverage_note"] = open(note).read()[:6000]
        out.append(m)
    write_json(f"{SITE_DATA}/sources.json", out)
    write_sources_md(out)
    return out


GAP_LINE = re.compile(r"not reached|CAPTCHA|HTTP [45]\d\d|\b40[34]\b|blocked|unreachable", re.I)
GAP_HEAD = re.compile(r"^## .*(tried|not used|not reached|not obtained|missing|not built|problems)", re.I)


def write_sources_md(srcs):
    """SOURCES.md: one table of every source, then the gap sections of each coverage note."""
    cell = lambda v: str(v or "—").replace("|", "/").replace("\n", " ")
    md = ["# Sources", "", "Generated by `pipeline/publish.py` from the dataset metadata. Do not edit by hand.", "",
          "Kind: official = government statistics; modelled = derived or estimated; satellite = remote sensing; curated = compiled from open registers (Wikidata, Wikipedia); historical = scholarship.", "",
          "| Id | Dataset | Publisher | Reference year | Kind | Licence | Link |", "|---|---|---|---|---|---|---|"]
    for m in srcs:
        md.append(f"| `{cell(m.get('id'))}` | {cell(m.get('name'))} | {cell(m.get('source_org'))} | {cell(m.get('reference_year'))} | {cell(m.get('kind'))} | {cell(m.get('license'))} | {m.get('landing_url') or m.get('url') or '—'} |")
    md += ["", "# Data gaps: sources tried and not reached or not used", ""]
    for m in srcs:
        f = f"{DATA}/meta/{m.get('id')}.md"
        note, keep, out = (open(f).read() if os.path.exists(f) else ""), False, []
        for line in note.splitlines():
            if line.startswith("## "):
                keep = bool(GAP_HEAD.match(line))
                continue
            if keep or GAP_LINE.search(line):
                out.append(line)
        if any(l.strip() for l in out):
            md += [f"## `{m.get('id')}`", *out, ""]
    open(f"{ROOT}/SOURCES.md", "w").write("\n".join(md) + "\n")


def main():
    ctx = Ctx()
    hs_lenses, hs_models = strengths.build(ctx, L)
    write_json(f"{SITE_DATA}/strengths.json", {"z_flag": strengths.Z_FLAG, "models": hs_models})
    lenses = build_lenses(ctx, LENSES + hs_lenses)
    lenses += series.build(ctx, RAMPS, stats, rnd)
    ylenses, nation, states_out = mechanics.build(ctx, lenses)
    tables = build_tables(ctx)
    write_json(f"{SITE_DATA}/lenses.json", {"groups": GROUPS, "lenses": lenses + ylenses, "tables": tables})
    build_sources(ctx)
    write_json(f"{SITE_DATA}/nation.json", nation)
    write_json(f"{SITE_DATA}/states.json", states_out)
    mechanics.build_cities(ctx)
    mechanics.build_points(ctx)
    mechanics.build_lines(ctx)
    mechanics.build_history(ctx)
    mechanics.build_advisors(ctx)
    adv = read_json(f"{SITE_DATA}/advisors.json"); adv.append(strengths.advisor(hs_models))
    write_json(f"{SITE_DATA}/advisors.json", adv)
    print("lenses", len(lenses) + len(ylenses), "tables", [(t["id"], t["n"], t["nfields"]) for t in tables])


if __name__ == "__main__":
    main()
