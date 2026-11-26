"""Build power_plants and airports. Run: .venv/bin/python -I pipeline/build_infra_power_air.py"""
import csv, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from infra_common import *

def num(s):
    try: return float(s)
    except (TypeError, ValueError): return None

# ---- power_plants
rows = []
for r in csv.DictReader(open(os.path.join(RAW, "global_power_plant_database.csv"))):
    if r["country"] != "IND": continue
    lat, lon = num(r["latitude"]), num(r["longitude"])
    if lat is None or lon is None or not in_india(lat, lon): continue
    cy = num(r["commissioning_year"])
    rows.append({"key": r["gppd_idnr"], "name": r["name"], "lat": round(lat, 5), "lon": round(lon, 5),
                 "category": r["primary_fuel"], "state": state_of(lat, lon),
                 "capacity_mw": num(r["capacity_mw"]), "commissioning_year": int(cy) if cy else None,
                 "owner": r["owner"] or None, "other_fuels": "; ".join(x for x in (r["other_fuel1"], r["other_fuel2"], r["other_fuel3"]) if x) or None,
                 "source_ids": {"gppd": r["gppd_idnr"], "wepp": r["wepp_id"] or None}})
write("power_plants", {
    "name": "Power plants in India (WRI Global Power Plant Database v1.3)",
    "source_org": "World Resources Institute (Global Power Plant Database)",
    "url": "https://raw.githubusercontent.com/wri/global-power-plant-database/master/output_database/global_power_plant_database.csv",
    "landing_url": "https://datasets.wri.org/dataset/globalpowerplantdatabase",
    "published": "2021-06-02", "reference_year": "2019", "resolution": "point",
    "license": "CC BY 4.0", "update_frequency": "one-off (WRI stopped updating after v1.3)", "kind": "curated",
    "limitations": "Capacity data is from about 2018-2019. Plants that open later are missing. Some fuel types (solar, wind) have low coverage of small plants. Coordinates of some plants have low precision.",
    "method": "Filter country == IND. Keep rows with coordinates inside India's bounding box. State from point-in-polygon on data/raw boundaries (nearest state within 0.25 degrees for coastal points). Capacity stays in MW."},
    sub(capacity_mw=F("Installed capacity", "MW", "count", "Nameplate capacity", "neutral"),
        commissioning_year=F("Commissioning year", "year", "value", "Year of commissioning, where the source gives it"),
        owner=F("Owner", None, "text", "Owner as in the source"), other_fuels=F("Other fuels", None, "text", "Secondary fuels")), rows)

# ---- airports
oa = [x for x in csv.DictReader(open(os.path.join(RAW, "airports.csv"))) if x["iso_country"] == "IN"]
keep = [x for x in oa if x["type"] in ("large_airport", "medium_airport") or (x["scheduled_service"] == "yes" and x["type"] in ("small_airport", "medium_airport", "large_airport"))]
# AAI passengers (FY 2025-26, Annexure III C: total passengers)
txt = open(os.path.join(RAW, "aai", "a3.txt"), encoding="utf-8").read()
txt = txt[txt.index("ANNEXURE-III C"):]
aai = {}
for ln in txt.splitlines():
    m = re.match(r"^\s+(\d+)\s+(.*?)\s{2,}([\d]+)\s+([\d]+)\s+(-|[-\d.]+%)\s+([\d]+)\s+([\d]+)\s+(-|[-\d.]+%)\s*$", ln)
    if not m: continue
    nm = re.findall(r"[A-Z][A-Z0-9 ()&.,/'-]+", m.group(2))
    name = nm[-1].strip() if nm else None
    # Hindi text may be glued to the name; keep the ASCII uppercase tail
    if name: aai.setdefault(name, int(m.group(6)))
print("AAI rows parsed:", len(aai))
MANUAL = {  # AAI name -> IATA or OurAirports ident (AAI names differ from OurAirports names)
 "AGRA":"AGR","MUMBAI (MIAL)":"BOM","PATNA":"PAT","DELHI":"DEL","AYODHYA":"AYJ","KOZHIKODE":"CCJ",
 "BARAPANI (SHILLONG)":"SHL","COOCHBEHER":"COH","CUDDAPAH":"CDP","GAGGAL (KANGRA)":"DHM","HUBBALI":"HBX",
 "MOHANBARI (DIBRUGARH)":"DIB","MYSURU":"MYQ","PAKYONG":"PYG","RUPSI":"RUP","SATNA":"TNI","SHOLAPUR":"SSE",
 "TEZU":"TEI","ALIGARH":"HRH","AZAMGARH":"AZH","CHITRAKOOT":"CWK","DATIA":"DPP","JEYPORE":"PYB","PASIGHAT":"IXT",
 "SHIVAMOGGA":"RQY","PURNEA":"VEPU","PITHORAGARH":"VIDF","JUHU":"VAJJ","MUNDRA":"VAMA","SHIMLA":"SLV","VIJAYANAGAR":"VDY","GOA (MOPA)":"VOGA","HYDERABAD (BEGUMPET)":"VOHY","BENGALURU (HAL)":"VOBG","NASIK (HAL OZAR)":"VAOZ"}
def norm(s): return re.sub(r"[^a-z0-9 ]", "", s.lower().replace("(", " ").replace(")", " ")).strip()
pool = [x for x in oa if x["type"] in ("large_airport","medium_airport","small_airport")]
by_iata = {k: x for x in pool for k in (x["iata_code"], x["ident"]) if k}
used = {}
unm = []
for name, pax in aai.items():
    base = norm(re.sub(r"\(.*?\)", "", name)); full = norm(name)
    cand = []
    if name in MANUAL: cand = [by_iata[MANUAL[name]]]
    else:
        for x in keep:
            hay = norm(x["municipality"]) + "|" + norm(x["name"])
            if base and (norm(x["municipality"]) == base or base in norm(x["name"]).split(" airport")[0] or base == norm(x["municipality"]).split(" ")[0]):
                cand.append(x)
        sched = [x for x in cand if x["scheduled_service"] == "yes" and x["iata_code"]]
        cand = sched or cand
    if len(cand) >= 1:
        cand.sort(key=lambda x: (x["type"] != "large_airport", x["type"] != "medium_airport"))
        if len(cand) > 1: print("AMBIG", name, [(c["iata_code"], c["name"]) for c in cand][:4])
        used.setdefault(cand[0]["ident"], (name, pax))
    else: unm.append(name)
print("AAI unmatched:", unm)
keepids = {x["ident"] for x in keep}
keep = keep + [x for x in pool if x["ident"] in used and x["ident"] not in keepids]
rows = []
for x in keep:
    lat, lon = float(x["latitude_deg"]), float(x["longitude_deg"])
    a = used.get(x["ident"])
    rows.append({"key": x["ident"], "name": x["name"], "lat": round(lat, 5), "lon": round(lon, 5),
                 "category": x["type"], "state": state_of(lat, lon), "iata": x["iata_code"] or None,
                 "icao": x["icao_code"] or None, "scheduled_service": x["scheduled_service"] == "yes",
                 "municipality": x["municipality"] or None,
                 "passengers": a[1] if a else None, "passengers_year": "2025-26" if a else None,
                 "passengers_aai_name": a[0] if a else None,
                 "source_ids": {"ourairports": x["id"]}})
write("airports", {
    "name": "Airports in India (OurAirports) with AAI passenger traffic FY 2025-26",
    "source_org": "OurAirports (public domain); Airports Authority of India (traffic statistics)",
    "url": "https://davidmegginson.github.io/ourairports-data/airports.csv",
    "landing_url": "https://ourairports.com/data/ ; https://www.aai.aero/en/business-opportunities/aai-traffic-news",
    "published": "2026-11-26", "reference_year": "2025-26", "resolution": "point", "license": "OurAirports: public domain. AAI traffic: Government of India open statistics.",
    "update_frequency": "OurAirports: continuous; AAI: monthly", "kind": "curated",
    "limitations": "Passengers are total (international + domestic) for April 2025 - March 2026 from AAI Annexure III C of the March 2026 traffic report. Only airports that AAI lists (about 148) have a value. Private airports and some JV/PPP airports may not be in the AAI list. Name matching between AAI and OurAirports uses municipality and name and was checked by hand for unmatched names.",
    "method": "India rows in OurAirports with type large_airport or medium_airport, or with scheduled_service = yes (small airports and heliports only if scheduled). AAI passengers parsed from the PDF text (pdftotext -layout) and joined by name. Unmatched AAI names are in data/meta/airports.md."},
    sub(iata=F("IATA code", None, "text", "IATA code"), icao=F("ICAO code", None, "text", "ICAO code"),
        scheduled_service=F("Scheduled service", None, "text", "True if OurAirports lists scheduled passenger service"),
        municipality=F("Municipality", None, "text", "Served place"),
        passengers=F("Passengers FY 2025-26", "persons", "count", "Total passengers (international + domestic), AAI, April 2025 - March 2026", "neutral"),
        passengers_year=F("Passengers fiscal year", None, "text", "Fiscal year of the passengers value"),
        passengers_aai_name=F("AAI airport name", None, "text", "Name in the AAI table that was joined")), rows)
if os.environ.get("DEBUG"):
    for ident,(n,p) in sorted(used.items(), key=lambda kv: kv[1][0]):
        x=[k for k in oa if k["ident"]==ident][0]; print(n,"->",x["iata_code"],x["name"],"|",x["municipality"])
    import difflib
    for n in unm:
        k=norm(re.sub(r"\(.*?\)","",n)).split()[0]
        print("??",n,[(x["iata_code"],x["name"],x["municipality"],x["type"],x["scheduled_service"]) for x in oa if k[:5] in norm(x["name"]+" "+x["municipality"]+" "+x["keywords"])][:4])
lost = [(n, p) for n, p in aai.items() if n not in {v[0] for v in used.values()}]
print("AAI not carried:", lost, "sum parsed", sum(aai.values()), "sum carried", sum(v[1] for v in used.values()))
