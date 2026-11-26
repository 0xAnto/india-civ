"""Build srs_state from SRS Bulletin 2024 (Table 1) and SRS Abridged Life Tables 2020-24 (Statement 3).
Needs pdftotext (poppler). Run: .venv/bin/python -I pipeline/build_health_srs.py"""
import csv, json, re, subprocess, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "raw/health/srs"
STATES = {r["id"]: r for r in csv.DictReader(open(ROOT / "data/ref/states.csv"))}
def norm(s): return re.sub(r"[^a-z]", "", s.lower())
SID = {}
for i, r in STATES.items():
    for n in [r["name"]] + [a for a in r["aliases"].split("|") if a]:
        SID[norm(n)] = i
SID[norm("Dadra & Nagar Haveli and Daman & Diu")] = "DH"
def txt(p): return subprocess.run(["pdftotext", "-layout", str(RAW / p), "-"], capture_output=True, text=True, check=True).stdout
NUM = r"(-?\d+(?:\.\d+)?)"
rows = {}
def row(sid):
    return rows.setdefault(sid, {"key": sid, "name": STATES[sid]["name"], "state": sid,
        **{k: None for k in ["birth_rate","death_rate","natural_growth_rate","imr","imr_rural","imr_urban",
                             "life_exp","life_exp_male","life_exp_female"]}})
# Table 1 of the bulletin
b = txt("bul2024.pdf")
t1 = b[b.index("Table 1: Estimated"):b.index("Table 2: Ninety")]
t1 = t1.replace("Dadra & Nagar Haveli\n", "Dadra & Nagar Haveli and Daman & Diu ").replace("and Daman & Diu\n", "")
for line in t1.splitlines():
    m = re.match(r"\s*\d+\.\s+([A-Za-z&\. ]+?)\*?\s{2,}(.*)$", line)
    if not m: continue
    nums = re.findall(NUM, m.group(2))
    nm = m.group(1).strip()
    if norm(nm) not in SID:
        if "Dadra" in nm: nm = "Dadra & Nagar Haveli and Daman & Diu"
        else: print("UNMATCHED", nm); continue
    if len(nums) != 12: print("BAD", nm, nums); continue
    v = [float(x) for x in nums]
    r = row(SID[norm(nm)])
    r.update(birth_rate=v[0], death_rate=v[3], natural_growth_rate=v[6], imr=v[9], imr_rural=v[10], imr_urban=v[11])
# the "Dadra" row wraps: numbers are on the next line
m = re.search(r"Dadra & Nagar Haveli\s*\n\s+" + r"\s+".join([NUM]*12), b[b.index("Table 1: Estimated"):])
if m:
    v = [float(x) for x in m.groups()]
    r = row("DH"); r.update(birth_rate=v[0], death_rate=v[3], natural_growth_rate=v[6], imr=v[9], imr_rural=v[10], imr_urban=v[11])
# life tables
l = txt("lt2024.pdf")
s3 = l[l.index("Statement 3"):]
s3 = s3[:s3.index("Chart 4")]
for line in s3.splitlines():
    m = re.match(r"\s+([A-Za-z&\. ]+?)\s{2,}" + r"\s+".join([NUM]*9) + r"\s*$", line)
    if not m or norm(m.group(1)) in ("india",): continue
    sid = SID.get(norm(m.group(1)))
    if not sid: print("UNMATCHED LT", m.group(1)); continue
    v = [float(x) for x in m.groups()[1:]]
    r = row(sid); r.update(life_exp=v[0], life_exp_male=v[1], life_exp_female=v[2])
def f(name, unit, hi, desc, t="rate"): return {"name": name, "unit": unit, "type": t, "description": desc, "higher_is": hi}
fields = {
 "birth_rate": f("Birth rate", "per 1,000 population", "neutral", "Crude birth rate, SRS 2024."),
 "death_rate": f("Death rate", "per 1,000 population", "worse", "Crude death rate, SRS 2024."),
 "natural_growth_rate": f("Natural growth rate", "per 1,000 population", "neutral", "Birth rate minus death rate, SRS 2024."),
 "imr": f("Infant mortality rate", "per 1,000 live births", "worse", "SRS 2024. For smaller States/UTs the SRS gives the 3-year value 2022-24."),
 "imr_rural": f("Infant mortality rate, rural", "per 1,000 live births", "worse", "As imr, rural areas."),
 "imr_urban": f("Infant mortality rate, urban", "per 1,000 live births", "worse", "As imr, urban areas."),
 "life_exp": f("Life expectancy at birth", "years", "better", "SRS abridged life table, 5-year period 2020-24, both sexes. Only bigger States/UTs and Himachal Pradesh."),
 "life_exp_male": f("Life expectancy at birth, male", "years", "better", "As life_exp, males."),
 "life_exp_female": f("Life expectancy at birth, female", "years", "better", "As life_exp, females."),
}
meta = dict(id="srs_state", name="Sample Registration System: birth rate, death rate, infant mortality, life expectancy by state",
 source_org="Office of the Registrar General & Census Commissioner, India (Vital Statistics Division)",
 url="https://censusindia.gov.in/nada/index.php/catalog/47150/download/51394/SRS_Bulletin_2024_Vol_59_No_1.pdf ; https://censusindia.gov.in/nada/index.php/catalog/47148/download/51393/SRS-Abridged_Life_Tables_2020-2024.pdf",
 landing_url="https://censusindia.gov.in/nada/index.php/catalog/47150",
 published="2026-05", reference_year="2024 (rates); 2020-24 (life expectancy)", resolution="state",
 license="Government of India data (Census of India website terms)", update_frequency="annual", kind="official",
 limitations="Rates are sample estimates with confidence limits (not stored). Smaller States/UTs have IMR from the 3-year period 2022-24. Manipur estimates use 130 SRS units. Life expectancy exists only for 21 bigger States/UTs plus Himachal Pradesh; other states are null. Chandigarh rural IMR (31) is as published and looks unstable.",
 method="pdftotext -layout on the two PDFs; regex rows of Table 1 (bulletin) and Statement 3 (life tables); state names mapped with data/ref/states.csv aliases. Values copied unchanged. The Dadra & Nagar Haveli and Daman & Diu row wraps over two lines and is read separately.",
 accessed="2026-11-26")
out = list(rows.values())
(ROOT / "data/normalized/srs_state.json").write_text(json.dumps({"meta": meta, "fields": fields, "rows": out}, ensure_ascii=False, indent=1))
print(len(out), "rows;", sum(r["imr"] is not None for r in out), "with rates;", sum(r["life_exp"] is not None for r in out), "with life exp")
print([r for r in out if r["state"] in ("DH","KL")])
