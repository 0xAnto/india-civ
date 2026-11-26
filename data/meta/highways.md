# highways

Source: Natural Earth 10m roads (public domain). Build: `pipeline/build_infra_lines.py`.

87 chains, about 26,100 km, 49 KB. Categories: `expressway` (28 chains; Natural Earth type "Major Highway", flag expressway = 1, not verified against NHAI) and `trunk_road` (59 chains; type "Road", scalerank 3-4: the main national highway corridors). The `expressway` field is true for the first class. There are no NH numbers in Natural Earth, so `name` is null.

## Sources tried and not reached
- OSM Overpass for `highway=motorway|trunk` with `ref=NH*`: same failures as railways (HTTP 502/504 at capacity). A full tile (11 N, 73 E) is 17 MB of JSON, so the whole of India is more than 100 MB and not workable on the public servers. Partial tiles exist in `raw/infra/osm/` but were not used (an incomplete country would be misleading). Re-run `pipeline/fetch_osm_infra.py nh` later; `build_infra_lines.py` switches to OSM by itself when all tiles exist.
