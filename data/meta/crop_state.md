# crop_state: state crop production 2023-24 and irrigation share

Files: data/normalized/crop_state.json. Script: pipeline/build_crop_state.py. Resolution: state (36 rows).

## Sources
- Agricultural Statistics at a Glance 2024-25, tables 2.3(b) to 2.21(b) (area, production, yield, irrigation % for 2023-24) and tables 2.30, 2.35, 2.38 (yield, all states). https://nccd.gov.in/uploads/Agricultural_Statisitcs_at_a_Glance_2024_25_11da3cd37d.pdf
- Land Use Statistics at a Glance 2022-23, tables 1.1 and 1.2. https://desagri.gov.in/wp-content/uploads/2024/09/Final-file-of-LUS-2022-23-for-uploading.pdf
- Older editions also downloaded for checks: Agricultural Statistics at a Glance 2022, 2023, 2024 (raw/agri/).

## Coverage
- Crops: total foodgrains, rice, wheat, maize, total pulses, nine oilseeds, cotton, sugarcane.
- The source lists only the major producing states in each (b) table. For other states the area and production are null. Null does not mean zero.
- Yield for foodgrains, pulses and oilseeds exists for all states (tables 2.30, 2.35, 2.38). Field names end in `_yield_all_kgha`.
- Irrigation share = net irrigated area / net sown area x 100, for 2022-23. Rows with data: 35 of 36.
- Cotton production unit is million bales of 170 kg.
- Sum check: national totals in the PDF are not summed from the rows, because only major states appear.

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
