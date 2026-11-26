# census2011_district and census2011_state

Build script: `pipeline/build_census2011.py`. Fetch script: `pipeline/fetch_population.py`.

## Source
- Used: GitHub mirror `nishusharma1608/India-Census-2011-Analysis`, file `india-districts-census-2011.csv`. It is the same file as Kaggle `danofer/india-census`. It is a compilation of the official Census 2011 Primary Census Abstract and houselisting tables.
- Not reached: the official Census site. `https://censusindia.gov.in` returns a redirect to `census.website` and the table files are not direct downloads. I did not try the Census Digital Library or `censuscode.gov.in`. The mirror's national total (1,210,854,977) equals the official total. The mirror values are not checked against the official files.

## Coverage
- District rows: 640 of 640 source rows match `data/ref/districts2011.csv` by censuscode (100 percent).
- The reference file has 641 rows. The one unmatched reference row is censuscode 0 ("Data Not Available"). It is a placeholder, not a district.
- 13 district names differ in spelling between the mirror and the reference (for example Mahrajganj/Maharajganj). The join uses the code only.
- State rows: 36 (all states and UTs of today). Sum of population = 1,210,854,977.
- Telangana: 10 districts of 2011 Andhra Pradesh (codes 532-541) map to TG. Ladakh: Leh and Kargil map to LA. Daman, Diu, Dadra and Nagar Haveli map to DH. Each district row has `state` (today) and `state_2011`.

## Gaps in the source
- No area, no 0-6 population, no urban population. `literacy_rate` is literate persons per 100 of the total population (all ages). It is not the official rate. Urban share is given for households only.
- Age groups are 0-29, 30-49 and 50+ only.
- The education-level counts cover a subset of persons (`edu_total`). Use `pct_graduate` only with that denominator.
- Senapati (Manipur): the worker-category counts do not sum to total workers in the source. Values are kept as they are.
- The mirror has other household columns (water, latrine, fuel, assets) that this dataset does not include.

## Optional dataset not built
- `growth` / `migration` (2001 to 2011 decadal growth): not built. No 2001 district table was fetched.
