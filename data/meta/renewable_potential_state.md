# renewable_potential_state: installed renewable capacity (31 Jan 2026) and potential by state

Files: data/normalized/renewable_potential_state.json. Script: pipeline/build_renewable_state.py. Rows: 36.

## Sources
- Installed capacity (MW): MNRE "State-wise (Location based) installed capacity of Renewable Power as on 31.01.2026". https://cdnbbsr.s3waas.gov.in/s3716e1b8c6cd17b771da77391355749f3/uploads/2026/02/202602091660392380.pdf
- Potential (MW): MNRE Renewable Energy Statistics 2024-25, table 7.1 (wind NIWE 150 m; solar NISE September 2025, ground-mounted; small hydro; biomass; bagasse; large hydro). https://cdnbbsr.s3waas.gov.in/s3716e1b8c6cd17b771da77391355749f3/uploads/2025/11/202511061627678782.pdf

## Checks
- Capacity: for each state, small hydro + wind + bio + solar + large hydro = total within 0.05 MW.
- Potential: each column sums to the table Total (wind 1,163,856 MW; solar 3,343,378 MW).
- Four bio-power numbers (Karnataka, Maharashtra, Tamil Nadu, Uttar Pradesh) and two Dadra and Nagar Haveli and Daman and Diu values wrap over two lines in the PDF. They are typed from the text layout.

## Caveats
The solar potential is a theoretical estimate from a 2025 NISE report. It is much larger than the older 748 GW figure. The Others row is dropped.

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
