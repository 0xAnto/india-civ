"""Download the PDF and query sources for the resources topic (agri, forest, minerals, energy, fisheries).
The APY district data comes from fetch_apy.py. Re-runnable: skips existing files. Run: .venv/bin/python -I pipeline/fetch_resources.py
After download, make the text files with:  pdftotext -layout <pdf> <txt>   (poppler)"""
import os, requests, urllib3
urllib3.disable_warnings()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = {
 "agri/asg2024-25.pdf": "https://nccd.gov.in/uploads/Agricultural_Statisitcs_at_a_Glance_2024_25_11da3cd37d.pdf",
 "agri/lus2022-23.pdf": "https://desagri.gov.in/wp-content/uploads/2024/09/Final-file-of-LUS-2022-23-for-uploading.pdf",
 "forest/isfr2023_v1.pdf": "https://fsi.nic.in/uploads/isfr2023/isfr_book_eng-vol-1_2023.pdf",
 "forest/isfr2023_v2.pdf": "https://fsi.nic.in/uploads/isfr2023/isfr_book_eng-vol-2_2023.pdf",
 "minerals/imyb2024.pdf": "https://ibm.gov.in/writereaddata/files/177426215469c1178a48453IMYB_2024_EBookFinal.pdf",
 "minerals/coal_stats_2024-25.pdf": "https://coal.gov.in/sites/default/files/2024-03/28-11-2025a-stc.pdf",
 "energy/mnre_state_re_2026-01-31.pdf": "https://cdnbbsr.s3waas.gov.in/s3716e1b8c6cd17b771da77391355749f3/uploads/2026/02/202602091660392380.pdf",
 "energy/mpr_Mar2026.pdf": "https://mopng.gov.in/files/petroleumStatistics/monthlyProduction/MPR-March-26.pdf",
 "fisheries/handbook2020.pdf": "https://www.dof.gov.in/static/uploads/2025/09/df5962d4c1cbaf9b18bb2a71e715c091.pdf",
}
SPARQL = """SELECT ?i ?iLabel ?c ?tLabel ?stLabel WHERE { VALUES ?t {wd:Q12091026 wd:Q820477 wd:Q211748 wd:Q1349255 wd:Q959309 wd:Q188040}
 ?i wdt:P31 ?t; wdt:P17 wd:Q668; wdt:P625 ?c. OPTIONAL{?i wdt:P131 ?st} SERVICE wikibase:label {bd:serviceParam wikibase:language "en".} }"""
for rel, url in FILES.items():
    fn = f"{ROOT}/raw/{rel}"
    if os.path.exists(fn): continue
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=300, verify=False)
    r.raise_for_status(); open(fn, "wb").write(r.content); print("got", rel, len(r.content))
fn = f"{ROOT}/raw/minerals/wd_fields.csv"
if not os.path.exists(fn):
    r = requests.get("https://query.wikidata.org/sparql", params={"query": SPARQL}, headers={"Accept": "text/csv", "User-Agent": "india-civ-research/0.1"}, timeout=120)
    r.raise_for_status(); open(fn, "wb").write(r.content)
