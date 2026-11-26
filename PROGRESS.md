# India Civ — plan and progress

This file records the plan, the decisions, and the status. Read it first when you continue the work.

## Phase 1 — reference analysis (done)

The reference, https://karpathy.ai/usaciv/, is a static site with no build step:

- `index.html` + vanilla ES modules + one Canvas 2D map. There is no map library.
- `data/world.json` holds a rectangular hex grid in projected pixels (pointy-top hexes,
  odd-row offset, radius 25 px, 117 × 90 cells) with one array per attribute: owner state,
  county, elevation, water class, relief class, land-cover class, land-cover percentages.
  Each class table has a written rule ("Hills: elevation standard deviation ≥ 85 m").
- `data/lenses.json`: each lens has id, group, unit, scale (log/linear), colour ramp,
  `higher_is`, source id, description, and one value per cell.
- `data/cities.json`: metro areas with population, jobs by sector, and yields.
  Yields are jobs by sector: Food = agriculture jobs, Production = manufacturing, Gold = GDP,
  Science = professional/scientific jobs, Culture = arts jobs.
- Banners (population pill + name + specialty icon), resource icons on tiles, wonders,
  state labels in serif caps, an Almanac ("pedia") that explains each number, a national
  yield report, search, share link/image, minimap, keyboard help.
- Visual language: dark navy chrome, gold hairlines, Palatino serif caps, parchment ink,
  terrain hexes with relief shading, rivers as polylines, foreign land faded.

## India-specific decisions

| Topic | Decision | Reason |
|---|---|---|
| Stack | Vanilla ES modules + Canvas 2D, no build step; Python data pipeline | Fast load, offline-friendly, same as reference. MapLibre is not necessary for a hex map. |
| Projection | Lambert conformal conic, lon0 82°E, lat0 24°N, standard parallels 12.47°N / 35.17°N, spherical Earth | Low distortion over all of India. |
| Hex size | Pointy-top, 20 km flat-to-flat (circumradius 11.55 km, 346 km²) | About 9,500 land hexes. Inside the 10–25 km target. |
| Hex id | `c<col>r<row>` in the LCC grid; centre lat/lon stored | Stable while the grid parameters stay the same. |
| Boundary | Survey of India outline and state map (DataMeet). Neighbours: Natural Earth admin-0, India point of view. | Indian maps must show the official boundary. |
| Disputed areas | Inside India's official outline but administered by Pakistan or China: hatched, labelled with the administering country, statistics set to missing. | Indian statistics do not cover these areas. Do not invent them. |
| Districts | Two vintages: Census 2011 (640) for Census data; ~2020 (724) for NFHS-5 and current names. | Each dataset joins to the boundaries of its own vintage. Hex aggregation reconciles them. |
| Small units | 73 sample points per hex give area fractions. A district with no sample gets its nearest hex. | Every district contributes to the data even if it is smaller than one hex. |
| Aggregation | Counts are split by area fraction; rates are area-weighted means of the districts in the hex. | No addition of unlike quantities. |

## Phases and status

- [x] Phase 1: reference analysis
- [x] Phase 2: data research. Six parallel workers covered census and cities, economy, health, infrastructure and places, agriculture and resources, and history. 36 datasets are in `data/normalized/`. Each dataset has a coverage note in `data/meta/`.
- [x] Phase 3: geographic foundation (`grid.py`, `terrain.py`, `world.py`). The grid has 9,197 land hexes, of which 333 are in areas that India does not administer.
- [x] Phase 4: data engineering. Aggregation is in `publish.py` (`Ctx.hex_values`). The site gets 59 lenses and 4 Explorer tables.
- [x] Phase 5: civilization mechanics (`mechanics.py`). This covers the 8 yields, the city footprints and specializations, 60 wonders and the advisors (`advisors.py`).
- [x] Phase 6: frontend: map, lenses, city, state and district panels, Explorer, Advisors, History, Almanac, and rail and road corridors.
- [x] Phase 7: validation (`check.py`, run by `make publish`). The fixes it found:
  - Point yields had zeros in non-administered hexes.
  - Coastal points fell into sea hexes.
  - Island cities had no hex.
  - City yields showed 0 for states with no source total.
- [~] Phase 8: deployment. The site is static and ready (`site/`, 8 MB). It is not published: publishing is an outward action that needs the owner's approval. GitHub Pages needs one step: push `site/` to a `gh-pages` branch, or serve it from `/docs`.

## Milestone 2 (done)

- Hidden strengths: `pipeline/strengths.py`, 8 models, drawer (`site/js/strengths.js`), lens group, Explorer presets, a "Strengths Scout" advisor. The immunisation model is dropped (R² 0.06). Crop rows with a rice or wheat yield above 7 t/ha are left out as source errors.
- Change over time: `pipeline/series.py`, 5 time lenses with a slider and 3 change lenses. Data: `census_district_series` (Census A-2, 1901–2011, 2011 boundaries), `census_state_series`, `gsdp_state_series`.
- History: era comparison with area and overlap statistics, and an era overlay on modern lenses.
- UI: name "India Civ", flag logo, legend moved to the lower left, top bar that never clips, a lens dock that fits narrow screens, a map fit that clears the bars.

## Open items

1. Pollution lens. Sample a satellite PM2.5 raster (WashU/ACAG V5) in `terrain.py`.
2. OSM rail and national highways. Run `fetch_osm_infra.py nh` again when Overpass has capacity. A full network can give a real transport-density lens. The Natural Earth corridors are too incomplete for density.
3. Railway stations. No open list with coordinates was found.
4. Medical college coordinates: 82 of 839 are geocoded.
5. Mobile layout. The layout works on a desktop, but small screens need a check.

## Source inventory

See `SOURCES.md` (generated by `pipeline/publish.py` from `data/normalized/*.json` meta)
and `data/meta/*.md` for coverage notes and the sources that could not be reached.
