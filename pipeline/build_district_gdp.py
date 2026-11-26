"""Build district_gdp (Maharashtra only) from the Maharashtra DES district domestic product report.
Run: .venv/bin/python -I pipeline/build_district_gdp.py   (needs raw/economy/ddp/mh_ddp_2022_23.pdf; pdftotext)"""
import csv, json, pathlib, re, subprocess
ROOT = pathlib.Path(__file__).resolve().parent.parent
PDF = ROOT / "raw/economy/ddp/mh_ddp_2022_23.pdf"
TXT = ROOT / "raw/economy/ddp/mh.txt"
if not TXT.exists():
    subprocess.run(["pdftotext", "-layout", str(PDF), str(TXT)], check=True)
L = TXT.read_text(errors="ignore").split("\n")
start = [i for i, l in enumerate(L) if "STATEMENT NO. 49 Contd" in re.sub(r"\s+", " ", l)]
assert len(start) == 1
valid = {r["district"] for r in csv.DictReader(open(ROOT / "data/ref/districts2020.csv")) if r["state"] == "Maharashtra"}
RENAME = {"Chhatrapati Sambhaji Nagar": "Aurangabad", "Dharashiv": "Osmanabad"}
AMBIG = {"Thane"}  # source value covers Thane + Palghar together
rows, unmatched, seen = [], [], set()
for l in L[start[0] + 1: start[0] + 60]:
    m = re.match(r"^\s*(\d+)\s+([A-Za-z][A-Za-z ]*?)[*$]?\s{2,}([\d, ]+)$", l)
    if not m: continue
    name = RENAME.get(m.group(2).strip(), m.group(2).strip())
    v = [int(x.replace(",", "")) for x in m.group(3).split()]
    assert len(v) == 16, (name, v)
    assert v[-6] + v[-5] - v[-4] == v[-3] or abs(v[-6] + v[-5] - v[-4] - v[-3]) <= 2, name  # GDVA + taxes - subsidies = GDDP
    seen.add(name)
    if name in AMBIG or name not in valid:
        unmatched.append(name); continue
    rows.append({"key": f"Maharashtra|{name}", "name": name, "state": "MH", "gdva_current": v[-6], "gddp_current": v[-3], "population_000": v[-2], "per_capita_gddp": v[-1]})
unmatched += sorted(valid - seen)
for d in sorted(valid - {r["name"] for r in rows}):  # Palghar, Thane: explicit null rows
    rows.append({"key": f"Maharashtra|{d}", "name": d, "state": "MH", "gdva_current": None, "gddp_current": None, "population_000": None, "per_capita_gddp": None})
F = lambda n, u, t, d, h="neutral": {"name": n, "unit": u, "type": t, "description": d, "higher_is": h}
fields = {"gdva_current": F("Gross district value added, current prices", "INR crore", "count", "GDVA at basic prices, 2022-23, base 2011-12.", "better"),
          "gddp_current": F("Gross District Domestic Product, current prices", "INR crore", "count", "GDDP at market prices (GDVA + taxes - subsidies on products), 2022-23.", "better"),
          "population_000": F("District population used by the state", "thousand persons", "count", "Population estimate used for per-capita, as printed.", "neutral"),
          "per_capita_gddp": F("Per-capita GDDP, current prices", "INR per person", "rate", "As printed in the report (column 'Per capita District Domestic Product').", "better")}
meta = {"id": "district_gdp", "name": "District domestic product, Maharashtra only, 2022-23 (state DES estimates)",
        "source_org": "Directorate of Economics and Statistics, Government of Maharashtra",
        "url": "https://mahaces.maharashtra.gov.in/files/report/DDP_2022-23_002.pdf", "landing_url": "https://mahaces.maharashtra.gov.in",
        "published": "2025 (report 'District Domestic Product of Maharashtra 2022-23'; date not read)", "reference_year": "2022-23",
        "resolution": "district2020", "license": "Government of Maharashtra publication (no licence text found)", "update_frequency": "annual", "kind": "official",
        "limitations": "Only Maharashtra. 2022-23 is a First Revised Estimate. The source reports Mumbai city + suburban together (matches the single district 'Mumbai') and Thane together with Palghar: Thane and Palghar are null here. Source names Chhatrapati Sambhaji Nagar and Dharashiv are matched to Aurangabad and Osmanabad.",
        "method": "pdftotext -layout; Statement 49 (continued): columns GDVA, GDDP, population, per capita; check GDVA + taxes - subsidies = GDDP on each row. No unit conversion.",
        "accessed": "2026-11-26"}
rows.sort(key=lambda r: r["key"])
json.dump({"meta": meta, "fields": fields, "rows": rows}, open(ROOT / "data/normalized/district_gdp.json", "w"), ensure_ascii=False, indent=1)
print("rows", len(rows), "non-null", sum(1 for r in rows if r["gddp_current"]), "unmatched/null:", unmatched, "state total check:", sum(r["gddp_current"] or 0 for r in rows))
