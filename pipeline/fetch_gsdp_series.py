"""Download state GDP series into raw/economy_series/ (each source in its own subfolder). Re-runnable.
Sources: MoSPI eSankhyiki NAS API (base 2011-12) and RBI DBIE handbook web pages (no CAPTCHA on dbie.rbihub.in).
Run: ../.venv/bin/python fetch_gsdp_series.py
"""
import json, os, requests
from common import RAW

UA = {"User-Agent": "india-civ-data-pipeline/1.0"}
API = "https://api.mospi.gov.in/api/nas/getNASData"
YEARS = ",".join(f"{y}-{str(y + 1)[2:]}" for y in range(2011, 2026))
D1 = os.path.join(RAW, "economy_series", "mospi_nas_series")
D2 = os.path.join(RAW, "economy_series", "rbi_dbie_hub_series")
os.makedirs(D1, exist_ok=True); os.makedirs(D2, exist_ok=True)

for code, name in [(23, "gsdp"), (24, "nsdp"), (25, "pc_nsdp"), (31, "pc_gsdp")]:
    rows, page = [], 1
    while True:
        r = requests.get(API, params=dict(base_year="2011-12", series="Current", frequency_code="Annually", indicator_code=code,
                                          year=YEARS, Format="JSON", limit=200, page=page), headers=UA, timeout=120)
        r.raise_for_status()
        j = r.json()
        rows += j["data"]
        if page >= j["meta_data"]["totalPages"]:
            break
        page += 1
    json.dump({"indicator_code": code, "data": rows}, open(os.path.join(D1, name + ".json"), "w"))
    print(name, len(rows))

for s in ["net-state-domestic-product-state-wise-at-constant-prices", "net-state-domestic-product-state-wise-at-current-prices",
          "per-capita-net-state-domestic-product-state-wise-at-constant-prices", "per-capita-net-state-domestic-product-state-wise-at-current-prices"]:
    r = requests.get("https://dbie.rbihub.in/handbook/" + s, headers=UA, timeout=120)
    r.raise_for_status()
    open(os.path.join(D2, s + ".html"), "wb").write(r.content)
    print(s, len(r.content))
