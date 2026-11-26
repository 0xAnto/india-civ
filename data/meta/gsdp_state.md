# gsdp_state

Reference year: 2023-24 (MoSPI Quick Estimates). Base year: 2011-12. Unit: INR crore (per-capita in INR).
Series: 2011-12 to 2024-25 in `series`. The 2024-25 values are Advance Estimates. The release date is not in the API.

Source: MoSPI eSankhyiki NAS API, `https://api.mospi.gov.in/api/nas/getNASData` (no key needed; limit 200 per page).
Indicators: 23 GSDP, 24 NSDP, 25 per-capita NSDP, 31 per-capita GSDP.
Build: `pipeline/fetch_economy.py`, `pipeline/build_economy.py`.

Coverage: 34 rows. GSDP, NSDP and per-capita NSDP: 30 states and UTs. Per-capita GSDP: 34 rows.
Null in the MoSPI columns: Assam, Haryana, Nagaland, Ladakh (no GSDP/NSDP in the API). Dadra and Nagar Haveli and Daman and Diu and Lakshadweep have no row.
For Assam, Haryana and Nagaland, NSDP and per-capita NSDP come from the RBI DBIE Handbook (`*_rbi` columns, 2023-24). That vintage differs a little from MoSPI (example: Andhra Pradesh per-capita NSDP 237,951 in RBI, 239,311 in MoSPI).
Unmatched source names: none.

Sources not reached:
- `https://rbidocs.rbi.org.in/rdocs/Publications/DOCs/21T_...XLSX` (RBI Handbook of Statistics on Indian States, Table 21 GSDP, and all other XLSX/PDF tables): HTTP 200 but a CAPTCHA/WAF page ("Your support ID is ..."). Not bypassed. The HTML list page `rbi.org.in/Scripts/AnnualPublications.aspx?head=Handbook of Statistics on Indian States` was reachable.
- `https://factodata.com/dataset/indian-states-dataset/state-wise-gdp-india/`: HTTP 403 (Cloudflare challenge).
- `https://dataful.in/datasets/20749/` and `19269/`: not tried (paid or login; third-party).
- `https://esankhyiki.mospi.gov.in/catalogue-main/...`: JavaScript page; the API above replaced it.
