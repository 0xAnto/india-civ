"""Build health_infra_state from Health Dynamics of India (Infrastructure & Human Resources) 2024-25,
status as on 31 March 2025. Needs pdftotext. Run: .venv/bin/python -I pipeline/build_health_infra.py"""
import json, re, subprocess, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
PDF = ROOT / "raw/health/infra/mohfw1.pdf"
txt = subprocess.run(["pdftotext", "-layout", str(PDF), "-"], capture_output=True, text=True, check=True).stdout
ORDER36 = "AP AR AS BR CT GA GJ HR HP JH KA KL MP MH MN ML MZ NL OR PB RJ SK TN TG TR UT UP WB AN CH DH DL JK LA LD PY".split()
ORDER37 = ORDER36[:30] + ["DH", "DAMAN"] + ORDER36[31:]
NAMES = {}
import csv
for r in csv.DictReader(open(ROOT / "data/ref/states.csv")): NAMES[r["id"]] = r["name"]

def section(start, end):
    i = txt.index(start); return txt[i:txt.index(end, i)].replace("N App", "NA")

def parse(sec, order):
    out, pending = {}, None
    for line in sec.splitlines():
        m = re.match(r"^\s*(\d+)\s*$", line)
        if m and int(m.group(1)) <= len(order): pending = int(m.group(1)); continue
        m = re.match(r"^\s*(\d+)\s+[A-Za-z&].*?\s{2,}((?:(?:[\d\*\-]+|NA)\s+)*(?:[\d\*\-]+|NA))\s*$", line)
        if m and int(m.group(1)) <= len(order):
            out[int(m.group(1))] = m.group(2).split(); pending = None; continue
        m = re.match(r"^\s+((?:(?:[\d\*\-]+|NA)\s+)*(?:[\d\*\-]+|NA))\s*$", line)
        if m and pending:
            out[pending] = m.group(1).split(); pending = None
    return {order[k - 1]: v for k, v in out.items()}

def n(t):
    return int(t) if re.fullmatch(r"\d+", t) else None

rows = {sid: {"key": sid, "name": NAMES[sid], "state": sid} for sid in ORDER36}
def put(data, cols, expect):
    for sid, v in data.items():
        if sid == "DAMAN": continue
        if len(v) != expect: print("BAD", sid, v); continue
        for c, t in zip(cols, v):
            if c: rows[sid][c] = n(t)
t1 = parse(section("NUMBER OF SUB-CENTRES, PHCs, CHCs FUNCTIONING IN RURAL", "Table 2."), ORDER36)
put(t1, ["sc_rural", "sc_urban", "phc_rural", "phc_urban", "chc_rural", "chc_urban"], 6)
t2 = parse(section("NUMBER OF SUB DIVISIONAL HOSPITAL, DISTRICT HOSPITAL & MEDICAL COLLEGES FUNCTIONING", "Table 3."), ORDER36)
put(t2, ["sdh", "sdh_as_mc", "dh", "dh_as_mc", "medical_colleges_standalone"], 5)
t7 = parse(section("NUMBER OF BEDS AT SDH, DH & MEDICAL COLLEGE", "SECTION IV"), ORDER36)
put(t7, ["beds_sdh", "beds_sdh_as_mc", "beds_dh", "beds_dh_as_mc", "beds_medical_colleges"], 5)
s5 = parse(section("DOCTORS3/MEDICAL OFFICERS3 AT PRIMARY HEALTH CENTRES in Rural Areas", "Notes: Telangana"), ORDER37)
for sid, v in s5.items():
    if sid == "DAMAN": continue
    if sid == "DH":  # 2025 values are on a wrapped line: required sanctioned in-position vacant shortfall
        v = ["-"] * 5 + v[-5:]
    if len(v) != 10: print("BAD s5", sid, v); continue
    rows[sid]["phc_doctors_sanctioned"] = n(v[6]); rows[sid]["phc_doctors_in_position"] = n(v[7])
for r in rows.values():
    for a, b, c in [("sc_rural", "sc_urban", "sub_centres"), ("phc_rural", "phc_urban", "phcs"), ("chc_rural", "chc_urban", "chcs")]:
        r[c] = r[a] + r[b] if r.get(a) is not None and r.get(b) is not None else None
    for k in ["phc_doctors_sanctioned", "phc_doctors_in_position"]: r.setdefault(k, None)
def f(name, unit, hi, desc): return {"name": name, "unit": unit, "type": "count", "description": desc, "higher_is": hi}
F = {
 "sub_centres": f("Sub-centres functioning (rural + urban)", "facilities", "better", "As on 31 March 2025. Sum of sc_rural and sc_urban."),
 "sc_rural": f("Sub-centres functioning, rural", "facilities", "better", "As on 31 March 2025."),
 "sc_urban": f("Sub-centres functioning, urban", "facilities", "better", "As on 31 March 2025."),
 "phcs": f("Primary health centres functioning (rural + urban)", "facilities", "better", "Sum of phc_rural and phc_urban."),
 "phc_rural": f("Primary health centres, rural", "facilities", "better", "As on 31 March 2025."),
 "phc_urban": f("Primary health centres, urban", "facilities", "better", "As on 31 March 2025."),
 "chcs": f("Community health centres functioning (rural + urban)", "facilities", "better", "Sum of chc_rural and chc_urban."),
 "chc_rural": f("Community health centres, rural", "facilities", "better", "As on 31 March 2025."),
 "chc_urban": f("Community health centres, urban", "facilities", "better", "As on 31 March 2025."),
 "sdh": f("Standalone sub-divisional hospitals", "facilities", "better", "As on 31 March 2025."),
 "sdh_as_mc": f("Sub-divisional hospitals functioning as medical college", "facilities", "better", "As on 31 March 2025."),
 "dh": f("Standalone district hospitals", "facilities", "better", "As on 31 March 2025."),
 "dh_as_mc": f("District hospitals functioning as medical college", "facilities", "better", "As on 31 March 2025."),
 "medical_colleges_standalone": f("Standalone state-owned medical colleges and hospitals", "facilities", "better", "As on 31 March 2025."),
 "beds_sdh": f("Beds in standalone sub-divisional hospitals", "beds", "better", "As on 31 March 2025."),
 "beds_sdh_as_mc": f("Beds in sub-divisional hospitals functioning as medical college", "beds", "better", "As on 31 March 2025."),
 "beds_dh": f("Beds in standalone district hospitals", "beds", "better", "As on 31 March 2025."),
 "beds_dh_as_mc": f("Beds in district hospitals functioning as medical college", "beds", "better", "As on 31 March 2025."),
 "beds_medical_colleges": f("Beds in standalone medical colleges", "beds", "better", "As on 31 March 2025."),
 "phc_doctors_sanctioned": f("Allopathic doctors / medical officers sanctioned at rural PHCs", "posts", "better", "As on 31 March 2025. Null where the report gives NA or not applicable."),
 "phc_doctors_in_position": f("Allopathic doctors / medical officers in position at rural PHCs", "persons", "better", "As on 31 March 2025. Null where the report gives NA or not applicable."),
}
meta = dict(id="health_infra_state", name="Public health infrastructure by state: Health Dynamics of India 2024-25 (formerly Rural Health Statistics)",
 source_org="Statistics Division, Ministry of Health and Family Welfare, India",
 url="https://www.mohfw-dohfw.gov.in/static/uploads/2026/10/ad371537b4765ba9d19b44c338e099d6.pdf",
 landing_url="https://mohfw.gov.in/", published="2026-10", reference_year="2025-03-31", resolution="state",
 license="Government of India publication", update_frequency="annual", kind="official",
 limitations="Public facilities only (no private hospitals). Counts only; no per-capita rates because no same-year state population is in the repository. Registered-doctor counts (National Health Profile) are not included: the CBHI PDF was not reachable. Doctors are rural PHC posts only. Dadra & Nagar Haveli and Daman & Diu: doctor numbers read from the wrapped row of the combined UT.",
 method="pdftotext -layout; parse Section III Table 1, Table 2, Table 7 and Comparative Statement 5 (2025 columns) by serial number; '*', '-', NA become null; urban and rural facility counts are summed for totals. No other change.",
 accessed="2026-11-26")
out = list(rows.values())
(ROOT / "data/normalized/health_infra_state.json").write_text(json.dumps({"meta": meta, "fields": F, "rows": out}, ensure_ascii=False, indent=1))
print(len(out), "rows")
for k in ["sub_centres", "phcs", "chcs", "beds_dh", "phc_doctors_in_position"]:
    print(k, sum(r[k] or 0 for r in out), "nulls", sum(r[k] is None for r in out))
