"""Download health sources into raw/health/. Re-runnable."""
import pathlib, sys, requests
RAW = pathlib.Path(__file__).resolve().parent.parent / "raw" / "health"
RAW.mkdir(parents=True, exist_ok=True)
GH = "https://raw.githubusercontent.com"
FILES = {
    "jv_districts.csv": GH + "/jvargh7/nfhs5_factsheets/main/data%20for%20analysis/districts.csv",
    "jv_states.csv": GH + "/jvargh7/nfhs5_factsheets/main/data%20for%20analysis/states.csv",
    "NFHS-5-Districts.csv": GH + "/pratapvardhan/NFHS-5/master/NFHS-5-Districts.csv",
    "NFHS-5-States.csv": GH + "/pratapvardhan/NFHS-5/master/NFHS-5-States.csv",
}
if len(sys.argv) > 1:  # extra "name=url" pairs
    FILES.update(dict(a.split("=", 1) for a in sys.argv[1:]))
for name, url in FILES.items():
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    (RAW / name).write_bytes(r.content)
    print(name, len(r.content))
