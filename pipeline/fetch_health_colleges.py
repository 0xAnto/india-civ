"""Fetch the NMC MBBS college list (public JSON endpoint of the NMC search page) and Wikidata
coordinates into raw/health/mc/. Re-runnable."""
import pathlib, requests
RAW = pathlib.Path(__file__).resolve().parent.parent / "raw/health/mc"
RAW.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "india-civ-research/0.1"}
r = requests.get("https://www.nmc.org.in/information-desk-college-and-course-search/search",
                 params={"course_name": "M.B.B.S.", "page": 1, "per_page": 1000},
                 headers={**UA, "Accept": "application/json"}, timeout=120)
r.raise_for_status(); (RAW / "nmc_mbbs.json").write_bytes(r.content)
Q_MC = """SELECT ?item ?itemLabel ?coord ?locLabel ?cls WHERE {
  VALUES ?cls { wd:Q494230 wd:Q17072837 wd:Q6040591 }
  ?item wdt:P31 ?cls ; wdt:P17 wd:Q668 ; wdt:P625 ?coord .
  OPTIONAL{?item wdt:P131 ?loc}
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". } }"""
Q_AIIMS = """SELECT DISTINCT ?item ?itemLabel ?coord ?locLabel WHERE {
  ?item wdt:P31 wd:Q47531586 ; wdt:P625 ?coord ; rdfs:label ?l .
  FILTER(LANG(?l)="en" && STRSTARTS(?l,"All India Institute of Medical Sciences"))
  OPTIONAL{?item wdt:P131 ?loc}
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". } }"""
for name, q in [("wd_medical_colleges.json", Q_MC), ("wd_aiims.json", Q_AIIMS)]:
    r = requests.get("https://query.wikidata.org/sparql", params={"query": q},
                     headers={**UA, "Accept": "application/sparql-results+json"}, timeout=180)
    r.raise_for_status(); (RAW / name).write_bytes(r.content); print(name, len(r.content))
