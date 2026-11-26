# cities

Build script: `pipeline/build_cities.py`. Fetch script: `pipeline/fetch_population.py`.

## Sources
- Population: English Wikipedia tables that cite Census of India 2011. They are fetched with the MediaWiki parse API.
  - `List of million-plus urban agglomerations in India` gives `ua_population_2011` (52 rows).
  - `List of cities in India by population` gives `city_population_2011`.
- Coordinates and QIDs: Wikidata. The Wikipedia pageprops API gives the QID. The Wikidata `wbgetentities` API gives property P625. All 112 rows use Wikidata P625. The script has fallbacks (Wikipedia coordinates API, then the Wikipedia table) that were not needed.
- Not reached: official Census UA tables (PDF/XLS) were not tried. The WDQS SPARQL endpoint was not used.

## Coverage
- 112 rows. 34 are state/UT/national capitals (36 jurisdictions: Chandigarh serves Chandigarh, Punjab and Haryana; New Delhi serves Delhi and India). 52 rows have a UA population. All 112 rows have coordinates, state, QID, `census2011_district` and `district2020`.
- Rows with no UA population are cities that are not million-plus (for example Guwahati, Bhubaneswar, Dehradun). They have `city_population_2011` where the Wikipedia city table has it.
- Capitals with no Census population in the source: Daman, Dispur (inside Guwahati UA), Gangtok, Itanagar, Kavaratti, Kohima, Leh, Panaji, Port Blair, Puducherry, Shillong. They have null population.
- Amaravati: the Wikipedia city table has 103,000. This is not a Census 2011 count, so `city_population_2011` is null.
- Mumbai, Bengaluru, Kolkata and other rows: `city_population_2011` can be the municipal city only. Jaipur, Ludhiana and some others repeat the UA value in the Wikipedia table.
- Kerala UA figures are inflated by a changed UA definition in 2011.
- Core district: the `census2011_district` of a multi-district city is one district (Delhi = Central, Mumbai = Mumbai, satellite towns of Mumbai = Thane). `district2020` uses `dt_code` of `districts2020.csv`, with fixed overrides for Delhi, Asansol, Durgapur and Vasai-Virar.
