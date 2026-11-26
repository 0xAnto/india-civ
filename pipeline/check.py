"""Validation of the published site data. Fails loudly (assert) on integrity problems.
Run after publish.py. Prints a short report."""
import json, math, os
from common import *


def main():
    w = read_json(f"{SITE_DATA}/world.json")
    g = read_json(f"{DATA}/grid/grid.json")
    L = read_json(f"{SITE_DATA}/lenses.json")
    src = {s["id"] for s in read_json(f"{SITE_DATA}/sources.json")}
    land = w["land"]
    rep = []

    # geography
    states_with_hex = {w["state"][i] for i in land}
    assert len(states_with_hex - {-1}) == 36, "every state/UT owns a hex"
    d20 = {w["district"][i] for i in land}
    assert len(d20 - {-1}) == len(w["districts"]), "every ~2020 district owns a hex"
    sample_area = sum(g["state_area_km2"])
    rep.append(f"land hexes {len(land)}; India area from samples {sample_area:,.0f} km² (official 3,287,263 km² incl. claimed areas): {sample_area / 3287263 * 100:.1f}%")
    assert 0.95 < sample_area / 3287263 < 1.03
    disputed = [k for k, i in enumerate(land) if w["disputed"][i] >= 0]

    # census totals
    c = read_json(f"{DATA}/normalized/census2011_district.json")
    pop = sum(r["population"] for r in c["rows"])
    assert pop == 1210854977, pop
    rep.append("census 2011 population total = 1,210,854,977 (official)")

    # lenses: sources, disputed hexes missing, values finite
    for l in L["lenses"]:
        assert l["source"] in src or l["source"] == "mechanics", f"lens {l['id']} source {l['source']} not in sources"
        lf = read_json(f"{SITE_DATA}/lens/{l['id']}.json")
        for vals in [lf["values"], *lf.get("series", [])]:  # time lenses: every year passes the same tests
            assert len(vals) == len(land), l["id"]
            assert all(vals[k] is None for k in disputed), f"lens {l['id']} has values in non-administered areas"
            assert all(v is None or math.isfinite(v) for v in vals), l["id"]
        if lf.get("series"):
            assert lf["series"][-1] == lf["values"] and len(lf["years"]) == len(lf["series"]), l["id"]
        vals = lf["values"]
        n = sum(v is not None for v in vals)
        if l["id"].startswith("y_"):
            continue
        assert n >= 50, l["id"]
    n_ser = sum(1 for l in L["lenses"] if l.get("series"))
    rep.append(f"{n_ser} time-series lenses: every year checked")
    rep.append(f"{len(L['lenses'])} lenses: sources known, no values in {len(disputed)} non-administered hexes, all finite")

    # hidden strengths: scores are standardised residuals (mean ~0, sd ~1)
    hs = read_json(f"{SITE_DATA}/strengths.json")
    for m in hs["models"]:
        z = [v for v in read_json(f"{SITE_DATA}/table_{m['table']}.json")["cols"][f"{m['dataset']}.{m['id']}_score"] if v is not None]
        mu = sum(z) / len(z); sd = (sum((v - mu) ** 2 for v in z) / len(z)) ** 0.5
        assert len(z) == m["n"] and abs(mu) < 0.05 and abs(sd - 1) < 0.05, (m["id"], len(z), mu, sd)
    rep.append(f"{len(hs['models'])} hidden-strength models: " + ", ".join(f"{m['id']} n={m['n']} R²={m['r2']:.2f}" for m in hs["models"]))
    # advisors: every evidence dataset is a known source
    adv = read_json(f"{SITE_DATA}/advisors.json")
    n_ins = 0
    for a in adv:
        for ins in a["insights"]:
            n_ins += 1
            for e in ins["evidence"]:
                assert e["dataset"] in src, f"advisor evidence {e['dataset']} not in sources"
    rep.append(f"{n_ins} advisor observations, every one traced to a source record")

    # cities on Indian land
    cities = read_json(f"{SITE_DATA}/cities.json")
    off = [c["name"] for c in cities if not c.get("cells")]
    assert not off, f"cities without an Indian land hex: {off}"
    rep.append(f"{len(cities)} cities, all on Indian land hexes; {sum(1 for c in cities if c['population'])} with a Census 2011 population")

    # yields: non-negative
    hy = read_json(f"{SITE_DATA}/hexyields.json")
    for y, p in hy["pips"].items():
        assert min(p) >= 0 and max(p) <= 4, y
    n = read_json(f"{SITE_DATA}/nation.json")
    rep.append("national yields: " + ", ".join(f"{k}={v:,.0f}" for k, v in n["yields"].items()))
    if n.get("validation"):
        v = n["validation"]
        rep.append(f"gold model check (Maharashtra district GDP, n={v['n']}): r={v['r_nonfarm']:.3f}, median error {v['err_nonfarm']:.1f}%")

    # sizes
    tot = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(SITE_DATA) for f in fs)
    rep.append(f"site/data size {tot / 1e6:.1f} MB")
    print("CHECK OK\n  " + "\n  ".join(rep))


if __name__ == "__main__":
    main()
