# forest_state: ISFR 2023 forest, tree and mangrove cover by state

Files: data/normalized/forest_state.json. Script: pipeline/build_forest_state.py. Rows: 36.

## Source
India State of Forest Report 2023, Volume 1 (FSI). https://fsi.nic.in/uploads/isfr2023/isfr_book_eng-vol-1_2023.pdf
Tables used: 9.1 (forest cover 2013 and 2023), 9.7 (tree cover), 3.3 (mangrove).

## Checks
- Sum of state forest cover = 715,342.61 km2. It equals the national total in table 9.1.
- Sum of state tree cover = 112,014.34 km2. It equals the national total.
- Sum of state mangrove cover = 4,991.68 km2. It equals table 3.3 total.
- Rows that the PDF wraps over two text lines (Dadra and Nagar Haveli and Daman and Diu; Andhra Pradesh and Andaman mangrove; Manipur tree cover) are typed from the table text in the build script (`OVR`).

## Caveats
- Jammu and Kashmir and Ladakh have no separate geographical area in the report. Their percent fields are null.
- Mangrove is null for states not in table 3.3.
- Wikipedia-style secondary sources were not used.

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
