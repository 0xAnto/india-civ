"""Mark ASI monuments that Wikidata classifies as places of worship (or stupas, monasteries,
dargahs), and record the tradition from the class label. Adds `religious` and `religion_class`
to data/normalized/asi_monuments.json.

Rule: the monument item is an instance of (P31) a class that is a subclass (P279*) of
place of worship (Q1370598), stupa (Q180987), monastery (Q44613) or dargah (Q1050451).
"""
import json, os, time
import requests
from common import *

ENDPOINT = "https://query.wikidata.org/sparql"
UA = {"User-Agent": "india-civ-data-pipeline/1.0 (public-data research project)", "Accept": "application/sparql-results+json"}
ROOTS = "wd:Q1370598 wd:Q180987 wd:Q44613 wd:Q1050451"
CACHE = f"{RAW}/faith/wikidata_worship.json"


def query(qids):
    vals = " ".join(f"wd:{q}" for q in qids)
    q = f"""SELECT ?item ?cls ?clsLabel WHERE {{ VALUES ?item {{ {vals} }} VALUES ?root {{ {ROOTS} }}
      ?item wdt:P31 ?cls . ?cls wdt:P279* ?root .
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }} }}"""
    for attempt in range(4):
        r = requests.post(ENDPOINT, data={"query": q}, headers=UA, timeout=120)
        if r.status_code == 200:
            return r.json()["results"]["bindings"]
        time.sleep(5 * (attempt + 1))
    r.raise_for_status()


def main():
    p = f"{DATA}/normalized/asi_monuments.json"
    d = read_json(p)
    qids = [r["key"] for r in d["rows"] if str(r["key"]).startswith("Q")]
    if os.path.exists(CACHE):
        hits = read_json(CACHE)
    else:
        hits = {}
        for i in range(0, len(qids), 300):
            for b in query(qids[i:i + 300]):
                q = b["item"]["value"].rsplit("/", 1)[1]
                hits.setdefault(q, set()).add(b["clsLabel"]["value"])
            time.sleep(1)
        hits = {k: sorted(v) for k, v in hits.items()}
        write_json(CACHE, hits)
    n = 0
    for r in d["rows"]:
        cl = hits.get(r["key"])
        r["religious"] = bool(cl)
        r["religion_class"] = ", ".join(cl) if cl else None
        n += bool(cl)
    d["fields"]["religious"] = {"name": "Place of worship (Wikidata class)", "type": "text", "description": "True when the item's class is a subclass of place of worship, stupa, monastery or dargah in Wikidata."}
    d["fields"]["religion_class"] = {"name": "Wikidata class", "type": "text"}
    if "build_faith_sites" not in d["meta"].get("method", ""):
        d["meta"]["method"] = d["meta"].get("method", "") + " Religious flag (pipeline/build_faith_sites.py): Wikidata P31/P279* place of worship (Q1370598), stupa (Q180987), monastery (Q44613) or dargah (Q1050451)."
    write_json(p, d, compact=False)
    print("monuments", len(d["rows"]), "places of worship", n)


if __name__ == "__main__":
    main()
