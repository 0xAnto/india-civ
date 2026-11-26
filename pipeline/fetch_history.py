"""Fetch the history layer sources into raw/history/.
1. aourednik/historical-basemaps GeoJSON files (GPL-3.0).
2. Wikidata items for every place, polity and capital (by enwiki title or QID)."""
import json, sys, time, urllib.parse
from pathlib import Path
import requests
sys.path.insert(0, str(Path(__file__).parent))
import history_config as H

RAW = Path(__file__).resolve().parent.parent / "raw" / "history"
UA = "india-civ-research/0.1 (open-data hex map project; research use)"
BASE = "https://raw.githubusercontent.com/aourednik/historical-basemaps/master/geojson/world_%s.geojson"

def refs():
    out = set()
    def add(r):
        if r: out.add(r)
    for e in H.ERAS:
        for p in e["places"]: add(p["ref"])
        for pol in e["polities"]:
            for c in pol["caps"]: add(c["ref"])
    for rs in H.ROUTES_BY_ERA.values():
        for r in rs:
            for w in r["waypoints"]: add(w)
    return sorted(out)

def is_qid(r): return r[0] == "Q" and r[1:].isdigit()

def sparql(q):
    for t in range(4):
        r = requests.get("https://query.wikidata.org/sparql", params={"query": q, "format": "json"},
                         headers={"User-Agent": UA}, timeout=120)
        if r.status_code == 200: return r.json()["results"]["bindings"]
        time.sleep(5 * (t + 1))
    r.raise_for_status()

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for y in H.BASEMAP_YEARS:
        f = RAW / f"world_{y}.geojson"
        if f.exists() and f.stat().st_size > 1000: continue
        r = requests.get(BASE % y, headers={"User-Agent": UA}, timeout=120); r.raise_for_status()
        f.write_bytes(r.content); print("got", f.name)
    (RAW / "LICENSE-historical-basemaps.txt").write_text(requests.get(
        "https://raw.githubusercontent.com/aourednik/historical-basemaps/master/LICENSE", timeout=60).text)
    rs = refs()
    titles = [r for r in rs if not is_qid(r)]; qids = [r for r in rs if is_qid(r)]
    res = {}
    # Step 1: English Wikipedia API resolves redirects and gives the Wikidata QID.
    t2q = {}; redirects = {}
    for i in range(0, len(titles), 40):
        for attempt in range(6):
            time.sleep(3 * (attempt + 1))
            r = requests.get("https://en.wikipedia.org/w/api.php", headers={"User-Agent": UA}, timeout=60, params={
                "action": "query", "titles": "|".join(titles[i:i+40]), "redirects": 1, "prop": "pageprops",
                "ppprop": "wikibase_item|disambiguation", "format": "json", "formatversion": 2})
            if r.status_code != 429: break
        r.raise_for_status(); j = r.json()["query"]
        for n in j.get("normalized", []): redirects[n["from"]] = n["to"]
        for rd in j.get("redirects", []): redirects[rd["from"]] = rd["to"]
        for pg in j["pages"]:
            pp = pg.get("pageprops", {})
            if "disambiguation" in pp: print("DISAMBIGUATION:", pg["title"]); continue
            if "wikibase_item" in pp: t2q[pg["title"]] = (pg["title"], pp["wikibase_item"])
    def final(t):
        seen = 0
        while t in redirects and seen < 5: t = redirects[t]; seen += 1
        return t
    qmap = {}
    for t in titles:
        ft = final(t)
        if ft in t2q: qmap[t] = (ft, t2q[ft][1])
    allq = sorted({q for _, q in qmap.values()} | set(qids))
    sel = "SELECT ?s ?l ?c ?art WHERE{ VALUES ?s {%s} OPTIONAL{?s rdfs:label ?l. FILTER(lang(?l)='en')} OPTIONAL{?s wdt:P625 ?c} OPTIONAL{?art schema:about ?s; schema:isPartOf <https://en.wikipedia.org/>.}}"
    byq = {}
    for i in range(0, len(allq), 40):
        for b in sparql(sel % " ".join("wd:" + x for x in allq[i:i+40])):
            qid = b["s"]["value"].split("/")[-1]
            d = byq.setdefault(qid, {"qid": qid, "label": b.get("l", {}).get("value"), "coords": [], "wikipedia": None})
            if "c" in b and b["c"]["value"] not in d["coords"]: d["coords"].append(b["c"]["value"])
            if "art" in b: d["wikipedia"] = b["art"]["value"]
    for t, (ft, q) in qmap.items():
        if q in byq: res[t] = dict(byq[q], resolved_title=ft, label=byq[q]["label"] or ft)
    for q in qids:
        if q in byq: res[q] = byq[q]
    for t, (ft, q) in qmap.items():
        if ft != t: print("redirect:", t, "->", ft)
    # polity QIDs (explicit in config): check labels
    pq = sorted({p["qid"] for e in H.ERAS for p in e["polities"] if p["qid"]})
    q = "SELECT ?s ?l WHERE{VALUES ?s {%s} ?s rdfs:label ?l. FILTER(lang(?l)='en')}" % " ".join("wd:" + x for x in pq)
    res["_polity_labels"] = {b["s"]["value"].split("/")[-1]: b["l"]["value"] for b in sparql(q)}
    missing = [r for r in rs if r not in res]
    (RAW / "wikidata_resolved.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print("resolved", len(res) - 1, "of", len(rs), "missing:", missing)

main()
