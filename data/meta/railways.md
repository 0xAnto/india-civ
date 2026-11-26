# railways

Source: Natural Earth 10m railroads (public domain), `ne_10m_railroads.zip`. Build: `pipeline/build_infra_lines.py`.

Natural Earth covers India: 644 segments with a bounding box in India. After clipping to India, merge and simplify (0.01 degrees), there are 421 chains with a total of about 40,800 km (the real route length is about 68,000 km, so branch lines are missing). File size 144 KB. Categories: electrified / non_electrified_or_unknown (Natural Earth `electric` flag).

No railway station list: no reliable open list with coordinates was found in the time allowed (Wikidata has stations but no complete "junction" flag).

## Sources tried and not reached
- OSM Overpass (`overpass.kumi.systems`, `overpass-api.de`, also `maps.mail.ru` and `overpass.private.coffee`): a single query for all India returned HTTP 504; tile queries (5 degree boxes, railway=rail + usage=main) returned 504/502 repeatedly ("server at capacity") and the first tiles took minutes. The fetch script `pipeline/fetch_osm_infra.py` is kept and can be re-run later. Natural Earth was used instead, as the task allows.
