"""Shared helpers for the resources topic (agriculture, forest, minerals, energy, fisheries)."""
import csv, json, re, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _norm(s):
    s = s.lower().replace("&", "and")
    return re.sub(r"[^a-z0-9]+", "", s)

def load_states():
    m = {}
    for r in csv.DictReader(open(f"{ROOT}/data/ref/states.csv")):
        for n in [r["name"]] + [a for a in r["aliases"].split("|") if a]:
            m[_norm(n)] = r["id"]
    extra = {"telengana": "TG", "tamilnadu": "TN", "chattisgarh": "CT", "andamannicobarislands": "AN",
             "andnislands": "AN", "andamanandnicobar": "AN", "dnhaveli": "DH", "damananddiu": "DH",
             "dadranagarhaveli": "DH", "jammukashmir": "JK", "uttrakhand": "UT", "orissa": "OR",
             "nctofdelhi": "DL", "dnagarhavelianddamananddiu": "DH", "dadraandnagarhavelianddamananddiu": "DH",
             "dandnagarhavelianddamananddiu": "DH", "dnhaveli": "DH", "puducherrypondicherry": "PY", "dadarandnagarhavelianddamananddiu": "DH", "andamanand": "AN", "damanand": "DH", "dandnhaveli": "DH", "dandnagarhaveliand": "DH", "anislands": "AN", "aandnislands": "AN", "dadraandnagar": "DH"}
    m.update(extra)
    return m
STATES = load_states()
def state_id(name):
    return STATES.get(_norm(name.strip().rstrip("*#")))

def write(dataset_id, meta, fields, rows):
    meta = dict(meta, id=dataset_id, accessed="2026-11-26")
    os.makedirs(f"{ROOT}/data/normalized", exist_ok=True)
    json.dump({"meta": meta, "fields": fields, "rows": rows},
              open(f"{ROOT}/data/normalized/{dataset_id}.json", "w"), ensure_ascii=False, indent=1)

def num(t):
    t = t.replace(",", "")
    try: return float(t)
    except ValueError: return None

_NT = re.compile(r"^(?:NA|-|-?\d[\d,]*\.?\d*)$")
def split_row(line):
    """Return (name, [numeric tokens]) for 'Name   1 2 3', or None. Linear time."""
    toks = line.split()
    k = 0
    while k < len(toks) and not _NT.match(toks[k]): k += 1
    if k == 0 or k == len(toks) or not all(_NT.match(t) for t in toks[k:]): return None
    return " ".join(toks[:k]), toks[k:]
