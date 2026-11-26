"""Download Census 2011 Table A-2 (decadal variation in population since 1901).
Source: censusindia.gov.in NADA catalog, entries 43333 (India) to 43368 (Andaman and Nicobar).
Each state file goes to its own file in raw/census_series/a2_xlsx/. The script re-runs safely.
"""
import os, re, sys, time, requests
from common import RAW

UA = {"User-Agent": "india-civ-data-pipeline/1.0"}
BASE = "https://censusindia.gov.in/nada/index.php/catalog/"
OUT = os.path.join(RAW, "census_series", "a2_xlsx")
os.makedirs(OUT, exist_ok=True)

for cid in range(43333, 43369):
    page = requests.get(BASE + str(cid), headers=UA, timeout=60).text
    m = re.search(r'href="([^"]*/download/\d+/[^"]*\.xlsx?)"', page)
    if not m:
        print(cid, "no download link"); continue
    url = m.group(1)
    ext = url.rsplit(".", 1)[1]
    dest = os.path.join(OUT, f"{cid - 43333:02d}.{ext}")
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        continue
    r = requests.get(url, headers=UA, timeout=120)
    r.raise_for_status()
    open(dest, "wb").write(r.content)
    print(cid, url, len(r.content)); time.sleep(0.5)
