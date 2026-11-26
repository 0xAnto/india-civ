"""Build seaports: curated list of Indian seaports with Wikidata coordinates and
cargo handled at the 12 major ports (MoPSW report, FY 2025-26)."""
import json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from infra_common import *

wd = {}
for b in json.load(open(os.path.join(RAW, "wd_ports.json")))["results"]["bindings"]:
    q = b["x"]["value"].rsplit("/", 1)[1]
    wd.setdefault(q, (float(b["lat"]["value"]), float(b["lon"]["value"]), b["xLabel"]["value"]))

# key, display name, Wikidata QID, category, order in MoPSW major-port table (None = not a major port)
PORTS = [
 ("kolkata", "Syama Prasad Mukherjee Port, Kolkata (incl. Haldia)", "Q7231171", "major", "SMP"),
 ("paradip", "Paradip Port", "Q7134171", "major", "Paradip"),
 ("visakhapatnam", "Visakhapatnam Port", "Q7935583", "major", "Visakhapatnam"),
 ("kamarajar", "Kamarajar Port (Ennore)", "Q10986919", "major", "Kamarajar"),
 ("chennai", "Chennai Port", "Q3524002", "major", "Chennai"),
 ("voc", "V.O. Chidambaranar Port (Tuticorin)", "Q12988613", "major", "V.O.C."),
 ("cochin", "Cochin Port", "Q5139316", "major", "Cochin"),
 ("new_mangalore", "New Mangalore Port", "Q26780951", "major", "New Mangalore"),
 ("mormugao", "Mormugao Port", "Q60296757", "major", "Mormugao"),
 ("mumbai", "Mumbai Port", "Q15260223", "major", "Mumbai"),
 ("jnpa", "Jawaharlal Nehru Port (Nhava Sheva)", "Q1984452", "major", "JNPA"),
 ("deendayal", "Deendayal Port (Kandla)", "Q64859173", "major", "Deendayal"),
 ("mundra", "Mundra Port", "Q20650238", "non_major", None),
 ("pipavav", "Pipavav Port", "Q7230862", "non_major", None),
 ("hazira", "Hazira Port", "Q5688293", "non_major", None),
 ("dahej", "Dahej Port", "Q7231119", "non_major", None),
 ("navlakhi", "Navlakhi Port", "Q7231212", "non_major", None),
 ("sikka", "Sikka Port", "Q111387331", "non_major", None),
 ("vadinar", "Vadinar Terminal", "Q111386911", "non_major", None),
 ("okha", "Okha Port", "Q111387057", "non_major", None),
 ("porbandar", "Porbandar Port", "Q111386490", "non_major", None),
 ("veraval", "Veraval Port", "Q111387008", "non_major", None),
 ("dighi", "Dighi Port", "Q114633218", "non_major", None),
 ("jaigad", "Jaigad Port", "Q114649340", "non_major", None),
 ("dharamtar", "Dharamtar Port", "Q5269138", "non_major", None),
 ("karwar", "Karwar Port", "Q111387011", "non_major", None),
 ("krishnapatnam", "Krishnapatnam Port", "Q6437585", "non_major", None),
 ("gangavaram", "Gangavaram Port", "Q5521085", "non_major", None),
 ("kakinada", "Kakinada Port", "Q6349454", "non_major", None),
 ("machilipatnam", "Machilipatnam Port", "Q23585025", "non_major", None),
 ("karaikal", "Karaikal Port", "Q6367985", "non_major", None),
 ("nagapattinam", "Nagapattinam Port", "Q17072061", "non_major", None),
 ("kollam", "Kollam Port", "Q17067699", "non_major", None),
 ("vizhinjam", "Vizhinjam International Seaport", "Q7938012", "non_major", None),
 ("port_blair", "Port Blair Port", "Q55886132", "non_major", None),
 ("vadhavan", "Vadhavan Port (under development)", "Q96689512", "planned", None),
]

# MoPSW PDF: FY 2025-26 total per port = 6th numeric column of each "Total" row
txt = subprocess.run(["pdftotext", "-layout", os.path.join(RAW, "ports", "major_mar2026.pdf"), "-"], capture_output=True, text=True).stdout
tot = []
for ln in txt.splitlines():
    m = re.match(r"^\s+Total\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(\d+)\s+(\d+)\s+([\d.]+)\s+(-?[\d.]+)\s*$", ln)
    if m: tot.append((int(m.group(5)), int(m.group(6))))
print("Total rows in PDF:", len(tot))
# order in PDF: SMP Kolkata, KDS, HDC (sub-docks of SMP), Paradip, Visakhapatnam, Kamarajar, Chennai, VOC, Cochin, New Mangalore, Mormugao, Mumbai, JNPA, Deendayal, grand total
order = ["SMP", "KDS", "HDC", "Paradip", "Visakhapatnam", "Kamarajar", "Chennai", "V.O.C.", "Cochin", "New Mangalore", "Mormugao", "Mumbai", "JNPA", "Deendayal", "ALL"]
assert len(tot) == len(order), tot
cargo = {k: v for k, v in zip(order, tot)}
assert cargo["ALL"][1] == 914727195, cargo["ALL"]
assert sum(cargo[k][1] for k in order if k not in ("KDS", "HDC", "ALL")) == cargo["ALL"][1]

rows = []
for key, name, q, cat, mk in PORTS:
    lat, lon, _ = wd[q]
    r = {"key": key, "name": name, "lat": round(lat, 4), "lon": round(lon, 4), "category": cat,
         "state": state_of(lat, lon), "cargo_tonnes": cargo[mk][1] if mk else None,
         "cargo_tonnes_prev": cargo[mk][0] if mk else None, "cargo_year": "2025-26" if mk else None,
         "source_ids": {"wikidata": q}}
    rows.append(r)
write("seaports", {
    "name": "Seaports of India: major ports with cargo handled FY 2025-26",
    "source_org": "Wikidata (coordinates, CC0); Ministry of Ports, Shipping and Waterways (cargo)",
    "url": "https://shipmin.gov.in/sites/default/files/Cargo%20handled%20at%20Major%20Ports%20March%202026.pdf",
    "landing_url": "https://shipmin.gov.in/division/transport-research",
    "published": "2026-04", "reference_year": "2025-26", "resolution": "point",
    "license": "Wikidata CC0; MoPSW Government of India open data (GODL)",
    "update_frequency": "monthly (cargo); one-off (port list)", "kind": "curated",
    "limitations": "The NGA World Port Index could not be downloaded (see data/meta/seaports.md), so the list of non-major ports is a hand-picked list of 23 well-known non-major ports plus Vadhavan (planned) and is not complete. The ministry publishes cargo per State Maritime Board (not per port) for non-major ports, so non-major ports have no cargo value. Kolkata includes Haldia Dock Complex and Kolkata Dock System (one major port, SMP Kolkata). Figures for 2025-26 are advance estimates.",
    "method": "Coordinates from Wikidata for hand-picked QIDs. Cargo is the April-March 2025-26 Total column of Table 1 in the MoPSW March 2026 report (parsed with pdftotext -layout). The sum of the 12 ports is checked against the grand total 914,727,195 t. State from point-in-polygon."},
    sub(cargo_tonnes=F("Cargo handled FY 2025-26", "tonnes", "count", "Overseas + coastal cargo, April 2025 - March 2026 (advance estimates)", "neutral"),
        cargo_tonnes_prev=F("Cargo handled FY 2024-25", "tonnes", "count", "Same measure for April 2024 - March 2025 (provisional)", "neutral"),
        cargo_year=F("Cargo fiscal year", None, "text", "Fiscal year of cargo_tonnes")), rows)
