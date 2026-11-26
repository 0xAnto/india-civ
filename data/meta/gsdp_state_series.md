# gsdp_state_series

Dataset: `data/normalized/gsdp_state_series.json`. Resolution: `state_year`. 478 rows, 34 states and UTs, financial years 2011-12 to 2025-26. Kind: official.
Build: `pipeline/fetch_gsdp_series.py`, `pipeline/build_gsdp_series.py`. Raw: `raw/economy_series/mospi_nas_series/`, `raw/economy_series/rbi_dbie_hub_series/`.
The older dataset `gsdp_state` (reference year 2023-24 with a `series` field) stays unchanged.

## Source
- MoSPI eSankhyiNAS API `https://api.mospi.gov.in/api/nas/getNASData` (base year 2011-12, series Current). Indicators: 23 GSDP, 24 NSDP, 25 per-capita NSDP, 31 per-capita GSDP. Each has a current and a constant (2011-12) price value.
- RBI DBIE handbook pages `https://dbie.rbihub.in/handbook/<slug>` for NSDP and per-capita NSDP, constant and current prices. They fill Assam, Haryana and Nagaland (NSDP only). Stored in separate `*_rbi` columns.
- `year` = first calendar year of the financial year; `fy` gives the text (for example 2011-12).

## Coverage
- GSDP at constant 2011-12 prices: 30 states and UTs for 2011-12 to 2024-25. Telangana is complete from 2011-12 (back-cast by the source).
- 2025-26: 15 states only (the others are null). Flagged in `flag`.
- No GSDP in the source for: Assam, Haryana, Nagaland, Ladakh, DH (Dadra and Nagar Haveli and Daman and Diu), Lakshadweep. NSDP (constant, current) and per-capita NSDP for Assam, Haryana, Nagaland come from RBI. Nagaland NSDP 2024-25 is missing in both sources. Ladakh has only per-capita GSDP. DH and Lakshadweep have no value in any field.
- Per-capita GSDP (MoSPI): 34 units, including Ladakh, for 2011-12 to 2023-24; fewer for 2024-25 and 2025-26.

## Checks
- All state names match `states.csv`. Unmatched: none.
- NSDP is below GSDP at constant prices in every cell where both exist.
- MoSPI against RBI, NSDP at constant prices: 86 cells differ. The differences start in 2022-23 and are small (for example Andaman and Nicobar 2023-24: 7434 MoSPI, 7147 RBI). The two sources are from different releases. The per-capita values differ by rounding for 2011-12 to 2021-22. Both stay in separate columns.

## Known breaks
- Base year 2011-12. Estimates of the latest years change in later releases. The source does not state the release type.
- Telangana before 2014-15 is a back-cast of the source.
- A back-series with base 2004-05 is not included. The MoSPI API returns no data for base year 2004-05.

## Sources tried and not reached
- `https://rbidocs.rbi.org.in/rdocs/Publications/DOCs/21T_...XLSX` (RBI Handbook Table 21, GSDP): CAPTCHA page. Not bypassed.
- `https://dbie.rbihub.in/handbook/gross-state-domestic-product-state-wise-at-constant-prices` and the current-price variant: HTTP 404 (RBI hub has no GSDP page under these names).
- `https://api.mospi.gov.in/api/nas/getNASData?base_year=2004-05&...`: "No Data Found".
