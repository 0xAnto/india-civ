"""Fetch raw files for the infrastructure / energy / institutions / heritage topic.
Run: .venv/bin/python -I pipeline/fetch_infra.py   (re-runnable; skips existing files)"""
import json, os, sys, time, requests
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "raw", "infra")
UA = "india-civ-research/0.1 (open data hobby project; python-requests)"
os.makedirs(RAW, exist_ok=True)

def get(url, name, **kw):
    p = os.path.join(RAW, name)
    if os.path.exists(p) and os.path.getsize(p) > 100:
        return
    r = requests.get(url, headers={"User-Agent": UA}, timeout=180, **kw)
    r.raise_for_status()
    open(p, "wb").write(r.content)
    print("ok", name, len(r.content))

def sparql(name, q):
    p = os.path.join(RAW, name)
    if os.path.exists(p) and os.path.getsize(p) > 100:
        return
    for i in range(4):
        try:
            r = requests.post("https://query.wikidata.org/sparql", data={"query": q, "format": "json"},
                              headers={"User-Agent": UA, "Accept": "application/sparql-results+json"}, timeout=200)
            r.raise_for_status()
            open(p, "wb").write(r.content)
            print("ok", name, len(r.content)); return
        except Exception as e:
            print("retry", name, e); time.sleep(10)

PRE = "PREFIX wd: <http://www.wikidata.org/entity/> PREFIX wdt: <http://www.wikidata.org/prop/direct/> PREFIX p: <http://www.wikidata.org/prop/> PREFIX ps: <http://www.wikidata.org/prop/statement/> PREFIX pq: <http://www.wikidata.org/prop/qualifier/> PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> "
SEL = "SELECT ?x ?xLabel ?lat ?lon ?inst ?instLabel ?stateLabel ?inc WHERE { "
def coord(var="?x"):
    return f"{var} p:P625/psv:P625 [wikibase:geoLatitude ?lat; wikibase:geoLongitude ?lon]. "
PRE += "PREFIX psv: <http://www.wikidata.org/prop/statement/value/> PREFIX wikibase: <http://wikiba.se/ontology#> PREFIX bd: <http://www.bigdata.com/rdf#> "
LBL = 'SERVICE wikibase:label { bd:serviceParam wikibase:language "en". } }'


def more():
    sparql("wd_tiger.json", PRE + "SELECT ?x ?xLabel ?lat ?lon ?area ?inc ?stateLabel WHERE { ?x wdt:P31/wdt:P279* wd:Q5533772; wdt:P17 wd:Q668. " + coord() + "OPTIONAL{?x wdt:P2046 ?area} OPTIONAL{?x wdt:P571 ?inc} OPTIONAL{?x wdt:P131 ?state} " + LBL)
    sparql("wd_ports.json", PRE + "SELECT ?x ?xLabel ?lat ?lon ?instLabel ?stateLabel ?wpi WHERE { ?x wdt:P31/wdt:P279* wd:Q44782; wdt:P17 wd:Q668. " + coord() + "OPTIONAL{?x wdt:P31 ?inst} OPTIONAL{?x wdt:P131 ?state} " + LBL)
    sparql("wd_aiims.json", PRE + "SELECT ?x ?xLabel ?lat ?lon ?stateLabel ?inc WHERE { ?x wdt:P361|wdt:P31|wdt:P749 wd:Q3279500. " + coord() + "OPTIONAL{?x wdt:P131 ?state} OPTIONAL{?x wdt:P571 ?inc} " + LBL)
    sparql("wd_asi.json", PRE + "SELECT ?x ?xLabel ?lat ?lon ?asi ?stateLabel WHERE { ?x wdt:P1371 ?asi. " + coord() + "OPTIONAL{?x wdt:P131 ?state} " + LBL)

def orgs():
    ORGC = "{?x wdt:P625 ?c} UNION {?x wdt:P159/wdt:P625 ?c} UNION {?x wdt:P276/wdt:P625 ?c} "
    sparql("wd_research_orgs.json", PRE + "SELECT DISTINCT ?x ?xLabel ?parentLabel ?instLabel ?c WHERE { VALUES ?parent {wd:Q229058 wd:Q3519967 wd:Q3523073 wd:Q1154393} ?x wdt:P749|wdt:P361|wdt:P137|wdt:P127|wdt:P1830|wdt:P108 ?parent. " + ORGC + "OPTIONAL{?x wdt:P31 ?inst} BIND(?parent AS ?parentLabelQ) ?parent rdfs:label ?parentLabel FILTER(LANG(?parentLabel)='en') " + LBL)
    names = ["Hindustan Aeronautics Limited", "Bharat Electronics", "Mazagon Dock Shipbuilders", "Garden Reach Shipbuilders & Engineers", "Cochin Shipyard Limited", "Hindustan Shipyard Limited", "Goa Shipyard Limited", "Bharat Dynamics Limited", "BEML", "Mishra Dhatu Nigam", "Naval Dockyard, Mumbai", "Naval Dockyard, Visakhapatnam", "Indian Coast Guard", "Tata Institute of Fundamental Research", "Bhabha Atomic Research Centre", "Indira Gandhi Centre for Atomic Research", "Raja Ramanna Centre for Advanced Technology", "Variable Energy Cyclotron Centre", "Indian Institute of Science", "Physical Research Laboratory", "Vikram Sarabhai Space Centre", "Satish Dhawan Space Centre", "U. R. Rao Satellite Centre", "Space Applications Centre", "Liquid Propulsion Systems Centre", "National Remote Sensing Centre", "Indian Institute of Space Science and Technology", "ISRO Inertial Systems Unit", "Mahendragiri ISRO Propulsion Complex", "Vikram Sarabhai Space Centre", "Indian Statistical Institute", "Indian Institute of Astrophysics", "National Centre for Biological Sciences", "Raman Research Institute", "Indian Space Research Organisation"]
    vals = " ".join('"%s"@en' % n.replace('"', '') for n in names)
    sparql("wd_named_orgs.json", PRE + "SELECT DISTINCT ?x ?xLabel ?instLabel ?c WHERE { VALUES ?l {" + vals + "} ?x rdfs:label ?l. ?x wdt:P17 wd:Q668. {?x wdt:P625 ?c} UNION {?x wdt:P159/wdt:P625 ?c} OPTIONAL{?x wdt:P31 ?inst} " + LBL)

def inst_search():
    for key, term in [("nit2", "National Institute of Technology"), ("nit3", "Malaviya National Institute of Technology"), ("nit4", "Visvesvaraya National Institute of Technology"), ("nit5", "Motilal Nehru National Institute of Technology"), ("nit6", "Dr. B. R. Ambedkar National Institute of Technology"), ("nit7", "NIT Jamshedpur"), ("nit8", "National Institute of Technology Puducherry"), ("nit9", "National Institute of Technology Uttarakhand"), ("nit10", "National Institute of Technology Arunachal Pradesh"), ("nit11", "National Institute of Technology Mizoram"), ("nit12", "National Institute of Technology Nagaland"), ("nit13", "National Institute of Technology Andhra Pradesh"), ("cu", "Central University"), ("iit2", "IIT"), ("iiit", "Indian Institute of Information Technology"), ("bits", "Birla Institute of Technology and Science"), ("jnu", "Jawaharlal Nehru University"), ("du", "University of Delhi"), ("iiser2", "IISER"), ("aiims2", "AIIMS"), ("iit", "Indian Institute of Technology"), ("nit", "National Institute of Technology"), ("iisc", "Indian Institute of Science"), ("aiims", "All India Institute of Medical Sciences"), ("iiser", "Indian Institute of Science Education and Research"), ("iim", "Indian Institute of Management")]:
        sparql(f"wd_search_{key}.json", PRE + "SELECT DISTINCT ?x ?xLabel ?lat ?lon ?instLabel ?inc WHERE { SERVICE wikibase:mwapi { bd:serviceParam wikibase:api 'EntitySearch'; wikibase:endpoint 'www.wikidata.org'; mwapi:search '" + term + "'; mwapi:language 'en'; mwapi:limit '400'. ?x wikibase:apiOutputItem mwapi:item. } ?x wdt:P17 wd:Q668. " + coord() + "OPTIONAL{?x wdt:P31 ?inst} OPTIONAL{?x wdt:P571 ?inc} " + LBL)


def tiger():
    sparql("wd_tiger2.json", PRE + "SELECT ?x ?xLabel ?lat ?lon ?area ?inc ?stateLabel WHERE { ?x wdt:P31 wd:Q473972; wdt:P17 wd:Q668; rdfs:label ?l. FILTER(LANG(?l)='en' && CONTAINS(LCASE(?l),'tiger reserve')) " + coord() + "OPTIONAL{?x wdt:P2046 ?area} OPTIONAL{?x wdt:P571 ?inc} OPTIONAL{?x wdt:P131 ?state} " + LBL)

def base():
    import zipfile, io
    for n, u in [("ne_rail", "ne_10m_railroads"), ("ne_road", "ne_10m_roads")]:
        if not os.path.exists(os.path.join(RAW, n)):
            r = requests.get(f"https://naciscdn.org/naturalearth/10m/cultural/{u}.zip", headers={"User-Agent": UA}, timeout=300)
            zipfile.ZipFile(io.BytesIO(r.content)).extractall(os.path.join(RAW, n))
    sparql("wd_univ.json", PRE + "SELECT ?x ?xLabel ?lat ?lon ?instLabel ?stateLabel ?inc WHERE { VALUES ?cls {wd:Q3918 wd:Q875538 wd:Q31855 wd:Q1664851 wd:Q4671277 wd:Q23002054 wd:Q2385804 wd:Q15936437 wd:Q38723 wd:Q62078547} ?x wdt:P31 ?cls; wdt:P17 wd:Q668. " + coord() + "OPTIONAL{?x wdt:P31 ?inst} OPTIONAL{?x wdt:P131 ?state} OPTIONAL{?x wdt:P571 ?inc} " + LBL)
    sparql("wd_whs.json", PRE + "SELECT ?x ?xLabel ?lat ?lon ?id ?inc ?crit ?typeLabel ?stateLabel WHERE { ?x p:P1435 ?st. ?st ps:P1435 wd:Q9259. ?x wdt:P17 wd:Q668. " + coord() + "OPTIONAL{?x wdt:P757 ?id} OPTIONAL{?st pq:P580 ?inc} OPTIONAL{?x wdt:P131 ?state} OPTIONAL{?x wdt:P31 ?type} " + LBL)
    sparql("wd_np.json", PRE + "SELECT ?x ?xLabel ?lat ?lon ?instLabel ?area ?inc ?stateLabel WHERE { VALUES ?inst {wd:Q46169} ?x wdt:P31 ?inst; wdt:P17 wd:Q668. " + coord() + "OPTIONAL{?x wdt:P2046 ?area} OPTIONAL{?x wdt:P571 ?inc} OPTIONAL{?x wdt:P131 ?state} " + LBL)
    # UNESCO open data portal (whc.unesco.org itself blocks scripts with a Cloudflare challenge)
    get('https://data.unesco.org/api/explore/v2.1/catalog/datasets/whc001/exports/csv?where=iso_codes%20like%20%22in%22', "whs/whc001.csv") if os.makedirs(os.path.join(RAW, "whs"), exist_ok=True) is None else None

if __name__ == "__main__":
    get("https://raw.githubusercontent.com/wri/global-power-plant-database/master/output_database/global_power_plant_database.csv", "global_power_plant_database.csv")
    get("https://davidmegginson.github.io/ourairports-data/airports.csv", "airports.csv")
    base(); more(); orgs(); inst_search(); tiger()

def tiger3():
    for key, term in [("tiger3", "Tiger Reserve"), ("np3", "National Park"), ("tiger4", "Tiger Project")]:
        sparql(f"wd_pa_{key}.json", PRE + "SELECT DISTINCT ?x ?xLabel ?lat ?lon ?instLabel ?area ?inc ?stateLabel WHERE { SERVICE wikibase:mwapi { bd:serviceParam wikibase:api 'EntitySearch'; wikibase:endpoint 'www.wikidata.org'; mwapi:search '" + term + "'; mwapi:language 'en'; mwapi:limit '500'. ?x wikibase:apiOutputItem mwapi:item. } ?x wdt:P17 wd:Q668. " + coord() + "OPTIONAL{?x wdt:P31 ?inst} OPTIONAL{?x wdt:P2046 ?area} OPTIONAL{?x wdt:P571 ?inc} OPTIONAL{?x wdt:P131 ?state} " + LBL)

def defence_search():
    for key, term in [("cochin", "Cochin Shipyard"), ("hsl", "Hindustan Shipyard"), ("dockyard", "Naval Dockyard"), ("beml", "BEML"), ("coastguard", "Coast Guard"), ("bhel", "Bharat Heavy Electricals")]:
        sparql(f"wd_def_{key}.json", PRE + "SELECT DISTINCT ?x ?xLabel ?instLabel ?c WHERE { SERVICE wikibase:mwapi { bd:serviceParam wikibase:api 'EntitySearch'; wikibase:endpoint 'www.wikidata.org'; mwapi:search '" + term + "'; mwapi:language 'en'; mwapi:limit '40'. ?x wikibase:apiOutputItem mwapi:item. } ?x wdt:P17 wd:Q668. {?x wdt:P625 ?c} UNION {?x wdt:P159/wdt:P625 ?c} OPTIONAL{?x wdt:P31 ?inst} " + LBL)

def nirf_coords():
    qs = sorted(set(json.load(open(os.path.join(ROOT, "pipeline", "nirf2025_qids.json"))).values()))
    sparql("wd_nirf.json", PRE + "SELECT DISTINCT ?x ?xLabel ?lat ?lon ?instLabel ?inc ?approx WHERE { VALUES ?x {" + " ".join("wd:" + q for q in qs) + "} {" + coord() + "} UNION {?x wdt:P131/p:P625/psv:P625 [wikibase:geoLatitude ?lat; wikibase:geoLongitude ?lon]. BIND(true AS ?approx) FILTER NOT EXISTS {?x wdt:P625 ?z}} OPTIONAL{?x wdt:P31 ?inst} OPTIONAL{?x wdt:P571 ?inc} " + LBL)
