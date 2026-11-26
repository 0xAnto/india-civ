"""Build census2011_district and census2011_state from raw/census/india-districts-census-2011.csv."""
import csv, json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data/normalized"; OUT.mkdir(parents=True, exist_ok=True)

ref = {int(r["censuscode"]): r for r in csv.DictReader(open(ROOT / "data/ref/districts2011.csv"))}
states = list(csv.DictReader(open(ROOT / "data/ref/states.csv")))
sid = {s["id"]: s for s in states}
byname = {}
for s in states:
    for n in [s["name"]] + [a for a in s["aliases"].split("|") if a]:
        byname[n.lower()] = s["id"]
byname.update({"nct of delhi": "DL", "arunanchal pradesh": "AR", "dadara & nagar havelli": "DH", "daman & diu": "DH",
               "andaman & nicobar island": "AN", "jammu & kashmir": "JK", "puducherry": "PY"})
# Districts of 2011 undivided Andhra Pradesh (state code 28, dt 1-10) that are in Telangana today.
TG = {"Adilabad", "Nizamabad", "Karimnagar", "Medak", "Hyderabad", "Rangareddy", "Mahbubnagar", "Nalgonda", "Warangal", "Khammam"}
LADAKH = {"Leh (ladakh)", "Kargil"}
def state_today(r):
    if r["state"] == "Andhra Pradesh" and r["district"] in TG: return "TG"
    if r["state"] == "Jammu & Kashmir" and r["district"] in LADAKH: return "LA"
    return byname[r["state"].lower()]

src = list(csv.DictReader(open(ROOT / "raw/census/india-districts-census-2011.csv")))
I = lambda x: int(x)
def rate(a, b, k=100):
    return round(a / b * k, 2) if b else None

# (output field, source column, name, unit, description)
COUNTS = [
 ("population","Population","Population","persons","Total population, Census 2011."),
 ("male","Male","Male population","persons",""),("female","Female","Female population","persons",""),
 ("literate","Literate","Literate persons","persons","Literate persons of all ages (the source has no 0-6 population)."),
 ("literate_male","Male_Literate","Literate males","persons",""),("literate_female","Female_Literate","Literate females","persons",""),
 ("sc","SC","Scheduled Caste population","persons",""),("st","ST","Scheduled Tribe population","persons",""),
 ("workers","Workers","Total workers","persons","Main plus marginal workers."),
 ("workers_male","Male_Workers","Male workers","persons",""),("workers_female","Female_Workers","Female workers","persons",""),
 ("main_workers","Main_Workers","Main workers","persons",""),("marginal_workers","Marginal_Workers","Marginal workers","persons",""),
 ("non_workers","Non_Workers","Non-workers","persons",""),
 ("cultivators","Cultivator_Workers","Cultivators","persons","Workers by category: cultivators."),
 ("agri_labourers","Agricultural_Workers","Agricultural labourers","persons",""),
 ("household_industry_workers","Household_Workers","Household-industry workers","persons",""),
 ("other_workers","Other_Workers","Other workers","persons",""),
 ("hindus","Hindus","Hindus","persons",""),("muslims","Muslims","Muslims","persons",""),("christians","Christians","Christians","persons",""),
 ("sikhs","Sikhs","Sikhs","persons",""),("buddhists","Buddhists","Buddhists","persons",""),("jains","Jains","Jains","persons",""),
 ("other_religions","Others_Religions","Other religions and persuasions","persons",""),
 ("religion_not_stated","Religion_Not_Stated","Religion not stated","persons",""),
 ("households","Households","Households","households",""),
 ("households_rural","Rural_Households","Rural households","households",""),("households_urban","Urban_Households","Urban households","households",""),
 ("hh_lpg_png","LPG_or_PNG_Households","Households using LPG or PNG for cooking","households",""),
 ("hh_electric_lighting","Housholds_with_Electric_Lighting","Households with electricity as main source of lighting","households",""),
 ("hh_internet","Households_with_Internet","Households with internet","households",""),
 ("hh_computer","Households_with_Computer","Households with computer or laptop","households",""),
 ("hh_mobile_phone","Households_with_Telephone_Mobile_Phone","Households with a telephone or mobile phone (landline, mobile or both)","households","Source column 'Telephone/Mobile Phone'; includes landline-only households."),
 ("hh_television","Households_with_Television","Households with television","households",""),
 ("hh_car","Households_with_Car_Jeep_Van","Households with car, jeep or van","households",""),
 ("hh_two_wheeler","Households_with_Scooter_Motorcycle_Moped","Households with scooter, motorcycle or moped","households",""),
 ("hh_bicycle","Households_with_Bicycle","Households with bicycle","households",""),
 ("age_0_29","Age_Group_0_29","Population aged 0-29","persons","Age groups in the source are 0-29, 30-49, 50+ and not stated."),
 ("age_30_49","Age_Group_30_49","Population aged 30-49","persons",""),("age_50_plus","Age_Group_50","Population aged 50 and above","persons",""),
 ("age_not_stated","Age not stated","Age not stated","persons",""),
 ("edu_total","Total_Education","Persons in the education-level table","persons","Denominator of the education-level counts. It is not the total population: the source table covers a subset of persons."),
 ("edu_below_primary","Below_Primary_Education","Education level: below primary","persons",""),
 ("edu_primary","Primary_Education","Education level: primary","persons",""),
 ("edu_middle","Middle_Education","Education level: middle","persons",""),
 ("edu_secondary","Secondary_Education","Education level: secondary","persons",""),
 ("edu_higher_secondary","Higher_Education","Education level: higher secondary","persons",""),
 ("edu_graduate","Graduate_Education","Education level: graduate and above","persons",""),
 ("edu_other","Other_Education","Education level: non-technical or technical diploma, other","persons",""),
 ("edu_illiterate","Illiterate_Education","Illiterate persons in the education-level table","persons",""),
]
RATES = [
 ("literacy_rate","Literate persons per 100 of total population (all ages)","percent","Not the official literacy rate: the source has no 0-6 population, so the denominator is the total population.","better"),
 ("literacy_rate_male","Male literate per 100 males (all ages)","percent","Same caveat as literacy_rate.","better"),
 ("literacy_rate_female","Female literate per 100 females (all ages)","percent","Same caveat as literacy_rate.","better"),
 ("sex_ratio","Sex ratio","females per 1000 males","","neutral"),
 ("urban_household_share","Urban share of households","percent","Urban households per 100 households. The source has no urban population.","neutral"),
 ("worker_participation","Worker participation rate","percent","Workers per 100 persons.","neutral"),
 ("female_worker_participation","Female worker participation rate","percent","Female workers per 100 females.","better"),
 ("pct_cultivators","Cultivators per 100 workers","percent","","neutral"),
 ("pct_agri_labourers","Agricultural labourers per 100 workers","percent","","worse"),
 ("pct_household_industry","Household-industry workers per 100 workers","percent","","neutral"),
 ("pct_other_workers","Other workers per 100 workers","percent","","neutral"),
 ("pct_marginal_workers","Marginal workers per 100 workers","percent","","worse"),
 ("pct_sc","Scheduled Caste share of population","percent","","neutral"),
 ("pct_st","Scheduled Tribe share of population","percent","","neutral"),
 ("pct_hindu","Hindu share of population","percent","","neutral"),("pct_muslim","Muslim share of population","percent","","neutral"),
 ("pct_christian","Christian share of population","percent","","neutral"),("pct_sikh","Sikh share of population","percent","","neutral"),
 ("pct_buddhist","Buddhist share of population","percent","","neutral"),("pct_jain","Jain share of population","percent","","neutral"),
 ("pct_graduate","Graduates per 100 persons in the education-level table","percent","Denominator is edu_total.","better"),
 ("pct_hh_electric_lighting","Households with electric lighting","percent","Per 100 households.","better"),
 ("pct_hh_lpg_png","Households using LPG or PNG","percent","Per 100 households.","better"),
 ("pct_hh_internet","Households with internet","percent","Per 100 households.","better"),
 ("pct_hh_computer","Households with computer","percent","Per 100 households.","better"),
 ("pct_hh_mobile_phone","Households with telephone or mobile phone","percent","Per 100 households.","better"),
 ("pct_hh_television","Households with television","percent","Per 100 households.","better"),
 ("pct_hh_car","Households with car, jeep or van","percent","Per 100 households.","better"),
 ("pct_hh_two_wheeler","Households with two-wheeler","percent","Per 100 households.","better"),
]
def rates(r):
    p, hh, w = r["population"], r["households"], r["workers"]
    return {
     "literacy_rate": rate(r["literate"], p), "literacy_rate_male": rate(r["literate_male"], r["male"]),
     "literacy_rate_female": rate(r["literate_female"], r["female"]),
     "sex_ratio": round(r["female"] / r["male"] * 1000) if r["male"] else None,
     "urban_household_share": rate(r["households_urban"], hh), "worker_participation": rate(w, p),
     "female_worker_participation": rate(r["workers_female"], r["female"]),
     "pct_cultivators": rate(r["cultivators"], w), "pct_agri_labourers": rate(r["agri_labourers"], w),
     "pct_household_industry": rate(r["household_industry_workers"], w), "pct_other_workers": rate(r["other_workers"], w),
     "pct_marginal_workers": rate(r["marginal_workers"], w),
     "pct_sc": rate(r["sc"], p), "pct_st": rate(r["st"], p), "pct_hindu": rate(r["hindus"], p), "pct_muslim": rate(r["muslims"], p),
     "pct_christian": rate(r["christians"], p), "pct_sikh": rate(r["sikhs"], p), "pct_buddhist": rate(r["buddhists"], p),
     "pct_jain": rate(r["jains"], p), "pct_graduate": rate(r["edu_graduate"], r["edu_total"]),
     "pct_hh_electric_lighting": rate(r["hh_electric_lighting"], hh), "pct_hh_lpg_png": rate(r["hh_lpg_png"], hh),
     "pct_hh_internet": rate(r["hh_internet"], hh), "pct_hh_computer": rate(r["hh_computer"], hh),
     "pct_hh_mobile_phone": rate(r["hh_mobile_phone"], hh), "pct_hh_television": rate(r["hh_television"], hh),
     "pct_hh_car": rate(r["hh_car"], hh), "pct_hh_two_wheeler": rate(r["hh_two_wheeler"], hh)}

def fields():
    f = {}
    for k, _, n, u, d in COUNTS:
        f[k] = {"name": n, "unit": u, "type": "count", "description": d, "higher_is": "neutral"}
    for k, n, u, d, h in RATES:
        f[k] = {"name": n, "unit": u, "type": "rate", "description": d, "higher_is": h}
    return f

rows, miss, noref = [], [], []
for x in src:
    c = int(x["District code"]); r = ref.get(c)
    if not r: noref.append((c, x["District name"])); continue
    row = {"key": str(c), "name": r["district"], "source_name": x["District name"], "state": state_today(r),
           "state_2011": byname[r["state"].lower()]}
    for k, col, *_ in COUNTS:
        row[k] = I(x[col])
    row.update(rates(row))
    rows.append(row)
got = {int(r["key"]) for r in rows}
miss = [(c, r["state"], r["district"]) for c, r in ref.items() if c not in got]
print(f"district rows {len(rows)}; source rows without ref match {len(noref)} {noref}; ref districts without source row {miss}")

common = dict(source_org="Office of the Registrar General & Census Commissioner, India (Census of India 2011)",
  landing_url="https://censusindia.gov.in/census.website/data/census-tables", published="2013-04-30", reference_year="2011",
  license="Government of India open data (Census of India). Mirror is a third-party compilation of the official tables.",
  update_frequency="decennial", kind="official", accessed="2026-11-26",
  redistributed_via="GitHub mirror nishusharma1608/India-Census-2011-Analysis (file india-districts-census-2011.csv, same file as the Kaggle danofer/india-census dataset). Official censusindia.gov.in tables were not fetched.",
  url="https://raw.githubusercontent.com/nishusharma1608/India-Census-2011-Analysis/master/india-districts-census-2011.csv")
lim = ("District boundaries are those of 2011 (640 districts). No area, no 0-6 population and no urban population in the source, "
       "so literacy is per total population and urban share uses households. Education-level counts cover a subset of persons (see edu_total). "
       "Worker-category counts of Senapati (Manipur) do not sum to total workers in the source. Mirror values are not re-checked against the official PCA files, "
       "but the national total (1,210,854,977) equals the Census 2011 total.")
doc = {"meta": {"id": "census2011_district", "name": "Census of India 2011 - district Primary Census Abstract and household tables (selected fields)",
        **common, "resolution": "district2011", "limitations": lim,
        "method": "Read the mirror CSV. Join on 'District code' = censuscode in data/ref/districts2011.csv (all 640 codes match; spelling differs in 13 names, codes are used). "
        "Counts are copied unchanged. Rates are computed as count/denominator*100 and rounded to 2 decimals; sex_ratio = females per 1000 males, rounded to integer. "
        "'state' is the state today (Telangana: 10 districts of 2011 Andhra Pradesh, codes 532-541; Ladakh: Leh and Kargil; DH: Daman, Diu, Dadra and Nagar Haveli); 'state_2011' is the state as in 2011."},
       "fields": fields(), "rows": rows}
(OUT / "census2011_district.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1))

# state
agg = {}
for r in rows:
    a = agg.setdefault(r["state"], {k: 0 for k, *_ in COUNTS}); a["_n"] = a.get("_n", 0) + 1
    for k, *_ in COUNTS: a[k] += r[k]
srows = []
for st, a in sorted(agg.items()):
    n = a.pop("_n")
    row = {"key": st, "name": sid[st]["name"], "state": st, "n_districts": n, **a}
    row.update(rates(row)); srows.append(row)
f2 = fields(); f2["n_districts"] = {"name": "Districts in 2011", "unit": "districts", "type": "count", "description": "", "higher_is": "neutral"}
print("state rows", len(srows), "sum pop", sum(r["population"] for r in srows))
sdoc = {"meta": {"id": "census2011_state", "name": "Census of India 2011 - state and UT totals (selected fields)", **common,
        "resolution": "state", "limitations": lim + " State totals are sums of district counts.",
        "method": "Sum each count over the 2011 districts, grouped by the state of today (key = id in data/ref/states.csv). Telangana = 2011 districts Adilabad, Nizamabad, Karimnagar, Medak, Hyderabad, Rangareddy, Mahbubnagar, Nalgonda, Warangal, Khammam; "
        "Andhra Pradesh = the other 13 districts of 2011 Andhra Pradesh. Ladakh = Leh and Kargil. Rates recomputed from the summed counts."},
        "fields": f2, "rows": srows}
(OUT / "census2011_state.json").write_text(json.dumps(sdoc, ensure_ascii=False, indent=1))
