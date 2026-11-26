# livestock_state: livestock products by state, 2023-24 (not census counts)

Files: data/normalized/livestock_state.json. Script: pipeline/build_fisheries_livestock.py.

## Content
Milk (thousand tonnes), eggs (lakh numbers), meat (thousand tonnes) and wool (thousand kg) by state for 2023-24. Source: Agricultural Statistics at a Glance 2024-25, table 2.55.
Dadra and Nagar Haveli and Daman and Diu is the sum of the two source rows (non-null values only).

## What is missing
The 20th Livestock Census (2019) state totals of animals were not found as a download. The book has only all-India totals (table 2.54: 536.76 million animals). The file name `livestock_state` holds products only.

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
