"""Build medical_colleges: NMC MBBS colleges geocoded only through Wikidata (matched by name + city).
Unmatched NMC colleges are written to raw/health/mc/unmatched_nmc.csv (not geocoded, not guessed)."""
import csv, json, re, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "raw/health/mc"
STATES = list(csv.DictReader(open(ROOT / "data/ref/states.csv")))
def n0(s): return re.sub(r"[^a-z]", "", s.lower())
SID = {}
for r in STATES:
    for nm in [r["name"]] + [a for a in r["aliases"].split("|") if a]: SID[n0(nm)] = r["id"]
SID.update({"andamanandnicobarislands": "AN", "delhi": "DL", "jammuandkashmir": "JK",
            "dadraandnagarhavelianddamananddiu": "DH", "dnhdd": "DH", "uttarakhand": "UT"})
STOP = {"the", "of", "and", "in", "at", "for"}
SYN = {"govt": "government", "inst": "institute", "med": "medical", "hosp": "hospital", "sciences": "science",
       "bengaluru": "bangalore", "mysuru": "mysore", "kolkata": "calcutta", "chennai": "madras", "mumbai": "bombay",
       "thiruvananthapuram": "trivandrum", "puducherry": "pondicherry", "vadodara": "baroda"}
def toks(s):
    s = s.lower().replace("&", " and ")
    t = [SYN.get(w, w) for w in re.findall(r"[a-z]+", s)]
    return [w for w in t if w not in STOP]
def key(s): return " ".join(toks(s))
def pt(c):
    m = re.match(r"Point\(([-\d.]+) ([-\d.]+)\)", c); return float(m.group(2)), float(m.group(1))

wd = {}
for fn in ["wd_medical_colleges.json", "wd_aiims.json"]:
    for b in json.load(open(RAW / fn))["results"]["bindings"]:
        q = b["item"]["value"].rsplit("/", 1)[-1]
        e = wd.setdefault(q, {"qid": q, "label": b["itemLabel"]["value"], "loc": set(), "coord": pt(b["coord"]["value"])})
        if "locLabel" in b: e["loc"].add(b["locLabel"]["value"])
for q in [q for q, e in wd.items() if re.match(r"^Q\d+$", e["label"])]: del wd[q]  # no English label

nmc = json.load(open(RAW / "nmc_mbbs.json"))["data"]
cands = []  # (score, nmc index, qid)
for i, c in enumerate(nmc):
    full = c["college_name"]; parts = [p.strip() for p in full.split(",")]
    city = parts[-1] if len(parts) > 1 else ""
    ctok = set(toks(city))
    names = {key(full), key(parts[0])}
    for q, e in wd.items():
        lk = key(e["label"]); lt = set(lk.split())
        ltoks = lt | {w for l in e["loc"] for w in toks(l)}
        city_ok = bool(ctok) and ctok <= ltoks
        if lk in names and (city_ok or lk == key(full) or not ctok):
            cands.append((3 if lk == key(full) else 2.5, i, q)); continue
        if city_ok:
            for nm in names:
                a = set(nm.split()); j = len(a & lt) / len(a | lt)
                if j >= 0.8: cands.append((j, i, q)); break
cands.sort(reverse=True)
used_i, used_q, match = set(), set(), {}
for s, i, q in cands:
    if i in used_i or q in used_q: continue
    used_i.add(i); used_q.add(q); match[i] = (q, s)

def cat(name): return "aiims" if re.match(r"all india institute of medical sciences", name, re.I) else "medical_college"
rows, unmatched = [], []
for i, c in enumerate(nmc):
    if i not in match: unmatched.append(c); continue
    q, s = match[i]; e = wd[q]
    parts = [p.strip() for p in c["college_name"].split(",")]
    rows.append({"key": q, "name": c["college_name"], "lat": e["coord"][0], "lon": e["coord"][1],
        "category": cat(c["college_name"]), "state": SID.get(n0(c["state_name"])), "wikidata_label": e["label"],
        "nmc_code": c["college_code"], "management": c["management_type"],
        "inception_year": c["inception_year"], "mbbs_seats": c["approved_seat"], "match_score": round(s, 2)})
nm_q = {r["key"] for r in rows}
# AIIMS from Wikidata that have no NMC match (still real AIIMS institutions with coordinates)
for q, e in wd.items():
    if q in nm_q or not re.match(r"all india institute of medical sciences", e["label"], re.I): continue
    rows.append({"key": q, "name": e["label"], "lat": e["coord"][0], "lon": e["coord"][1], "category": "aiims",
        "state": None, "wikidata_label": e["label"], "nmc_code": None, "management": None,
        "inception_year": None, "mbbs_seats": None, "match_score": None})
with open(RAW / "unmatched_nmc.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["college_code", "college_name", "state_name", "management_type"])
    for c in unmatched: w.writerow([c["college_code"], c["college_name"], c["state_name"], c["management_type"]])
def fd(name, unit, t, hi, desc): return {"name": name, "unit": unit, "type": t, "description": desc, "higher_is": hi}
fields = {
 "mbbs_seats": fd("Approved MBBS seats", "seats", "count", "better", "Approved seats for the latest NMC academic year in the list (AY 2026-27 in the file used)."),
 "inception_year": fd("Year of inception", "year", "value", "neutral", "Year the college started (NMC)."),
 "match_score": fd("Name match score", "ratio", "value", "neutral", "3 = exact full-name match, 2.5 = exact name before the comma, below 2 = token overlap with city check."),
}
meta = dict(id="medical_colleges", name="Medical colleges (NMC MBBS list) and AIIMS, located through Wikidata",
 source_org="National Medical Commission, India (list); Wikidata (coordinates)",
 url="https://www.nmc.org.in/information-desk-college-and-course-search/search?course_name=M.B.B.S.&per_page=1000",
 landing_url="https://www.nmc.org.in/information-desk-college-and-course-search",
 published="2026-11", reference_year="2026", resolution="point",
 license="NMC public list; Wikidata CC0", update_frequency="annual", kind="curated",
 limitations=f"NMC lists {len(nmc)} MBBS colleges; only {len(match)} could be matched to a Wikidata item with coordinates. The rest are not geocoded and are not in this file (list: raw/health/mc/unmatched_nmc.csv). The match is automatic (name plus city) and can be wrong for look-alike names. Row key is the Wikidata QID. AIIMS rows without an NMC record have null state and seats.",
 method="Download the NMC JSON (course M.B.B.S.), query Wikidata for items of class medical school, medical college in India, Institute of Medical Sciences, and AIIMS institutes with coordinates, match by normalised name and city token, one NMC row to one QID, best score first. No coordinate is estimated.",
 accessed="2026-11-26")
(ROOT / "data/normalized/medical_colleges.json").write_text(json.dumps({"meta": meta, "fields": fields, "rows": rows}, ensure_ascii=False, indent=1))
print(f"NMC {len(nmc)}; matched {len(match)}; unmatched {len(unmatched)}; rows {len(rows)}; aiims {sum(r['category']=='aiims' for r in rows)}")
import collections; print(collections.Counter(round(r['match_score'] or 0,1) for r in rows).most_common(8))
print([r['name'] for r in rows if r['match_score'] and r['match_score']<2][:15])
