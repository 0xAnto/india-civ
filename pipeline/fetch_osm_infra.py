"""Fetch OSM main railway lines and National Highway ways from Overpass in 5x5 degree tiles.
Re-runnable: skips tiles that exist. Output: raw/infra/osm/<kind>_<lat>_<lon>.json"""
import os, sys, time, requests
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "raw", "infra", "osm"); os.makedirs(OUT, exist_ok=True)
UA = "india-civ-research/0.1 (open data hobby project; python-requests)"
EPS = ["https://overpass.kumi.systems/api/interpreter", "https://overpass-api.de/api/interpreter"]
Q = {"rail": 'way["railway"="rail"]["usage"="main"]',
     "nh": 'way["highway"~"^(motorway|trunk|primary)$"]["ref"~"^(NH|AH|NE|[A-Z]*[0-9]*;?NH)"]'}
Q["nh"] = 'way["highway"~"^(motorway|trunk)$"]["ref"~"^NH"]'
SKIP = {(6,68),(6,73),(6,83),(6,88),(6,93),(11,68),(11,93),(16,68),(16,93),(21,93),(26,68),(31,68),(31,93),(36,68),(36,73)}
for kind in (sys.argv[1:] or Q):
    for lat in range(6, 37, 5):
        for lon in range(68, 98, 5):
            if kind == "nh" and (lat, lon) in SKIP: continue
            p = os.path.join(OUT, f"{kind}_{lat}_{lon}.json")
            if os.path.exists(p): continue
            body = f'[out:json][timeout:240];{Q[kind]}({lat},{lon},{lat+5},{lon+5});out geom qt;'
            for att in range(6):
                try:
                    r = requests.post(EPS[att % 2], data={"data": body}, headers={"User-Agent": UA}, timeout=300)
                    if r.status_code == 200 and r.content.startswith(b"{"):
                        open(p, "wb").write(r.content); print("ok", p, len(r.content), flush=True); break
                    print("fail", kind, lat, lon, r.status_code, flush=True)
                except Exception as e:
                    print("err", kind, lat, lon, e, flush=True)
                time.sleep(15)
