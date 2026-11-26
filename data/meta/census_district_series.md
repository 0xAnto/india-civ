# census_district_series

Dataset: `data/normalized/census_district_series.json`. Resolution: `district2011_year`. Kind: official.
Build: `pipeline/fetch_census_series.py`, `pipeline/build_census_series.py`.

## Source
Census of India 2011, Table A-2 "Decadal variation in population since 1901". The Census publishes one file per state at district level on 2011 boundaries.
Catalog pages: `https://censusindia.gov.in/nada/index.php/catalog/43333` (India) to `/43368` (Andaman and Nicobar Islands). Catalog id = 43333 + state code.
The fetch script reads the download link on each page (xls or xlsx). Raw files: `raw/census_series/a2_xlsx/NN.xls(x)`, NN = Census state code (00 = India).
Columns used: Persons, Males, Females. The file of Andhra Pradesh holds the 10 districts of Telangana. The file of Jammu and Kashmir holds Leh and Kargil (Ladakh). The state id comes from `census2011_district.json`.

## Coverage
- 640 districts x 12 census years (1901-2011) = 7680 rows. All 640 districts of `census2011_district` match. Unmatched source rows: none.
- 421 rows have a null population: 394 are `N.A` in the source (districts without a past value, mostly Arunachal Pradesh, Mizoram, Delhi, Punjab, Manipur, Haryana, Sikkim, Nagaland, 1901-1951), and 27 are Assam 1981 (see breaks).
- Null counts by year: 1901 69, 1911 69, 1921 69, 1931 69, 1941 68, 1951 40, 1961 10, 1981 27. Years 1971, 1991, 2001, 2011 are complete.
- The column `flag` holds the reason for each null.

## Checks (district sum against the national row of Table A-2)
| Year | District sum | India row | Difference |
|---|---|---|---|
| 1951 | 359,010,091 | 361,088,090 | 2,077,999 (null districts) |
| 1971 | 548,159,652 | 548,159,652 | 0 |
| 1991 | 846,421,039 | 846,421,039 | 0 |
| 2001 | 1,028,737,436 | 1,028,737,436 | 0 |
| 2011 | 1,210,854,977 | 1,210,854,977 | 0 |

- 2011 sum equals 1,210,854,977 exactly. This equals the Census 2011 total.
- The India row for 1951 is 361,088,090 (official about 361.1 M). The India row for 2001 is 1,028,737,436 (official about 1,028.7 M). The district sums are lower in 1951 because of null districts. The state series (`census_state_series`) uses official state rows and matches both national totals exactly.
- Differences in 1901-1941, 1961 and 1981 come from null districts (and Assam 1981).

## Known breaks
- Past populations are adjusted by the Census to 2011 boundaries. The adjustment method is the Census own method. No re-check is done here.
- Assam 1981: the census was not held. The source has no district value ("---"). The state row has a value that the Census interpolated. The district rows stay null.
- Andhra Pradesh: for 1901, 1911, 1921 and 1931 the district totals differ from the state row (-21,599; -70,744; +16,456; +8,240). The Census explains this in a note: an error in Table A-2 of 1941 for Medak and Nizamabad. The district values are copied as published.
- Actual census years differ from the nominal year in some units. Column `year_actual` holds them: Goa, Daman, Diu, Dadra and Nagar Haveli (1900, 1910, 1940, 1950, 1960; Dadra and Nagar Haveli 1961 = 1962) and Puducherry, Karaikal, Mahe, Yanam (1951 = 1948).
- 1901 state male and female figures of Madhya Pradesh are estimates in the Census table. District values are not touched.
- Italic districts (formed after 2001) are normal rows here.

## Sources tried and not reached
- None failed for this dataset. Every catalog page 43333-43368 returned a file.
