"""Build nfhs5_district and nfhs5_state from the jvargh7 mirror of the NFHS-5 fact sheets."""
import csv, json, re, collections, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "raw" / "health"
OUT = ROOT / "data" / "normalized"

# NFHS indicator number -> (field, name, unit, higher_is)
IND = {
 1: ("female_ever_school", "Female population age 6+ who ever attended school", "%", "better"),
 3: ("sex_ratio_total", "Sex ratio of total population", "females per 1,000 males", "neutral"),
 4: ("sex_ratio_birth", "Sex ratio at birth (births in last 5 years)", "females per 1,000 males", "better"),
 7: ("electricity", "Population in households with electricity", "%", "better"),
 8: ("improved_water", "Population in households with improved drinking-water source", "%", "better"),
 9: ("improved_sanitation", "Population in households using improved sanitation facility", "%", "better"),
 10: ("clean_cooking_fuel", "Households using clean fuel for cooking", "%", "better"),
 12: ("health_insurance", "Households with a member covered by health insurance/financing scheme", "%", "better"),
 14: ("women_literate", "Women who are literate", "%", "better"),
 15: ("women_10yr_school", "Women with 10 or more years of schooling", "%", "better"),
 16: ("child_marriage_women", "Women age 20-24 married before age 18", "%", "worse"),
 33: ("anc_4visits", "Mothers with at least 4 antenatal care visits", "%", "better"),
 42: ("institutional_births", "Institutional births", "%", "better"),
 45: ("skilled_birth_attendance", "Births attended by skilled health personnel", "%", "better"),
 46: ("caesarean_births", "Births delivered by caesarean section", "%", "neutral"),
 49: ("full_immunisation", "Children age 12-23 months fully vaccinated (card or recall)", "%", "better"),
 61: ("diarrhoea", "Children with diarrhoea in the 2 weeks before survey", "%", "worse"),
 68: ("exclusive_breastfeeding", "Children under 6 months exclusively breastfed", "%", "better"),
 73: ("stunting", "Children under 5 who are stunted (height-for-age)", "%", "worse"),
 74: ("wasting", "Children under 5 who are wasted (weight-for-height)", "%", "worse"),
 76: ("underweight", "Children under 5 who are underweight (weight-for-age)", "%", "worse"),
 78: ("women_bmi_low", "Women with BMI below normal (<18.5)", "%", "worse"),
 79: ("women_overweight", "Women who are overweight or obese (BMI >= 25)", "%", "worse"),
 81: ("child_anaemia", "Children age 6-59 months who are anaemic", "%", "worse"),
 84: ("women_anaemia", "All women age 15-49 who are anaemic", "%", "worse"),
 88: ("women_high_sugar", "Women with high or very high blood sugar or on medicine", "%", "worse"),
 91: ("men_high_sugar", "Men with high or very high blood sugar or on medicine", "%", "worse"),
 94: ("women_high_bp", "Women with elevated blood pressure or on medicine", "%", "worse"),
 97: ("men_high_bp", "Men with elevated blood pressure or on medicine", "%", "worse"),
}

STATES = {r["id"]: r for r in csv.DictReader(open(ROOT / "data/ref/states.csv"))}
def norm(s): return re.sub(r"[^a-z]", "", s.lower())
STATE_ID = {}
for i, r in STATES.items():
    for n in [r["name"]] + [a for a in r["aliases"].split("|") if a]:
        STATE_ID[norm(n)] = i
# the mirror strips "&" from some state names
STATE_ID.update({norm(k): v for k, v in {
    "Andaman Nicobar Islands": "AN", "Dadra Nagar Haveli Daman Diu": "DH",
    "Jammu Kashmir": "JK", "NCT Delhi": "DL",
    "Dadra & Nagar Haveli and Daman & Diu": "DH"}.items()})

# Explicit district alias table: state id -> {NFHS name: districts2020.csv name}
ALIAS = {
 "AP": {"Y.S.R.": "Y.S.R. Kadapa", "Sri Potti Sriramulu Nellore": "S.P.S. Nellore"},
 "AR": {"Dibang Valley": "Upper Dibang Valley"},
 "AS": {"South Salmara Mancachar": "South Salmara Mankachar"},
 "BR": {"Kaimur (Bhabua)": "Kaimur", "Purba Champaran": "East Champaran", "Buxer": "Buxar",
        "Pashchim Champaran": "West Champaran"},
 "CT": {"Bemetara": "Bametara", "Kodagaon": "Kondagaon", "Gariyaband": "Gariaband",
        "Dantewada": "Dakshin Bastar Dantewada"},
 "GJ": {"Aravali": "Aravalli", "Kachchh": "Kutch", "Mahesana": "Mehsana", "The Dangs": "Dang"},
 "HR": {"Mewat": "Nuh", "Gurgaon": "Gurugram"},
 "HP": {"Lahul and Spiti": "Lahaul and Spiti"},
 "JH": {"Purbi Singhbhum": "East Singhbhum", "Kodarma": "Koderma", "Pashchimi Singhbhum": "West Singhbhum"},
 "KA": {"Gulbarga": "Kalaburagi", "Belgaum": "Belagavi", "Bangalore": "Bengaluru Urban",
        "Bijapur": "Vijayapura", "Shimoga": "Shivamogga", "Bagalkot": "Bagalkote",
        "Chamarajanagar": "Chamarajanagara", "Chikmagalur": "Chikkamagaluru",
        "Bangalore Rural": "Bengaluru Rural", "Bellary": "Ballari", "Mysore": "Mysuru",
        "Tumkur": "Tumakuru"},
 "LA": {"Leh(Ladakh)": "Leh"},
 "MP": {"Khandwa (East Nimar)": "Khandwa", "Khargone (West Nimar)": "Khargone", "Narsimhapur": "Narsinghpur"},
 "MH": {"Gondiya": "Gondia", "Bid": "Beed", "Raigarh": "Raigad", "Buldana": "Buldhana",
        "Ahmadnagar": "Ahmednagar"},
 "ML": {"East Jantia Hills": "East Jaintia Hills"},
 "OR": {"Jajapur": "Jajpur", "Baleshwar": "Balasore", "Jagatsinghapur": "Jagatsinghpur",
        "Anugul": "Angul", "Baudh": "Boudh", "Debagarh": "Deogarh"},
 "PB": {"Firozpur": "Ferozepur", "Muktsar": "Sri Muktsar Sahib", "Sahibzada Ajit Singh Nagar": "S.A.S. Nagar"},
 "RJ": {"Jalor": "Jalore", "Chittaurgarh": "Chittorgarh", "Dhaulpur": "Dholpur", "Jhunjhunun": "Jhunjhunu"},
 "SK": {"North  District": "North Sikkim", "South District": "South Sikkim",
        "East District": "East Sikkim", "West District": "West Sikkim"},
 "TN": {"The Nilgiris": "Nilgiris", "Kanniyakumari": "Kanyakumari"},
 "TG": {"Komaram Bheem Asifabad": "Komaram Bheem", "Jagitial": "Jagtial", "Jangoan": "Jangaon"},
 "TR": {"Unakoti": "Unokoti", "Sepahijala": "Sipahijala"},
 "UP": {"Mahrajganj": "Maharajganj", "Kheri": "Lakhimpur Kheri", "Kanshiram Nagar": "Kasganj",
        "Mahamaya Nagar": "Hathras", "Sant Ravidas Nagar (Bhadohi)": "Bhadohi", "Faizabad": "Ayodhya",
        "Jyotiba Phule Nagar": "Amroha"},
 "UT": {"Hardwar": "Haridwar"},
 "WB": {"Haora": "Howrah", "Maldah": "Malda", "Puruliya": "Purulia",
        "North Twenty Four Parganas": "North 24 Parganas", "Purba Barddhaman": "Purba Bardhaman",
        "Paschim Barddhaman": "Paschim Bardhaman", "South Twenty Four Parganas": "South 24 Parganas",
        "Hugli": "Hooghly", "Koch Bihar": "Cooch Behar"},
 "JK": {"Badgam": "Budgam", "Bandipore": "Bandipora", "Baramula": "Baramulla", "Shupiyan": "Shopiyan"},
 "AN": {"Nicobar": "Nicobars", "North  & Middle Andaman": "North and Middle Andaman"},
 "DH": {"Dadra & Nagar Haveli": "Dadra and Nagar Haveli"},
}

# State fact sheets number the indicators differently (131 vs 104). district number -> state number.
STATE_NO = {1: 1, 3: 3, 4: 4, 7: 7, 8: 8, 9: 9, 10: 10, 12: 12, 14: 14, 15: 16, 16: 20, 33: 41,
            42: 50, 45: 53, 46: 54, 49: 57, 61: 69, 68: 76, 73: 81, 74: 82, 76: 84, 78: 86,
            79: 88, 81: 92, 84: 95, 88: 101, 91: 104, 94: 107, 97: 110}
# Extra state-only indicators: state number -> (field, name, unit, higher_is)
STATE_EXTRA = {
 22: ("tfr", "Total fertility rate", "children per woman", "neutral"),
 25: ("nnmr", "Neonatal mortality rate (NFHS-5)", "per 1,000 live births", "worse"),
 26: ("imr", "Infant mortality rate (NFHS-5)", "per 1,000 live births", "worse"),
 27: ("u5mr", "Under-five mortality rate (NFHS-5)", "per 1,000 live births", "worse"),
}

def num(s):
    if s in ("NA", "", None): return None
    try: return float(s)
    except ValueError: return None

def ind_no(text):
    m = re.match(r"(\d+)\.\s", text)
    return int(m.group(1)) if m else None

def fields_meta():
    return {f: {"name": n, "unit": u, "type": "rate", "description": n + " (NFHS-5, 2019-21).",
                "higher_is": h} for _, (f, n, u, h) in IND.items()}

def write(id_, meta, fields, rows):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{id_}.json").write_text(json.dumps({"meta": meta, "fields": fields, "rows": rows}, ensure_ascii=False, indent=1))
    print(id_, len(rows), "rows")

def main():
    ref = list(csv.DictReader(open(ROOT / "data/ref/districts2020.csv")))
    ref_by = {(r["state"], norm(r["district"])): r["district"] for r in ref}
    blank = {f: None for f, *_ in IND.values()}
    rows = collections.OrderedDict()
    unmatched = set()
    for x in csv.DictReader(open(RAW / "jv_districts.csv")):
        n = ind_no(x["Indicator"])
        if n not in IND: continue
        sid = STATE_ID.get(norm(x["state"]))
        d = ALIAS.get(sid, {}).get(x["district"], x["district"].strip())
        sname = STATES[sid]["name"]
        key_d = ref_by.get((sname, norm(d)))
        if key_d is None:
            unmatched.add((sname, x["district"])); continue
        key = f"{sname}|{key_d}"
        row = rows.setdefault(key, {"key": key, "name": key_d, "state": sid, **blank})
        v = num(x["NFHS5"])
        if v is not None: row[IND[n][0]] = v
    print(f"district: matched {len(rows)} of {len(ref)} districts2020 rows; "
          f"{len(unmatched)} source districts unmatched: {sorted(unmatched)}")
    never = sorted(set(f"{r['state']}|{r['district']}" for r in ref) - set(rows))
    print(f"{len(never)} districts2020 rows without data: {never}")
    meta = dict(
        id="nfhs5_district", name="NFHS-5 (2019-21) district fact sheet indicators",
        source_org="International Institute for Population Sciences (IIPS) and Ministry of Health and Family Welfare, India",
        url="https://raw.githubusercontent.com/jvargh7/nfhs5_factsheets/main/data%20for%20analysis/districts.csv",
        landing_url="http://rchiips.org/nfhs/nfhs5.shtml",
        published="2021-12", reference_year="2019-21", resolution="district2020",
        license="Official fact sheets: Government of India data. Parsed CSV mirror: MIT (jvargh7/nfhs5_factsheets).",
        update_frequency="about every 5 years", kind="official",
        limitations="Values come from a community parse of the official PDF fact sheets and can have parse errors. Districts are the NFHS-5 (2019-21) districts; districts created later have no row. The 11 Delhi districts and Mumbai Suburban do not match districts2020.csv and are left out; Mumbai may cover only the island city. Chandigarh and Lakshadweep have no district fact sheet. Values with fewer than 25 cases are null; values from 25-49 cases are kept without a flag.",
        method="Read the mirror CSV, keep the selected indicators by their NFHS fact-sheet number, convert NA to null, map state and district names to districts2020.csv with an explicit alias table in pipeline/build_health.py. No numbers are changed.",
        accessed="2026-11-26",
        redistributed_via="https://github.com/jvargh7/nfhs5_factsheets (rchiips.org not used; cross-checked against pratapvardhan/NFHS-5 for the states it covers)")
    write("nfhs5_district", meta, fields_meta(), list(rows.values()))
    srows = {}
    by_state_no = {v: IND[k] for k, v in STATE_NO.items()}
    by_state_no.update(STATE_EXTRA)
    sblank = {v[0]: None for v in by_state_no.values()}
    for x in csv.DictReader(open(RAW / "jv_states.csv")):
        n = ind_no(x["Indicator"])
        if n not in by_state_no: continue
        sid = STATE_ID.get(norm(x["state"]))
        if sid is None: print("state unmatched", x["state"]); continue
        row = srows.setdefault(sid, {"key": sid, "name": STATES[sid]["name"], "state": sid, **sblank})
        v = num(x["Total"])
        if v is not None: row[by_state_no[n][0]] = v
    smeta = dict(meta, id="nfhs5_state", name="NFHS-5 (2019-21) state and UT fact sheet indicators",
                 url="https://raw.githubusercontent.com/jvargh7/nfhs5_factsheets/main/data%20for%20analysis/states.csv",
                 resolution="state",
                 limitations="Total (urban + rural) column of the state fact sheets. Parsed from PDFs by a community mirror; can have parse errors.",
                 method="Read the Total column of the mirror CSV, keep the selected indicators by NFHS number, NA to null, map state names with data/ref/states.csv aliases.")
    sf = fields_meta()
    for f, nme, u, h in STATE_EXTRA.values():
        sf[f] = {"name": nme, "unit": u, "type": "rate", "description": nme + " (NFHS-5, 2019-21).", "higher_is": h}
    write("nfhs5_state", smeta, sf, list(srows.values()))
    print(f"state: {len(srows)} of {len(STATES)} states/UTs")

if __name__ == "__main__":
    main()
