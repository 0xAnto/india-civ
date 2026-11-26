# asi_monuments

Source: Wikidata items with property P1371 (ASI monument ID) and coordinates. Build: `pipeline/build_infra_heritage.py`.

4484 rows (the ASI protects about 3,700 sites, but some Wikidata items are components or duplicates, so this is a count of Wikidata items and not an official count). Count per state (rows): MP 724, MH 526, GJ 502, RJ 475, UP 424, TN 356, KA 282, WB 214, DL 149, AP 145, HR 92, OR 82, BR 72, AS 69, CT 50, KL 46, PB 44, UT 43, HP 40, JK 35, GA 27, TG 19, LA 15, JH 12, DH 9, PY 7, TR 7, ML 6, NL 4, SK 3, AR 2, MZ 2, MN 1. The state of a point comes from the state polygons, so points near borders can be wrong. Use the dataset `asi_state` (other topic) for official totals.

## Sources tried and not reached
- ASI official list (asi.nic.in): not tried for scraping; the list there has no coordinates.
