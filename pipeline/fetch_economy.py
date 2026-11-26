"""Download economy sources into raw/economy/. Re-runnable. Run: .venv/bin/python -I pipeline/fetch_economy.py"""
import json, pathlib, requests, time
RAW = pathlib.Path(__file__).resolve().parent.parent / "raw" / "economy"
UA = {"User-Agent": "Mozilla/5.0"}
API = "https://api.mospi.gov.in/api/nas/getNASData"
YEARS = ",".join(f"{y}-{str(y+1)[2:]}" for y in range(2011, 2025))

def get(url, out, **kw):
    r = requests.get(url, headers=UA, timeout=120, **kw)
    r.raise_for_status()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(r.content)
    print("saved", out, len(r.content))

def nas(code, years, name):
    """The API caps limit at 200 records per page: follow pages and merge."""
    rows, page = [], 1
    while True:
        p = dict(base_year="2011-12", series="Current", frequency_code="Annually", indicator_code=code,
                 year=years, Format="JSON", limit=200, page=page)
        r = requests.get(API, params=p, headers=UA, timeout=120)
        r.raise_for_status()
        j = r.json()
        rows += j["data"]
        if page >= j["meta_data"]["totalPages"]:
            break
        page += 1
    out = RAW / "mospi_nas" / f"{name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"query": {"indicator_code": code, "year": years}, "data": rows}))
    print("saved", out, len(rows))

for code, name in [(23, "gsdp"), (24, "nsdp"), (25, "pc_nsdp"), (31, "pc_gsdp")]:
    nas(code, YEARS, name)
for y in ("2022-23", "2023-24", "2024-25"):
    nas(29, y, f"gsva_{y}")
get("https://www.mospi.gov.in/uploads/publications_reports/publications_reports1780040415321_0624fb13-fb47-40bc-b470-7c7e9635c3ef_PLFS_2025_F_REV_29052026.pdf",
    RAW / "plfs" / "ar2025rev.pdf")
get("https://www.mospi.gov.in/uploads/latestreleasesfiles/1759232761372-ASI%20Vol%20I%202023-24C-2.pdf",
    RAW / "asi" / "asi_vol1_2023_24.pdf")
get("https://themapsdaily.com/posts/in-state-exports", RAW / "exports" / "tmd.html")
# RBI DBIE handbook pages (embedded JSON)
for s in ["net-state-domestic-product-state-wise-at-current-prices", "per-capita-net-state-domestic-product-state-wise-at-current-prices"]:
    get(f"https://dbie.rbihub.in/handbook/{s}", RAW / "rbi" / f"hub_{s}.html")
get("https://mahaces.maharashtra.gov.in/files/report/DDP_2022-23_002.pdf", RAW / "ddp" / "mh_ddp_2022_23.pdf")
