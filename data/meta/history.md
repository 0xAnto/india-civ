# history (historical timeline layer)

File: `data/normalized/history.json` (kind `historical`, about 115 KB).
Scripts: `pipeline/history_config.py` (curated selection), `pipeline/fetch_history.py`, `pipeline/build_history.py`.
Run: `.venv/bin/python -I pipeline/fetch_history.py` then `.venv/bin/python -I pipeline/build_history.py`.
This layer is separate from modern statistics. Do not join it to census or economic data.

## Content (counts)
15 eras, 51 polities, 69 capital entries, 218 places, 37 polities with an extent polygon, 4 routes.
Eras: Indus Valley Civilisation; Vedic period; Mahajanapadas; Maurya Empire; post-Maurya kingdoms; Gupta Empire;
Pallava dynasty and early Deccan kingdoms; Chola Empire with Chalukya and Rashtrakuta; Delhi Sultanate;
Vijayanagara Empire with Bahmani and Deccan sultanates; Mughal Empire; Maratha Empire; Sikh Empire;
Colonial India; Independence and modern India (key dates only: 1947, 1950, 1956).

## Sources and licences
| Source | Use | Licence |
|---|---|---|
| Wikidata (https://query.wikidata.org/sparql) | QIDs, English labels, coordinates (P625) | CC0 |
| English Wikipedia API (https://en.wikipedia.org/w/api.php) | Title to QID, redirect resolution; article URLs; dating references | CC BY-SA 4.0 (only titles and URLs are used; no text is copied) |
| aourednik/historical-basemaps (https://github.com/aourednik/historical-basemaps), `geojson/world_*.geojson` | Polity extents | GPL-3.0. Derived extents keep GPL-3.0. Licence text is in `raw/history/LICENSE-historical-basemaps.txt`. |
| Britannica and Wikipedia articles listed per era | Era dates; summaries are written by this project | Cited only |

Basemap files used: bc2000, bc1000, bc500, bc200, 100, 400, 600, 700, 800, 1000, 1100, 1300, 1500, 1530, 1700, 1783, 1815, 1880, 1960.

## Method
- Places and capitals are chosen by hand in `history_config.py`. Each one is resolved from its English Wikipedia title
  (redirects followed; disambiguation pages are rejected) to a Wikidata QID. Coordinates come from Wikidata P625.
  Capitals of the polities were checked against Wikidata P36 (for example Pataliputra, Amaravati, Agra, Fatehpur Sikri, Bidar, Penukonda).
- Dates are rounded values from the cited articles. Negative years are BCE (1 BCE = -1; no year 0). `null` means unknown.
- Extents: basemap features are matched by exact NAME, unioned, clipped to lon 60-100 and lat 5-40, simplified at 0.05 degrees,
  rounded to 2 decimals. Parts under 0.01 square degrees are dropped. Confidence is `low` if the basemap year is before 1000 CE, else `medium`.
  If the basemap has no matching polygon, `geometry` is `null` and `confidence` is `null`. No outline is drawn by hand.
- Routes: polylines through the Wikidata coordinates of documented waypoint cities. They are not surveyed paths.

## Uncertainty notes
- The basemap shows one snapshot year per file. The snapshot year differs from `peak_year` (for example Maurya: 200 BCE map, peak about 250 BCE;
  Maratha: 1783 map, peak about 1760; Chola: 1000 map, peak about 1030). Each extent note says so.
- Ancient and medieval states had no fixed borders. Border lines show the basemap author's generalisation.
- The basemap name `Satavahanihara` is spelled so in the source. The match of `Saka Kingdom` to the Western Satraps is a reading by this project.
- `Vedic Aryans` (basemap) is a culture area, not a state. It is listed as "Vedic culture area (not a state)".
- Sites linked to legend (Kurukshetra and the Mahabharata) and to tradition (Buddha sites, Bodh Gaya, Lumbini) carry that remark in `note`.
- Indus sites: dates are approximate ranges. Mehrgarh and Bhirrana start before the Indus era and are precursors.
- Basemap before 1000 CE: confidence `low` for all extents.

## Coverage report (polities without an extent, `geometry` null)
- Mahajanapadas: Anga, Vajji, Chedi, Matsya, Assaka, Kamboja (no polygon in the basemap).
- Shunga, Harsha's realm, Sikh Empire (the basemap has no Sikh polygon in 1815 or nearby years), Bahmani Sultanate
  (the 1500 map has only a tiny remnant), Bengal, Bombay and Madras Presidencies and Hyderabad State (no provincial boundaries in the basemap).
- Polities with `qid` null have no QID in the file. They are listed by name only.
- Four battles were dropped because Wikidata has no coordinates: Battle of Takkolam, Battle of Pratapgad, Battle of Chillianwala, Battle of Gujrat.
  Some other battle coordinates are those of the nearest town or site and are approximate.
- Wikidata `Q389755` (Pataliputra) and similar are used by QID where the English title is not unique.

## Sources not used / problems
- The Wikidata `wbsearchentities` API did not return JSON to curl; SPARQL and the Wikipedia API were used instead.
- The QIDs in the task list for Indus (Q11954), Vijayanagara (Q1053347), Delhi Sultanate (Q130336), Sikh Empire (Q83891) and Pallava (Q1052961)
  were wrong (they point to unrelated items). Correct QIDs used: Indus Valley Civilization Q42534, Vijayanagara Empire Q167639,
  Delhi Sultanate Q229411, Sikh Empire Q83572, Pallava dynasty Q466803. The others were verified by label.
- The Wikipedia API returned HTTP 429 on rapid calls; the fetch script waits between calls.
