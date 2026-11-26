"""Fetch district-wise area/production/yield (APY) for 2022-23 from the DES portal data.desagri.gov.in.
Saves each response as raw/agri/apy/<kind>_<state>_<crop>.html. Re-runnable: skips files that exist.
Run: .venv/bin/python -I pipeline/fetch_apy.py"""
import os, re, sys, time, requests, urllib3
# The server sends an incomplete certificate chain (Python cannot verify it; macOS curl can). Data is public and read-only, so verify=False is used.
urllib3.disable_warnings()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = f"{ROOT}/raw/agri/apy"; os.makedirs(OUT, exist_ok=True)
BASE = "https://data.desagri.gov.in"
UA = {"User-Agent": "Mozilla/5.0 (india-civ research; contact via repo)"}
YEAR = "2022"  # agricultural year 2022-23
STATES = [35,28,12,18,10,4,22,26,25,7,30,24,6,2,1,20,29,32,37,31,23,27,14,17,15,13,21,34,3,8,11,33,36,38,16,9,5,19]
QCROPS = {"rice": 1, "wheat": 2, "maize": 5, "cotton": 26, "sugarcane": 62}
GROUPS = {"cereals": 1, "pulses": 2, "foodgrains": 3, "oilseeds": 4}
def session(page):
    s = requests.Session(); s.headers.update(UA); s.verify = False
    h = s.get(f"{BASE}/website/{page}", timeout=40).text
    tok = re.search(r'hdnrltoken" name="_token" value="([^"]+)"', h).group(1)
    return s, tok
def post(s, tok, path, page, data, name):
    fn = f"{OUT}/{name}.html"
    if os.path.exists(fn) and os.path.getsize(fn) > 200: return
    for k in range(3):
        r = s.post(f"{BASE}{path}", data=data + [("_token", tok)], headers={"X-Requested-With": "XMLHttpRequest", "Referer": f"{BASE}/website/{page}"}, timeout=90)
        if r.status_code == 200 and "<table" in r.text.lower(): break
        time.sleep(2)
    open(fn, "w").write(r.text if r.status_code == 200 else "")
    time.sleep(0.5)
if __name__ == "__main__":
    s, tok = session("apy-query-report-web")
    for st in STATES:
        for cn, c in QCROPS.items():
            d = [("fltrstates[]", st), ("fltrdistricts[]", "all"), ("fltrcrops[]", c)] + [("fltrseason[]", x) for x in "KRSWAY"] + [("fltrstartyear", YEAR), ("fltrendyear", YEAR), ("fltrrptformat", "scrview"), ("fltrcontribut", "all")]
            post(s, tok, "/report/crop/apy-query-report-show", "apy-query-report-web", d, f"q_{st}_{cn}")
    s, tok = session("crops-report-district-level-web")
    for st in STATES:
        for gn, g in GROUPS.items():
            d = [("fltrstates[]", st), ("fltrcrops", g), ("fltrstartyear", YEAR), ("fltrendyear", YEAR), ("fltrrptformat", "scrview")]
            post(s, tok, "/report/crop/report-district-level", "crops-report-district-level-web", d, f"g_{st}_{gn}")
    print("done", len(os.listdir(OUT)))
