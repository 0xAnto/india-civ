"""Build universities (higher education + research institutions) from Wikidata and NIRF 2025."""
import glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from infra_common import *

def v(b, k): return b.get(k, {}).get("value")
def wkt(c):
    m = re.match(r"Point\(([-\d.]+) ([-\d.]+)\)", c or "")
    return (float(m.group(2)), float(m.group(1))) if m else (None, None)

ent = {}
def add(b, lat, lon):
    q = v(b, "x").rsplit("/", 1)[1]; n = v(b, "xLabel")
    if lat is None or not in_india(lat, lon) or not n or re.fullmatch(r"Q\d+", n): return
    e = ent.setdefault(q, {"name": n, "lat": lat, "lon": lon, "inst": set(), "inc": None})
    if v(b, "instLabel"): e["inst"].add(v(b, "instLabel"))
    if v(b, "inc") and not e["inc"]: e["inc"] = v(b, "inc")[:4]
    if v(b, "approx"): e["approx"] = True
for f in ["wd_univ"] + [os.path.basename(x)[:-5] for x in glob.glob(os.path.join(RAW, "wd_search_*.json"))] + ["wd_aiims", "wd_nirf"]:
    for b in json.load(open(os.path.join(RAW, f + ".json")))["results"]["bindings"]:
        add(b, float(v(b, "lat")), float(v(b, "lon")))

CATS = [  # (category, regex on label, extra condition on instance labels)
 ("IISc", r"^Indian Institute of Science(,| Bengaluru|$)", None),
 ("IISER", r"Indian Institute of Science Education and Research|^IISER", None),
 ("IIT", r"^Indian Institute of Technology|^IIT \(ISM\)|^Indian Institute of Technology \(BHU\)", None),
 ("IIM", r"^Indian Institute of Management", None),
 ("NIT", r"National Institute of Technology|^NIT ", None),
 ("AIIMS", r"^All India Institute of Medical Sciences|^AIIMS", None),
 ("IIIT", r"^Indian Institute of Information Technology|^Atal Bihari Vajpayee Indian Institute of Information", None),
 ("central_university", r"", "central university"),
 ("institute_national_importance", r"", "Institute of National Importance"),
]
BAD = re.compile(r"Metro|building|station|hostel|Hospital$|Library|Alumni|Society|Sports Complex|Stadium", re.I)
def classify(e):
    n = e["name"]
    if BAD.search(n): return None
    for cat, rx, inst in CATS:
        if rx and re.search(rx, n): return cat
        if inst and inst in e["inst"]: return cat
    return None
rows = {}
for q, e in ent.items():
    c = classify(e)
    if c: rows[q] = dict(e, category=c)

# research organisations (ISRO / CSIR / DAE / DRDO)
RES_OK = {"research institute", "laboratory", "research center", "space center", "Moonport", "spaceport", "institution", "institute", "research laboratory", "facility", "university", "factory", "organization"}
RES_BAD = re.compile(r"Board|Directorate|Hospital|Recruitment|Talent|Resource Development|Unit for Research|Antrix|Deep Space|Telemetry|Master Control|Launch Pad|Pragyan|^Vikram$|Bhavini|Nuclear Power Corporation|Proof and Experimental|NISCAIR|Construction|Atomic Minerals|Organisation$", re.I)
PARENT = {"Indian Space Research Organisation": "ISRO", "Council of Scientific and Industrial Research": "CSIR", "Department of Atomic Energy": "DAE", "Defence Research and Development Organisation": "DRDO"}
for b in json.load(open(os.path.join(RAW, "wd_research_orgs.json")))["results"]["bindings"]:
    lat, lon = wkt(v(b, "c")); n = v(b, "xLabel"); inst = v(b, "instLabel")
    if lat is None or not in_india(lat, lon) or RES_BAD.search(n or "") or (inst and inst not in RES_OK): continue
    q = v(b, "x").rsplit("/", 1)[1]
    cat = PARENT[v(b, "parentLabel")]
    if q in rows and rows[q]["category"] not in ("central_university", "institute_national_importance"): continue
    rows[q] = {"name": n, "lat": lat, "lon": lon, "inst": {inst} if inst else set(), "inc": None, "category": cat}
for b in json.load(open(os.path.join(RAW, "wd_named_orgs.json")))["results"]["bindings"]:
    lat, lon = wkt(v(b, "c")); n = v(b, "xLabel"); q = v(b, "x").rsplit("/", 1)[1]
    if lat is None or not in_india(lat, lon) or q in rows: continue
    if re.search(r"TIFR|Tata Institute|Bhabha|Indira Gandhi Centre|Raja Ramanna|Variable Energy|Physical Research|Indian Institute of Astrophysics|National Centre for Biological|Raman Research|Indian Statistical", n):
        rows[q] = {"name": n, "lat": lat, "lon": lon, "inst": set(), "inc": None,
                   "category": "DAE" if re.search(r"Tata Institute|Bhabha|Indira Gandhi Centre|Raja Ramanna|Variable Energy", n) else "research_institute"}
    elif re.search(r"Space Centre|Space Applications|Remote Sensing|Propulsion|Inertial|Space Science", n):
        rows[q] = {"name": n, "lat": lat, "lon": lon, "inst": set(), "inc": None, "category": "ISRO"}

# NIRF 2025 Overall top 100
s = open(os.path.join(RAW, "nirf", "overall_2025.html"), encoding="utf-8", errors="replace").read()
parts = re.split(r"<td>(IR-[A-Z0-9-]+)</td>", s)[1:]
nirf = []
for i in range(0, len(parts), 2):
    body = parts[i + 1]
    name = re.sub(r"\s+", " ", re.sub(r"<[^>]*>", "", body.split("<div")[0])).strip()
    t = re.findall(r"<td[^>]*>\s*([^<]*?)\s*</td>", body.split("</table>")[1])
    nirf.append({"id": parts[i], "name": name, "city": t[0], "state": t[1], "score": float(t[2]), "rank": int(t[3])})
assert len(nirf) == 100
def nm(x):
    x = x.lower().replace("&", "and"); x = re.sub(r"\(.*?\)", " ", x)
    return re.sub(r"[^a-z0-9]+", " ", x).replace(" the ", " ").strip()
allent = dict(ent)
idx = {}
for q, e in allent.items(): idx.setdefault(nm(e["name"]), []).append(q)
NIRF_FIX = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "nirf2025_qids.json")))  # NIRF rank -> QID (hand-checked, for names that do not match by text)
nirf_unmatched = []
for r in nirf:
    q = NIRF_FIX.get(str(r["rank"])) or next((x for k, x in NIRF_FIX.items() if k.startswith(str(r["rank"]) + "|") and r["name"].startswith(k.split("|")[1])), None)
    q = q if q in allent else None
    if not q:
        c = idx.get(nm(r["name"]), [])
        if not c:  # try "<name>, <city>" and name without punctuation
            c = idx.get(nm(r["name"] + " " + r["city"]), []) or [k for k, e in allent.items() if nm(e["name"]) in (nm(r["name"]).replace("institute of ", "institute of "),)]
        if len(c) > 1:  # prefer the one in the same state
            c2 = [k for k in c if state_of(allent[k]["lat"], allent[k]["lon"]) == state_id(r["state"])]
            c = c2 or c
        q = c[0] if c else None
    if not q: nirf_unmatched.append(r); continue
    if q not in rows:
        rows[q] = dict(allent[q], category="other_nirf")
    rows[q]["nirf"] = r
print("NIRF unmatched:", [(r["rank"], r["name"], r["city"]) for r in nirf_unmatched])

out = []
for q, e in sorted(rows.items(), key=lambda kv: (kv[1]["category"], kv[1]["name"])):
    n = e.get("nirf")
    if q == "Q3631118" or e["name"] == "National Institute of Technology, Rourkela":  # Wikidata longitude is wrong (82.9 E, in Chhattisgarh); institute is at 84.90 E
        e = dict(e, lat=22.2536, lon=84.9014)
    out.append({"key": q, "name": e["name"], "lat": round(e["lat"], 5), "lon": round(e["lon"], 5), "category": e["category"],
                "state": state_of(e["lat"], e["lon"]), "founded": int(e["inc"]) if e.get("inc") else None,
                "nirf_rank": n["rank"] if n else None, "nirf_score": n["score"] if n else None,
                "nirf_year": 2025 if n else None, "nirf_id": n["id"] if n else None, "coord_precision": "locality (Wikidata P131)" if e.get("approx") else "site",
                "source_ids": {"wikidata": q}})
write("universities", {
    "name": "Higher education and research institutions (IIT/IIM/NIT/IISER/AIIMS/IISc/central universities, ISRO/CSIR/DAE/DRDO labs) with NIRF 2025 Overall rank",
    "source_org": "Wikidata (CC0); NIRF, Ministry of Education (rank and score)",
    "url": "https://query.wikidata.org/sparql ; https://www.nirfindia.org/Rankings/2025/OverallRanking.html",
    "landing_url": "https://www.nirfindia.org/Rankings/2025/OverallRanking.html",
    "published": "2025-09-04", "reference_year": "2025", "resolution": "point", "license": "Wikidata CC0; NIRF public Government of India data",
    "update_frequency": "annual (NIRF)", "kind": "curated",
    "limitations": "NIRF 2025 is the latest edition found (2026 page returned 404). Coverage of the categories depends on Wikidata labels and coordinates and is not guaranteed complete: see data/meta/universities.md for counts per category. Only the Overall top 100 have rank and score. DRDO labs only if Wikidata lists them with coordinates. Several DRDO/ISRO items share the HQ coordinate of their parent. Founded year is empty if Wikidata has no inception date.",
    "method": "SPARQL pulls from Wikidata (classes: university, research institute, central university, Institute of National Importance, plus name searches). Category from the label (IIT, IIM, NIT, IISER, AIIMS, IISc, IIIT) or the Wikidata class. ISRO/CSIR/DAE/DRDO labs are items with a parent-organisation link to the agency. NIRF names are joined to Wikidata labels by a normalised name (unmatched ones are listed in the meta file). State from point-in-polygon."},
    sub(founded=F("Founded year", "year", "value", "Year of inception in Wikidata"),
        nirf_rank=F("NIRF Overall rank", "rank", "value", "NIRF 2025 Overall category rank (1 = best)", "better"),
        nirf_score=F("NIRF Overall score", "score (0-100)", "value", "NIRF 2025 Overall score", "better"),
        nirf_year=F("NIRF edition", None, "value", "Year of the NIRF edition"), nirf_id=F("NIRF institute id", None, "text", "NIRF institute code"),
        coord_precision=F("Coordinate precision", None, "text", "site = Wikidata point of the institution; locality = point of the place in which it lies")), out)
import collections
print(collections.Counter(r["category"] for r in out))
