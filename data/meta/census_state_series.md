# census_state_series

Dataset: `data/normalized/census_state_series.json`. Resolution: `state_year`. 36 states and UTs x 12 census years (1901-2011) = 432 rows. Kind: official.
Build: `pipeline/build_census_state_series.py` (needs `census_district_series.json` and `census2011_district.json`).

## Sources and tables
- Population, males, females, sex ratio: Census 2011 Table A-2 (2011 boundaries). State row of each state file. See `census_district_series.md`.
  - AP and TG, JK and LA: sum of A-2 district rows, only when every district has a value in that year. Both AP and TG are complete for all years.
  - DH (Dadra and Nagar Haveli and Daman and Diu): sum of the two UT rows of A-2.
  - Sex ratio = females per 1000 males (rounded) from the same rows.
- Literacy rate 1951-2001: Economic Survey 2021-22, Statistical Appendix Table 8.5 "State-wise literacy rates (1951-2011)". Source note: Registrar General of India. Raw: `raw/census_series/es_pages/page621.html` (URL `https://www.indiabudget.gov.in/economicsurvey/ebook_es2022/files/basic-html/page621.html`). A second copy (2020-21 Table 9.4, page906) is also saved but not used.
- Literacy rate 2011 and urban population and share 2011: computed from the 2011 district counts in `census2011_district.json` on present boundaries (literacy = literate / (population - age 0-6), age 7+).
- Urban share 1991 and 2001: MoSPI "Selected Socio-Economic Statistics India 2017", Table 1.7 (source: Registrar General of India). URL `https://mospi.gov.in/sites/default/files/publication_reports/SelectedSocio-EconomicStatisticsIndia2017_27oct17.pdf`, PDF page 20. The PDF text layer is garbled, so the values are read by eye from the page image and typed into `URBAN_TABLE` in the build script. The 2011 column of the same table is checked against the district sums (see checks).
- Table A-4 is not used for urban values. A-4 lists towns of 2011 with their past population. A sum of these is not the urban population of past years.

## Checks
- National sums of the state rows: 1951 = 361,088,090; 2001 = 1,028,737,436; 2011 = 1,210,854,977. All equal the India row of A-2 (official about 361.1 M, 1,028.7 M, 1,210.9 M).
- For states that have their own A-2 file, the state row equals the sum of the district rows in every year where all districts have a value: 0 mismatches.
- 2011 urban share (district sum) against the MoSPI table: equal within 0.06 points for all states except AP (29.58 against 33.36: the table includes Telangana), DH (58.51 against 46.72 and 75.17: the table lists the two UTs apart) and JK (27.48 against 27.38: the table includes Ladakh). This also supports the hand transcription.
- 2011 literacy (district derived) against Economic Survey: equal within 0.06 points except AP (67.41 against 67.0) and JK (67.0 against 67.2). Same boundary reasons.

## Definitions and breaks
- Literacy age basis is in `literacy_age_basis`: "5+" for 1951, 1961, 1971; "7+" for 1981 onward. West Bengal 1951 includes ages 0-4. Do not compare the two bases without care.
- Literacy 1951 of Chhattisgarh, Madhya Pradesh and Manipur is based on a sample (flag). Manipur 2001 excludes three sub-divisions of Senapati district (cancelled census).
- Population is on 2011 boundaries. Literacy 1951-2001 and urban share 1991-2001 are on the state boundaries of the census year as published (the Census recasts Chhattisgarh, Jharkhand, Uttarakhand). For states with a boundary change (AP, TG, JK, LA, DH) these values are left null before 2011. The published values exist for AP (with Telangana), JK (with Ladakh), Daman and Diu and Dadra and Nagar Haveli (apart) but do not match present boundaries.
- Assam 1981: the Census did not count. The state population is interpolated by the Census (flag). The Economic Survey has no literacy value for Assam 1981 (null). J&K 1991: census not held; Census values are interpolated (JK 1991 population is a district sum from A-2 and is not flagged here; the interpolation note of the Census applies).
- Puducherry 1951 slot is the census of 1948 (`year_actual` = 1948). Goa, Daman, Diu and DNH use 1900/1910/1940/1950/1960 (DNH 1962).
- Telangana (2014), Ladakh (2019) and DH (2020) are shown for all years on present boundaries. TG and LA come from district sums. DH comes from the two UT rows.

## Gaps (null cells)
- Population: Arunachal Pradesh 1901-1951 (source N.A). Sex ratio: Madhya Pradesh 1901, Puducherry 1901, 1931, 1941 (no male or female split in the source), and Arunachal Pradesh 1901-1951.
- Urban share: all states for 1901-1981 (no state table found on a usable route), and AP, TG, JK, LA, DH for 1991 and 2001. Present for 1991, 2001, 2011 for 31 states and UTs and for 2011 for all 36.
- Literacy: all states for 1901-1941. Null in 1951-2001 where the Economic Survey says na: AR 1951; AS 1981; CH 1951, 1961; DL 1951; HR 1951, 1961; HP 1951-1981; KA 1951; ML 1951; PY 1951; PB 1951, 1961; SK 1951, 1961; TN 1951; TR 1951; plus AP, TG, JK, LA, DH 1951-2001 (boundary rule). 2011 is complete for all 36.

## Sources tried and not reached
- `https://rbidocs.rbi.org.in/rdocs/Publications/PDFs/3TABLE3853D8DB4F244F00BFCFCEDA774D7030.PDF` (RBI Handbook, Table 3 state-wise urban population, historic): HTTP 200 with a CAPTCHA page. Not bypassed.
- `https://rbidocs.rbi.org.in/rdocs/Publications/PDFs/6TABLE4134B659E3B243EE9CB292D36ABC281B.PDF` (RBI Handbook, Table 6 literacy): same CAPTCHA page.
- `https://mohua.gov.in/pdf/5c80e2225a124Handbook%20of%20Urban%20Statistics%202019.pdf`: HTTP 200 but the body is an HTML page, not a PDF.
- `https://censusindia.gov.in/2011-prov-results/paper2/data_files/india/Rural_Urban_2011.pdf` and `.../Final_PPT_2011_chapter1.pdf`, `..._chapter3.pdf`: HTTP 404.
- No source with the urban share by state for 1951-1981 was reached. The WRI "State of the Cities" PDF has national values only for these years.
