"""Build normalized economy datasets from raw/economy/. Run: .venv/bin/python -I pipeline/build_economy.py
Writes data/normalized/{gsdp_state,gsva_sector_state,plfs_state,asi_state,exports_state}.json"""
import csv, json, pathlib, re, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "raw" / "economy"
OUT = ROOT / "data" / "normalized"
OUT.mkdir(parents=True, exist_ok=True)
ACCESSED = "2026-11-26"

# ---------- state name -> id ----------
def norm(s):
    s = s.lower().replace("&", " and ").replace(".", " ")
    return re.sub(r"[^a-z]+", " ", s).strip()
STATES = {}
NAMES = {}
for r in csv.DictReader(open(ROOT / "data/ref/states.csv")):
    NAMES[r["id"]] = r["name"]
    for n in [r["name"]] + [a for a in r["aliases"].split("|") if a]:
        STATES[norm(n)] = r["id"]
for n, i in {"chattisgarh": "CT", "a and n islands": "AN", "andaman and n island": "AN",
             "dadra and n haveli and daman and diu": "DH", "orissa": "OR", "nct of delhi": "DL",
             "andaman and nicobar islands": "AN"}.items():
    STATES[n] = i
def sid(name):
    return STATES.get(norm(name))

UNMATCHED = {}
def note_unmatched(ds, name):
    UNMATCHED.setdefault(ds, []).append(name)

def write(meta, fields, rows, ds):
    meta = dict(meta, id=ds, accessed=ACCESSED)
    rows = sorted(rows, key=lambda r: r["key"])
    json.dump({"meta": meta, "fields": fields, "rows": rows}, open(OUT / f"{ds}.json", "w"), ensure_ascii=False, indent=1)
    cov = {f: sum(1 for r in rows if r.get(f) is not None) for f in fields if f != "series"}
    print(f"[{ds}] rows={len(rows)} unmatched={UNMATCHED.get(ds, [])}")
    print("   non-null per field:", cov)

def num(x):
    if x is None: return None
    x = str(x).replace(",", "").strip()
    if x in ("", "-", "NA", "null", "None"): return None
    try: return float(x) if "." in x else int(x)
    except ValueError: return None

def F(name, unit, typ, desc, hi="neutral"):
    return {"name": name, "unit": unit, "type": typ, "description": desc, "higher_is": hi}

# ======================================================================
# 1. gsdp_state  (MoSPI NAS API, base 2011-12)
# ======================================================================
REF = "2023-24"
def nas(name):
    return json.load(open(RAW / "mospi_nas" / f"{name}.json"))["data"]

def build_gsdp():
    ds = "gsdp_state"
    rows = {}
    series_keys = {"gsdp": ("gsdp_current", "gsdp_constant"), "nsdp": ("nsdp_current", "nsdp_constant"),
                   "pc_nsdp": ("pc_nsdp_current", "pc_nsdp_constant"), "pc_gsdp": ("pc_gsdp_current", "pc_gsdp_constant")}
    for f, (kc, kk) in series_keys.items():
        for r in nas(f):
            i = sid(r["state"])
            if not i:
                note_unmatched(ds, r["state"]); continue
            row = rows.setdefault(i, {"key": i, "name": NAMES[i], "state": i, "series": {}})
            for k, v in ((kc, r["current_price"]), (kk, r["constant_price"])):
                row["series"].setdefault(k, {})[r["year"]] = num(v)
    # RBI DBIE handbook: fill-in for states that MoSPI does not publish (own, separate fields)
    sys.path.insert(0, str(pathlib.Path(__file__).parent))
    import _hub
    hub = {}
    for slug, key in [("net-state-domestic-product-state-wise-at-current-prices", "nsdp_current_rbi"),
                      ("per-capita-net-state-domestic-product-state-wise-at-current-prices", "pc_nsdp_current_rbi")]:
        d = _hub.load(RAW / "rbi" / f"hub_{slug}.html")
        yi = d["years"].index(REF)
        for st in d["states"]:
            i = sid(st)
            v = d["data"][st][yi]
            hub.setdefault(i, {})[key] = v
    out = []
    for i, row in rows.items():
        s = row.pop("series")
        for k in ("gsdp_current", "gsdp_constant", "nsdp_current", "nsdp_constant", "pc_nsdp_current", "pc_nsdp_constant", "pc_gsdp_current", "pc_gsdp_constant"):
            row[k] = s.get(k, {}).get(REF)
        row["series"] = {k: {y: v for y, v in sorted(d.items()) if v is not None} for k, d in s.items()}
        h = hub.get(i, {}) if row["nsdp_current"] is None else {}  # RBI only where MoSPI has no NSDP
        row.update({"nsdp_current_rbi": h.get("nsdp_current_rbi"), "pc_nsdp_current_rbi": h.get("pc_nsdp_current_rbi")})
        out.append(row)
    have = {r["key"] for r in out}
    for i, h in hub.items():
        if i and i not in have:
            out.append({"key": i, "name": NAMES[i], "state": i, **{k: None for k in ("gsdp_current", "gsdp_constant", "nsdp_current", "nsdp_constant", "pc_nsdp_current", "pc_nsdp_constant", "pc_gsdp_current", "pc_gsdp_constant")},
                        "nsdp_current_rbi": h.get("nsdp_current_rbi"), "pc_nsdp_current_rbi": h.get("pc_nsdp_current_rbi"), "series": {}})
    fields = {
        "gsdp_current": F("GSDP, current prices", "INR crore", "value", f"Gross State Domestic Product at current prices, {REF}. MoSPI NAS, base 2011-12 (Quick Estimate).", "better"),
        "gsdp_constant": F("GSDP, constant (2011-12) prices", "INR crore", "value", f"GSDP at constant 2011-12 prices, {REF}.", "better"),
        "nsdp_current": F("NSDP, current prices", "INR crore", "value", f"Net State Domestic Product at current prices, {REF}.", "better"),
        "nsdp_constant": F("NSDP, constant (2011-12) prices", "INR crore", "value", f"NSDP at constant prices, {REF}.", "better"),
        "pc_nsdp_current": F("Per-capita NSDP, current prices", "INR per person", "rate", f"Per-capita Net State Domestic Product at current prices, {REF}.", "better"),
        "pc_nsdp_constant": F("Per-capita NSDP, constant (2011-12) prices", "INR per person", "rate", f"Per-capita NSDP at constant prices, {REF}.", "better"),
        "pc_gsdp_current": F("Per-capita GSDP, current prices", "INR per person", "rate", f"GSDP per person at current prices, {REF}, as published by MoSPI.", "better"),
        "pc_gsdp_constant": F("Per-capita GSDP, constant (2011-12) prices", "INR per person", "rate", f"GSDP per person at constant prices, {REF}.", "better"),
        "nsdp_current_rbi": F("NSDP, current prices (RBI fill-in)", "INR crore", "value", f"Only for states that MoSPI NAS does not publish. Source: RBI DBIE Handbook of Statistics, {REF}. Different vintage than the MoSPI columns; do not mix in one ranking without care.", "better"),
        "pc_nsdp_current_rbi": F("Per-capita NSDP, current prices (RBI fill-in)", "INR per person", "rate", "Same as nsdp_current_rbi, per person.", "better"),
        "series": F("Series by year", "see keys", "text", "Object: metric -> {year: value} for 2011-12 to 2024-25 (2024-25 is an Advance Estimate). Units as in the columns of the same name.", "neutral"),
    }
    meta = {"name": "State GSDP / NSDP / per-capita NSDP, base 2011-12 (MoSPI National Accounts Statistics)",
            "source_org": "Ministry of Statistics and Programme Implementation (MoSPI), National Statistics Office; fill-in from Reserve Bank of India (DBIE Handbook of Statistics)",
            "url": "https://api.mospi.gov.in/api/nas/getNASData?base_year=2011-12&series=Current&frequency_code=Annually&indicator_code=23,24,25,31",
            "landing_url": "https://esankhyiki.mospi.gov.in/catalogue-main/catalogue?page=0&search=&product=NAS",
            "published": "2025-2026 (state estimates: 2023-24 Quick Estimates, 2024-25 Advance Estimates; the API gives no release date)",
            "reference_year": REF, "resolution": "state", "license": "Government Open Data License - India (GODL)",
            "update_frequency": "annual", "kind": "official",
            "limitations": "Base year 2011-12. MoSPI NAS gives no GSDP or NSDP value for Assam, Haryana, Nagaland, Ladakh, Dadra and Nagar Haveli and Daman and Diu, Lakshadweep: these are null in the MoSPI columns (the API does return per-capita GSDP for Assam, Haryana, Nagaland, Ladakh; Dadra and Nagar Haveli and Daman and Diu and Lakshadweep have no row). For Assam, Haryana and Nagaland the RBI Handbook gives NSDP: it is in separate *_rbi columns. GSDP for these states is null (no official GSDP file reached). 2023-24 is the common year because 2024-25 is only an Advance Estimate. State series are not strictly comparable across states for methodology reasons.",
            "method": f"Downloaded all states and years 2011-12..2024-25 from the MoSPI NAS API (series=Current, indicators 23 GSDP, 24 NSDP, 25 per-capita NSDP, 31 per-capita GSDP). Row values are the {REF} values; `series` holds all years. No unit conversion (INR crore; per-capita INR). Null values stay null."}
    write(meta, fields, out, ds)

# ======================================================================
# 2. gsva_sector_state
# ======================================================================
SECTORS = [("agri", "Agriculture, Livestock, Forestry and Fishing", "Agriculture, forestry and fishing"),
           ("mining", "Mining and Quarrying", "Mining and quarrying"),
           ("mfg", "Manufacturing", "Manufacturing"),
           ("elec", "Electricity, Gas, Water Supply & Other Utility Services", "Electricity, gas, water supply and other utilities"),
           ("constr", "Construction", "Construction"),
           ("trade", "Trade, Repair, Hotels and Restaurants", "Trade, repair, hotels and restaurants"),
           ("transport", "Transport, Storage, Communication & Services Related to Broadcasting", "Transport, storage, communication and broadcasting"),
           ("finance", "Financial Services", "Financial services"),
           ("realestate", "Real Estate, Ownership of Dwelling & Professional Services", "Real estate, dwellings and professional services"),
           ("pubadmin", "Public Administration", "Public administration"),
           ("other", "Other Services", "Other services")]
def build_gsva():
    ds = "gsva_sector_state"
    d = json.load(open(RAW / "mospi_nas" / f"gsva_{REF}.json"))["data"]
    byst = {}
    for r in d:
        if r["subindustry"]: continue
        i = sid(r["state"])
        if not i:
            note_unmatched(ds, r["state"]); continue
        byst.setdefault(i, {})[r["industry"]] = r
    rows = []
    for i, m in byst.items():
        row = {"key": i, "name": NAMES[i], "state": i}
        tot = m.get("Total Gross State Value Added")
        row["gsva_total"] = num(tot["current_price"]) if tot else None
        row["gsva_total_constant"] = num(tot["constant_price"]) if tot else None
        vals = {}
        for k, long, _ in SECTORS:
            r = m.get(long)
            v = num(r["current_price"]) if r else None
            vals[k] = v
            row[f"gsva_{k}"] = v
        for k, _, _ in SECTORS:
            v = vals[k]
            row[f"share_{k}"] = round(100 * v / row["gsva_total"], 2) if v is not None and row["gsva_total"] else None
        # check: sector sum vs total
        if None not in vals.values() and row["gsva_total"]:
            diff = abs(sum(vals.values()) - row["gsva_total"]) / row["gsva_total"]
            if diff > 0.002: print("  WARN sector sum differs from total:", i, diff)
        rows.append(row)
    fields = {"gsva_total": F("Total GSVA, current prices", "INR lakh", "value", f"Total Gross State Value Added at basic prices, current prices, {REF}.", "better"),
              "gsva_total_constant": F("Total GSVA, constant (2011-12) prices", "INR lakh", "value", f"Total GSVA at constant prices, {REF}.", "better")}
    for k, _, label in SECTORS:
        fields[f"gsva_{k}"] = F(f"GSVA: {label}", "INR lakh", "value", f"GSVA of this sector at current prices, {REF}. Null if the source gives no value.", "neutral")
        fields[f"share_{k}"] = F(f"Share of GSVA: {label}", "percent", "rate", "Sector GSVA divided by total GSVA, times 100. Computed here, 2 decimals.", "neutral")
    meta = {"name": "State GSVA by economic activity (11 sectors), current prices, base 2011-12",
            "source_org": "Ministry of Statistics and Programme Implementation (MoSPI), National Statistics Office",
            "url": "https://api.mospi.gov.in/api/nas/getNASData?base_year=2011-12&series=Current&frequency_code=Annually&indicator_code=29&year=2023-24",
            "landing_url": "https://esankhyiki.mospi.gov.in/catalogue-main/catalogue?page=0&search=&product=NAS",
            "published": "2025-2026 (API gives no release date)", "reference_year": REF, "resolution": "state",
            "license": "Government Open Data License - India (GODL)", "update_frequency": "annual", "kind": "official",
            "limitations": "One year only (2023-24, Quick Estimates). The API returns a null for some sectors in some states (for example trade and transport in a few states): those values and shares are null, not estimated. Ladakh, Lakshadweep, Dadra and Nagar Haveli and Daman and Diu may be absent. Shares are of total GSVA at basic prices (without product taxes).",
            "method": "Took top-level industry rows of indicator 29 (Gross State Value Added), current price column, INR lakh (unchanged). Shares = sector / 'Total Gross State Value Added' x 100. Sub-industry rows were ignored."}
    write(meta, fields, rows, ds)

# ======================================================================
# 3. plfs_state (Annual Report 2025, PDF text via pdftotext -layout)
# ======================================================================
def build_plfs():
    ds = "plfs_state"
    import subprocess
    txt_path = RAW / "plfs" / "ar.txt"
    if not txt_path.exists():
        subprocess.run(["pdftotext", "-layout", str(RAW / "plfs" / "ar2025rev.pdf"), str(txt_path)], check=True)
    L = open(txt_path, errors="ignore").read().split("\n")
    numre = re.compile(r"(?<![\w.])-?\d[\d,]*\.?\d*(?![\w.])")
    def split_row(line):
        m = re.match(r"^(\D+?)\s{2,}(.*)$", line)
        if not m: return None
        nums = [x for x in m.group(2).split() ]
        try: vals = [float(x.replace(",", "")) for x in nums]
        except ValueError: return None
        return m.group(1).strip(), vals
    def block(header_re, age_re, ncols):
        starts = [i for i, l in enumerate(L) if re.search(header_re, l) and i > 7000 and any(age_re.search(L[j]) for j in range(i + 1, i + 4))]
        assert len(starts) == 1, (header_re, starts)
        out = {}
        for l in L[starts[0] + 1: starts[0] + 60]:
            r = split_row(l)
            if not r: continue
            name, v = r
            if name.lower() == "all india":
                out["ALL"] = v; break
            if len(v) in (ncols, ncols - 3, 9, 6): out[name] = v
        return out
    age = re.compile(r"age group:\s*15 years and above")
    tabs = {"lfpr": block(r"Table \(16\.0\)", age, 9), "wpr": block(r"Table \(17\.0\)", age, 9), "ur": block(r"Table \(18\.0\)", age, 9)}
    for k, t in tabs.items(): assert t["ALL"], k
    print("   PLFS all-India (15+ r+u male/female/person):", {k: t["ALL"][-3:] for k, t in tabs.items()})
    # Table 27, rural+urban persons block: industry sections A..T + all
    t27 = [i for i, l in enumerate(L) if l.startswith("Table (27)") and i > 13000]
    pos = [i for i in t27 if re.match(r"rural\+urban\s+persons", L[i + 2].strip() if L[i + 2].strip() else L[i + 3].strip())]
    assert len(pos) == 1, pos
    ind = {}
    for l in L[pos[0] + 1: pos[0] + 60]:
        r = split_row(l)
        if r and len(r[1]) == 21:
            ind["ALL" if r[0].lower() == "all india" else r[0]] = r[1]
    print("   PLFS all-India industry sections A,C,F:", ind["ALL"][0], ind["ALL"][2], ind["ALL"][5])
    rows = []
    for name in tabs["lfpr"]:
        if name == "ALL": continue
        i = sid(name)
        if not i:
            note_unmatched(ds, name); continue
        def g(tab, idx):  # idx from the end: -1 person r+u, -2 female r+u, -3 male r+u, -4 urban person, -7 rural person
            v = tabs[tab].get(name)
            return v[idx] if v and len(v) >= -idx else None
        row = {"key": i, "name": NAMES[i], "state": i,
               "lfpr": g("lfpr", -1), "lfpr_male": g("lfpr", -3), "lfpr_female": g("lfpr", -2),
               "wpr": g("wpr", -1), "wpr_male": g("wpr", -3), "wpr_female": g("wpr", -2),
               "ur": g("ur", -1), "ur_male": g("ur", -3), "ur_female": g("ur", -2),
               "ur_urban": g("ur", -4),
               "ur_rural": (tabs["ur"][name][-7] if len(tabs["ur"][name]) == 9 else None)}
        v = ind.get(name)
        if v:
            tot = v[-1]
            row["share_agri"] = round(v[0], 2)
            row["share_industry"] = round(sum(v[1:6]), 2)   # B..F
            row["share_manufacturing"] = round(v[2], 2)     # C
            row["share_construction"] = round(v[5], 2)      # F
            row["share_services"] = round(sum(v[6:20]), 2)  # G..T
            assert abs(row["share_agri"] + row["share_industry"] + row["share_services"] - 100) < 0.2, (name, v)
        else:
            for k in ("share_agri", "share_industry", "share_manufacturing", "share_construction", "share_services"): row[k] = None
            note_unmatched(ds + ":industry", name)
        rows.append(row)
    fd = lambda n, d, h: F(n, "percent", "rate", d, h)
    fields = {"lfpr": fd("LFPR, persons 15+", "Labour force participation rate, usual status (ps+ss), age 15+, rural+urban, persons, Jan-Dec 2025.", "neutral"),
              "lfpr_male": fd("LFPR, male 15+", "Same, male.", "neutral"), "lfpr_female": fd("LFPR, female 15+", "Same, female.", "neutral"),
              "wpr": fd("WPR, persons 15+", "Worker population ratio, usual status (ps+ss), age 15+, rural+urban, persons.", "better"),
              "wpr_male": fd("WPR, male 15+", "Same, male.", "better"), "wpr_female": fd("WPR, female 15+", "Same, female.", "better"),
              "ur": fd("Unemployment rate, persons 15+", "Unemployment rate, usual status (ps+ss), age 15+, rural+urban, persons.", "worse"),
              "ur_male": fd("Unemployment rate, male 15+", "Same, male.", "worse"), "ur_female": fd("Unemployment rate, female 15+", "Same, female.", "worse"),
              "ur_urban": fd("Unemployment rate, urban persons 15+", "Urban persons. Null where the source has no urban sample.", "worse"),
              "ur_rural": fd("Unemployment rate, rural persons 15+", "Rural persons. Null where the source has no rural sample (Chandigarh).", "worse"),
              "share_agri": fd("Workers in agriculture (NIC section A)", "Share of usually working persons (ps+ss), rural+urban, persons.", "neutral"),
              "share_industry": fd("Workers in industry (NIC sections B-F)", "Mining, manufacturing, electricity, water, construction. Sum of sections B to F.", "neutral"),
              "share_manufacturing": fd("Workers in manufacturing (NIC section C)", "Part of share_industry.", "neutral"),
              "share_construction": fd("Workers in construction (NIC section F)", "Part of share_industry.", "neutral"),
              "share_services": fd("Workers in services (NIC sections G-T)", "Sum of sections G to T.", "neutral")}
    meta = {"name": "Periodic Labour Force Survey, Annual Report 2025: state-wise LFPR, WPR, unemployment rate (usual status, age 15+) and industry of workers",
            "source_org": "National Statistics Office, MoSPI",
            "url": "https://www.mospi.gov.in/uploads/publications_reports/publications_reports1780040415321_0624fb13-fb47-40bc-b470-7c7e9635c3ef_PLFS_2025_F_REV_29052026.pdf",
            "landing_url": "https://www.mospi.gov.in/publication/annual-report-plfs-2025",
            "published": "2026-03-27 (press note); revised report file dated 2026-05-29", "reference_year": "2025 (Jan-Dec 2025)",
            "resolution": "state", "license": "Government Open Data License - India (GODL)", "update_frequency": "annual", "kind": "official",
            "limitations": "Sample survey: small-state estimates (Lakshadweep, Ladakh, Sikkim, north-east, UTs) have large errors. From Jan 2025 PLFS changed the design (monthly sample, new weights), so 2025 is not strictly comparable with earlier rounds. Chandigarh has no rural sample.",
            "method": "pdftotext -layout on the PDF. Appendix Tables 16.0 (LFPR), 17.0 (WPR), 18.0 (UR), block 'age group: 15 years and above'; last three numbers of each row = rural+urban male, female, person; next three before = urban; before = rural. Industry: Appendix Table 27, rural+urban persons block; shares of NIC sections summed: A agriculture, B-F industry, G-T services; each row's three groups sum to 100 (checked). Rates in percent as published. All-India (not a row): LFPR 59.3, WPR 57.4, UR 3.1."}
    write(meta, fields, rows, ds)

# ======================================================================
# 4. asi_state (ASI 2023-24 Volume I, Tables 2 and 4)
# ======================================================================
def build_asi():
    ds = "asi_state"
    L = open(RAW / "asi" / "asi.txt", errors="ignore").read().split("\n")
    def first_nonblank(j, skip=()):
        while not L[j].strip() or any(s in L[j] for s in skip): j += 1
        return L[j].strip()
    first = lambda m: int(m.group(1).replace(",", ""))
    t2, t4 = {}, {}
    for i, l in enumerate(L):
        if "Table 2: Estimate of selected" in l:
            st = first_nonblank(i + 1, ("for each State",))
            if st in t2: continue
            blk = L[i: i + 60]
            d = {}
            for b in blk:
                for key, rx in (("factories", r"^1\. Number of Factories \(no\.\)\s+(-?\d+)"), ("operating", r"^2\. Factories in Operation \(no\.\)\s+(-?\d+)"),
                                ("fixed_capital", r"^3\. Fixed Capital\s+(-?\d+)"), ("output", r"^15\. Total Output\s+(-?\d+)"),
                                ("gva", r"^19\. Gross Value Added\s+(-?\d+)"), ("nva", r"^21\. Net Value Added\s+(-?\d+)")):
                    m = re.match(rx, b.strip())
                    if m and key not in d: d[key] = first(m)
            t2[st] = d
        if "Table 4: Estimate of (i) employment" in l:
            st = first_nonblank(i + 1, ("for each 3-digit", "for each State"))
            if st in t4: continue
            d = {}
            for b in L[i: i + 60]:
                for key, rx in (("persons", r"^A\.\s+No\. of Persons Engaged \(no\.\)\s+(-?\d+)"), ("workers", r"^1\. Workers\s+(-?\d+)")):
                    m = re.match(rx, b.strip())
                    if m and key not in d: d[key] = first(m)
            t4[st] = d
    allind = t2.pop("All-India"); t4.pop("All-India", None)
    print("   ASI all-India:", allind, "persons", sum(v.get("persons", 0) for v in t4.values()))
    rows = []
    for st, d in t2.items():
        i = sid(st)
        if not i:
            note_unmatched(ds, st); continue
        e = t4.get(st, {})
        rows.append({"key": i, "name": NAMES[i], "state": i, "factories": d.get("factories"), "factories_operating": d.get("operating"),
                     "persons_engaged": e.get("persons"), "workers": e.get("workers"), "fixed_capital": d.get("fixed_capital"),
                     "output": d.get("output"), "gva": d.get("gva"), "nva": d.get("nva")})
    for st in t4:
        if st not in t2 and st != "All-India": note_unmatched(ds, "T4-only:" + st)
    fc = lambda n, u, t, d, h="neutral": F(n, u, t, d, h)
    fields = {"factories": fc("Number of factories", "factories", "count", "Total factories in the ASI frame (ASI Table 2, row 1).", "neutral"),
              "factories_operating": fc("Factories in operation", "factories", "count", "ASI Table 2, row 2.", "neutral"),
              "persons_engaged": fc("Persons engaged", "persons", "count", "Total persons engaged in factories (ASI Table 4, row A).", "better"),
              "workers": fc("Workers", "persons", "count", "Workers in factories (ASI Table 4, row A.1).", "better"),
              "fixed_capital": fc("Fixed capital", "INR lakh", "value", "ASI Table 2, row 3.", "neutral"),
              "output": fc("Total output", "INR lakh", "value", "ASI Table 2, row 15.", "better"),
              "gva": fc("Gross value added", "INR lakh", "value", "ASI Table 2, row 19.", "better"),
              "nva": fc("Net value added", "INR lakh", "value", "ASI Table 2, row 21.", "better")}
    meta = {"name": "Annual Survey of Industries 2023-24: state-wise factory sector, all industries",
            "source_org": "National Statistics Office, MoSPI", "url": "https://www.mospi.gov.in/uploads/latestreleasesfiles/1759232761372-ASI%20Vol%20I%202023-24C-2.pdf",
            "landing_url": "https://www.mospi.gov.in/annual-survey-industries", "published": "2025-09 (Volume I; PIB release of ASI 2023-24)",
            "reference_year": "2023-24", "resolution": "state", "license": "Government Open Data License - India (GODL)", "update_frequency": "annual", "kind": "official",
            "limitations": "Factory sector only (registered factories). Estimates from a sample plus census sector; very small UTs may be missing or merged. Money is in INR lakh as in the report. Counts are for the ASI frame year, not the calendar.",
            "method": "pdftotext -layout. For each state, the first page of ASI Table 2 (by 3-digit industry group), column 'All': rows 1, 2, 3, 15, 19, 21. Persons engaged and workers from the first page of Table 4, column 'All'. No conversion."}
    write(meta, fields, rows, ds)

# ======================================================================
# 5. exports_state (RBI Handbook of Statistics on Indian States, Table 181, via The Maps Daily)
# ======================================================================
def build_exports():
    ds = "exports_state"
    h = open(RAW / "exports" / "tmd.html", errors="ignore").read()
    i0 = h.find("Every State and UT")
    seg = h[i0:]
    rows = {}
    for m in re.finditer(r'<td class="py-1\.5 pr-3 text-ink-800[^"]*">([^<]+)</td><td[^>]*>([\d,]+)</td>', seg):
        name, v = m.group(1).replace("&#x27;", "'"), int(m.group(2).replace(",", ""))
        i = sid(name)
        if not i:
            note_unmatched(ds, name); continue
        rows[i] = {"key": i, "name": NAMES[i], "state": i, "exports_usd_mn": v}
    for i in NAMES:
        rows.setdefault(i, {"key": i, "name": NAMES[i], "state": i, "exports_usd_mn": None})
    total = sum(r["exports_usd_mn"] or 0 for r in rows.values())
    print("   exports sum USD mn:", total)
    fields = {"exports_usd_mn": F("Merchandise exports", "USD million", "count", "State-wise merchandise exports, FY 2024-25 (RBI Handbook Table 181; DGCI&S basis). Values below 1 are shown as 0 in the source (Ladakh, Mizoram).", "better")}
    meta = {"name": "State-wise merchandise exports, FY 2024-25 (RBI Handbook of Statistics on Indian States, Table 181)",
            "source_org": "Reserve Bank of India (Handbook of Statistics on Indian States 2024-25), original data DGCI&S, Ministry of Commerce and Industry",
            "url": "https://themapsdaily.com/posts/in-state-exports", "landing_url": "https://www.rbi.org.in/Scripts/AnnualPublications.aspx?head=Handbook%20of%20Statistics%20on%20Indian%20States",
            "published": "2025-12-11 (RBI Handbook 2024-25 edition)", "reference_year": "2024-25", "resolution": "state", "license": "Not stated by the compiler; RBI data, cite RBI and DGCI&S",
            "update_frequency": "annual", "kind": "curated",
            "redistributed_via": "The Maps Daily (themapsdaily.com) re-keyed RBI Table 181. The RBI file itself (rbidocs.rbi.org.in) answers automated requests with a CAPTCHA page.",
            "limitations": "Secondary compilation of the RBI table. The compiler labels the year '2024'; the all-India total 437,417 USD million matches India's FY 2024-25 merchandise exports, and top-state values (Gujarat 116,332; Karnataka 30,481) match FIEO/other FY 2024-25 listings, so the year is read as FY 2024-25. The 36 state and UT rows sum to 389,294 USD million; the rest of the all-India total (437,417) is not assigned to a state in the source. Export value is booked to the state of origin of the goods as recorded by DGCI&S, which over-states port states.",
            "method": "Parsed the state table from the saved HTML page; no conversion. States with no row would be null (none)."}
    write(meta, fields, list(rows.values()), ds)

if __name__ == "__main__":
    for f in (build_gsdp, build_gsva, build_plfs, build_asi, build_exports):
        f()
