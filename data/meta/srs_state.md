# srs_state

Built by `pipeline/build_health_srs.py` from two official PDFs on censusindia.gov.in (downloaded by hand with curl into raw/health/srs/; URLs in meta.url).

- Birth rate, death rate, natural growth rate, IMR (total, rural, urban): SRS Bulletin 2024, Vol 59 No 1 (May 2026), Table 1. 36 of 36 states/UTs. For smaller States/UTs the IMR is the 3-year value 2022-24 (note in the report).
- Life expectancy at birth (total, male, female): SRS Abridged Life Tables 2020-24 (May 2026), Statement 3. Only the 21 bigger States/UTs plus Himachal Pradesh (22 rows). The other 14 are null: the report does not give them.
- Check: national totals in the PDF match the text (birth rate 18.3, death rate 6.4, IMR 24; Kerala life expectancy 75.6 and Chhattisgarh 64.7 as the extremes).
- Chandigarh rural IMR 31 (total 6) is as printed and looks unstable (small numbers).
- Other editions available (not used): Bulletins 2018-2023, Life Tables 2016-20 and 2017-21 on the same catalogue (catalog ids 45558, 44377, 47148).

## Sources tried and not used
- https://censusindia.gov.in/census.website/data/SRSStatistical and the old www.censusindia.gov.in vital_statistics paths: 404. The NADA catalogue (https://censusindia.gov.in/nada/index.php/catalog/?sk=SRS+bulletin) worked.
- SRS Statistical Report 2021 (catalog 45556) exists but was not needed; the bulletin is newer.
