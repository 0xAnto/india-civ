# gsva_sector_state

Reference year: 2023-24, current prices, base 2011-12. Unit: INR lakh (GSVA) and percent (shares, computed here).
Source: MoSPI NAS API, indicator 29 (Gross State Value Added), top-level industry rows (`https://api.mospi.gov.in/api/nas/getNASData`).
Eleven sectors: agriculture/forestry/fishing, mining, manufacturing, electricity and utilities, construction, trade/hotels, transport/communication, finance, real estate/professional, public administration, other services.

Coverage: 34 rows (more than gsdp_state, because the GSVA table includes Assam, Haryana and Nagaland). All 34 rows have all 11 sectors in the final file. Sector sums match the total within 0.2 percent (checked in the build).
The API also gives 2022-23 and 2024-25 (raw files saved); only 2023-24 is written.
Missing rows: Dadra and Nagar Haveli and Daman and Diu, Lakshadweep. Unmatched source names: none.
Sub-industry rows (crops, livestock, rail, road, and so on) exist in the raw data but are not used.

Sources not reached: RBI Handbook Tables 25 to 52 (GSVA by activity): CAPTCHA page, see gsdp_state.md.
The RBI DBIE page `https://dbie.rbihub.in/handbook/net-state-value-added-by-economic-activity-at-current-prices` was reachable (NSVA, net basis) and saved in `raw/economy/rbi/` for cross-checks, but not used.
