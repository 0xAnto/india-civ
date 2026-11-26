# crop_district: district crop area, production, yield, 2022-23

Files: data/normalized/crop_district.json. Scripts: pipeline/fetch_apy.py, pipeline/build_crop_district.py. Resolution: district2020 (key `State|District`).

## Source
DES portal data.desagri.gov.in (public web forms, same data as the APY reports). Year 2022-23 is the latest year on the portal. Crops: rice, wheat, maize, cotton (lint, bales of 170 kg), sugarcane, and the groups cereals and millets, total pulses, total oilseeds, foodgrains.
The portal certificate chain is incomplete for Python. The fetch script uses verify=False for this public read-only data.

## Why district2020
The portal uses current district names (2022-23, after new districts). district2020 matches 700 of 737 source districts. district2011 would match fewer.

## Coverage
- Source districts: 737. Matched: 700 (exact 606, renamed by a hand table 64, close spelling 30). Unmatched: 37.
- Rows by field (non-null): rice 639, wheat 536, maize 618, pulses 675, oilseeds 686, sugarcane 481, cotton 285.
- `listed_foodgrain_prod_t` = rice + wheat + maize + total pulses. It leaves out jowar, bajra, ragi, barley, small millets. It is null when one of the four is null (for example no wheat). It is not the official foodgrain total. Rows with a value: 454.
- The fields `cereals_*` and `foodgrains_*` are the totals that the portal gives (all crops of the group).

## Quality notes
- National sums of the district values are higher than the official 2022-23 estimates: rice 148.6 Mt (official 135.8), wheat 128.2 Mt (official 110.6), foodgrains 357.8 Mt (official 330.5). District figures come from the states and differ from the national estimates. Use them for the spatial pattern, not for national totals.
- Blank values in the source are null. A crop that a district does not report is null, not zero.

## Unmatched source districts
- Andhra Pradesh: Alluri sitharama raju, Anakapalli, Annamayya, Bapatla, Eluru, Kadapa, Kakinada, Konaseema, Nandyal, Ntr, Palnadu, Parvathipuram manyam, Sri sathya sai, Tirupati
- Arunachal Pradesh: Dibang valley
- Chhattisgarh: Gaurella-pendra-marwahi, Khairgarh chhuikhadan gandai, Manendragarh chirimiri bharatpur, Mohla manpur ambagarh chouki, Sakti, Sarangarh bilaigarh
- Karnataka: Vijayanagar
- Mizoram: Saitual
- Nagaland: Chumoukedima, Noklak, Nuiland, Shamator, Tseminyu
- Punjab: Malerkotla
- Sikkim: Gangtok, Geyzing, Mangan, Namchi, Pakyong, Soreng
- Tamil Nadu: Mayiladuthurai
- Telangana: Warangal

## Sources tried that failed or were not used

| Source | URL | Result | What I tried |
|---|---|---|---|
| ICRISAT District Level Database | http://data.icrisat.org/dld/src/crops.html (also https, and /dld/) | Connection timed out after 25 s (no HTTP answer) | Three URL variants with curl. The old landing URL www.icrisat.org/district-level-database/ gives 404. |
| DES APY legacy portal | https://aps.dac.gov.in/APY/Index.htm | Connection timed out after 25 s | One curl try. The new portal data.desagri.gov.in works and is used instead. |
| Kaggle copies of district crop data | kaggle.com/datasets/arjunyadav99/... | Needs a login | Not tried. |
| data.gov.in district crop catalog | https://data.gov.in/catalog/district-wise-season-wise-crop-production-statistics | Catalog page loads; file download needs an API key or login | Not used. DES portal is the original source. |
| Handbook on Fisheries Statistics 2023 | https://dof.gov.in/sites/default/files/2024-06/Handbook.pdf | HTTP 200 but the body is a 404 page | Replaced by table 2.57 of Agricultural Statistics at a Glance 2024-25. |
| Handbook on Fisheries Statistics 2022 | https://archive.org/download/PARI.handbook-on-fisheries-statistics-2022/Handbook%20on%20Fisheries%20Statistics%202022.pdf | Returned an HTML error page (146 bytes) | One try. |
| PPAC Indian Petroleum & Natural Gas Statistics | ppac.gov.in | Annual book not found by web search. Only monthly snapshots found (national totals). | Used MoPNG Monthly Production Report instead. |
| MoPNG monthly report, guessed URLs | .../MPR-for-the--month-of-Mar,2025.pdf and 3 variants | HTTP 500 | Found the real file names on the listing page. |
| Global Energy Monitor Coal Mine Tracker | globalenergymonitor.org | Download needs a request form. Not tried. | - |
| Livestock Census 2019 state totals (20th census) | DAHD site | Not found as a download. Only the all-India total is in Agricultural Statistics at a Glance 2024-25 table 2.54. | Web search. |
