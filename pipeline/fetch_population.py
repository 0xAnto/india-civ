"""Download raw files for census2011_district and cities into raw/census and raw/cities."""
import json, sys, urllib.parse, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "india-civ-research/0.1 (open data project)"}
MIRROR = "https://raw.githubusercontent.com/nishusharma1608/India-Census-2011-Analysis/master/india-districts-census-2011.csv"
API = "https://en.wikipedia.org/w/api.php"

def get(url, out):
    out.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers=UA)
    import time
    for k in range(6):
        try:
            out.write_bytes(urllib.request.urlopen(req, timeout=90).read()); break
        except urllib.error.HTTPError as e:
            if e.code != 429: raise
            time.sleep(15 * (k + 1))
    print("ok", out)

def wiki(page, out):
    q = urllib.parse.urlencode({"action": "parse", "format": "json", "prop": "wikitext", "page": page, "redirects": 1})
    get(f"{API}?{q}", out)

if __name__ == "__main__":
    get(MIRROR, ROOT / "raw/census/india-districts-census-2011.csv")
    wiki("List_of_million-plus_urban_agglomerations_in_India", ROOT / "raw/cities/ua.json")
    wiki("List_of_cities_in_India_by_population", ROOT / "raw/cities/cities.json")

# ---- step 2: Wikipedia page -> Wikidata QID, Wikipedia coordinates, Wikidata P625 coordinates
import re
CAPITALS = ["Amaravati", "Itanagar", "Dispur", "Patna", "Raipur", "Panaji", "Gandhinagar", "Chandigarh", "Shimla",
            "Ranchi", "Bengaluru", "Thiruvananthapuram", "Bhopal", "Mumbai", "Imphal", "Shillong", "Aizawl",
            "Kohima", "Bhubaneswar", "Jaipur", "Gangtok", "Chennai", "Hyderabad", "Agartala", "Lucknow",
            "Dehradun", "Kolkata", "Port Blair", "New Delhi", "Srinagar", "Leh", "Kavaratti",
            "Puducherry (city)", "Daman, India"]
LINK = re.compile(r"\[\[([^\]|#]+)")

def titles():
    t = set(CAPITALS)
    ua = json.loads((ROOT / "raw/cities/ua.json").read_text())["parse"]["wikitext"]["*"]
    ua = ua[ua.find('{| class="wikitable sortable sticky'):]
    ua = ua[:ua.find("\n|}")]
    for row in ua.split("\n|-\n")[1:]:
        m = LINK.search(row)
        if m: t.add(m.group(1).strip())
    cw = json.loads((ROOT / "raw/cities/cities.json").read_text())["parse"]["wikitext"]["*"]
    cw = cw[cw.find("== List of cities above 100,000"):]
    for row in cw.split("\n|-\n")[3:]:
        m = LINK.search(row)
        if m: t.add(m.group(1).strip())
    return sorted(t)

def api(base, **p):
    p["format"] = "json"
    import time
    req = urllib.request.Request(base + "?" + urllib.parse.urlencode(p), headers=UA)
    for k in range(6):
        time.sleep(1.5)
        try:
            return json.load(urllib.request.urlopen(req, timeout=90))
        except urllib.error.HTTPError as e:
            if e.code != 429: raise
            time.sleep(10 * (k + 1))
    raise RuntimeError("rate limited")

def resolve():
    ts = titles()
    pages = {}
    for i in range(0, len(ts), 50):
        r = api(API, action="query", titles="|".join(ts[i:i + 50]), prop="pageprops|coordinates", ppprop="wikibase_item",
                redirects=1, colimit="max", coprimary="primary")
        if "query" not in r: print(r)
        q = r["query"]
        alias = {}
        for x in q.get("normalized", []) + q.get("redirects", []):
            alias[x["from"]] = x["to"]
        for pg in q["pages"].values():
            c = pg.get("coordinates", [{}])[0]
            pages[pg["title"]] = {"qid": pg.get("pageprops", {}).get("wikibase_item"),
                                  "wp_lat": c.get("lat"), "wp_lon": c.get("lon")}
        for t in ts[i:i + 50]:
            a = t
            for _ in range(3): a = alias.get(a, a)
            pages.setdefault("__alias__", {})[t] = a
    qids = sorted({v["qid"] for k, v in pages.items() if k != "__alias__" and v["qid"]})
    wd = {}
    for i in range(0, len(qids), 50):
        r = api("https://www.wikidata.org/w/api.php", action="wbgetentities", ids="|".join(qids[i:i + 50]), props="claims")
        for qid, e in r["entities"].items():
            for c in e.get("claims", {}).get("P625", []):
                v = c["mainsnak"].get("datavalue", {}).get("value")
                if v: wd[qid] = {"lat": v["latitude"], "lon": v["longitude"]}; break
    (ROOT / "raw/cities/wikidata.json").write_text(json.dumps({"pages": pages, "wikidata_coords": wd}, indent=1))
    print("resolved", len(ts), "titles;", len(qids), "qids;", len(wd), "with P625")

resolve()
