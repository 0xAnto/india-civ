# India Civ

India Civ is an interactive hex-map atlas of India in the style of a strategy game. Every value on the map comes from a public dataset. The page names the source, the year and the kind of each value.

The model for the design is https://karpathy.ai/usaciv/.

## What it shows

- **Map.** 9,197 land hexes, 20 km flat-to-flat (346 km² each). The map has terrain, relief, land cover, rivers, coasts and the boundaries of all 36 states and union territories and about 720 districts. It also shows 112 cities as banners and about 5,800 resource and facility points. Main rail lines and highways show as roads and railroads.
- **Lenses.** 75 thematic layers in 10 groups: people, prosperity, knowledge, health, land, climate, faith, hidden strengths, change over time and yields. Each lens has a legend with the direction ("higher is better" or "lower is better"), the year, the source and the kind.
- **Yields.** Food, Production, Gold, Science, Culture, Faith, Health and Infrastructure. Each yield comes from one named dataset. The Almanac explains the model for each yield.
- **Cities.** Population, a footprint (the city's hex and its 6 neighbours), the footprint yields, and specializations. A city gets a specialization when a yield per resident is at least 1.6× the median city, or when a facility rule applies.
- **Explorer.** Tables at the district (2011 and ~2020), state and city level. Scatter plots, histograms, Pearson correlation and sortable rankings. A row or a dot selects the region on the map. "Map X" shows any column as a lens.
- **Advisors.** 42 observations from nine advisors. Each observation shows its numbers and links to its source.
- **Hidden strengths.** Eight models find places that do better than their conditions predict: graduates for the wealth of a district, grain yield for its climate and crop mix, child growth for its living standards, exports for the size of a state's economy, and more. Each model shows its weights, R², sample size and years. Open it with the Strengths button or the S key.
- **Change over time.** Time lenses with a year slider and a play button: district population 1901–2011 on 2011 boundaries, state literacy 1951–2011, sex ratio 1901–2011, urbanisation 1991–2011, and real income per person 2011-12 to 2024-25. Three change lenses show growth between two years.
- **History.** A separate timeline from the Indus civilization to the Republic. Each extent shows a confidence level. The map does not show exact historical borders. "Compare with" puts a second era on top of the first. The 🏺 button puts an era's extent over any modern lens.
- **Almanac.** Methodology, the terrain rules, the yield model, every source, and the data gaps.

## Run it

The site is static. It needs no build step.

```sh
make serve            # http://localhost:8765
```

Any static host can serve the `site/` folder as it is, for example GitHub Pages, Netlify or an S3 bucket. The site loads about 10 MB of JSON, most of it only when you open a lens.

## Rebuild the data

You need `uv` and Python 3.13. Some PDF-based builders also need `pdftotext` from poppler.

```sh
make venv        # .venv with numpy, shapely, pyshp, pillow, tifffile, imagecodecs, openpyxl, xlrd, requests
make fetch       # downloads into raw/ (network; some sources are slow)
make normalize   # raw/ -> data/normalized/*.json (one file per dataset, with metadata)
make grid        # hex grid, terrain and world.json
make publish     # lenses, tables, yields, cities, advisors, SOURCES.md; then the validation check
```

`make all` runs all five steps in that order. The order in `normalize` is important: `build_census2011_pca.py` corrects the output of `build_census2011.py`, and `build_faith_sites.py` adds Wikidata classes to the ASI monuments.

Treat the files in `raw/` as untrusted input. The pipeline only parses them. It does not execute them.

## Layout

| Path | Contents |
|---|---|
| `raw/` | Downloads, unchanged (one subfolder per source) |
| `data/normalized/` | One JSON per dataset: `meta`, `fields` (type count / rate / value / text), `rows` with a join key |
| `data/meta/` | Coverage notes per dataset, and the sources that could not be reached |
| `data/ref/` | State and district reference tables with name aliases |
| `data/grid/` | Hex grid, district weights per hex, raster samples |
| `pipeline/` | Fetch, build, grid, aggregation and mechanics scripts |
| `site/` | The static site: `index.html`, `css/`, `js/`, `data/` |
| `docs/DATA_CONTRACT.md` | The normalized format and the join keys |
| `SOURCES.md` | All sources and data gaps (generated) |
| `PROGRESS.md` | Plan, decisions and status |

## Method in short

- **Projection.** Lambert conformal conic, centre 82°E 24°N, standard parallels 12.47°N and 35.17°N.
- **Boundaries.** India's official outline (Survey of India, through DataMeet). Areas that Pakistan or China administer are hatched. They have no statistics, because Indian statistics do not cover them.
- **Aggregation.** About 73 sample points per hex give the area share of each district in the hex.
  - Counts become densities with the official district area, then an area-weighted mean.
  - Rates are area-weighted means. A rate is missing when the districts with data cover less than half of the hex.
  - State values apply to all hexes of the state.
- **Vintages.** Census 2011 data joins to the 640 districts of 2011. NFHS-5 and newer data join to the ~2020 districts. The pipeline does not mix the years of one dataset.
- **Missing data.** A missing value stays missing. It shows as grey on the map and as "—" in the panels.
- **Gold check.** The Gold yield spreads state GSDP by Census 2011 non-farm workers. The check compares it with Maharashtra's official district GDP 2022-23 (33 districts): log correlation r = 0.99, median error 9%. Night lights as the weight did worse (r = 0.52).

## Validation

`make publish` ends with `pipeline/check.py`. The check stops the build when one of these conditions fails:

- Each of the 36 states and union territories, and each ~2020 district, owns at least one hex.
- The Census 2011 population total is 1,210,854,977.
- Each lens and each advisor observation points to a source record.
- No lens has a value in an area that India does not administer.
- All values are finite.
- Each city has an Indian land hex.
- All yield pips are between 0 and 4.
- Every year of every time lens passes the same tests.
- Each strength score column has a mean of 0 and a standard deviation of 1.

## Known limits

- **Railways and highways.** These are Natural Earth major corridors (about 40,800 km of rail out of about 68,000 km). The map does not use them as a density measure.
- **District crop totals.** The district totals add up to more than the national foodgrain estimate. The Almanac explains this.
- **Wikidata coverage.** Coverage of monuments and institutions differs between states. A low count can mean missing records.
- **Medical colleges.** Only 82 of 839 have coordinates.
- **Not reached.** Some sources were blocked or not available, for example the RBI handbook (CAPTCHA), OSM Overpass (timeouts) and the UNESCO tentative list. `SOURCES.md` lists each one with the error.
- **No pollution lens.** This build has no air-quality dataset. A satellite PM2.5 grid, for example the WashU/ACAG surface PM2.5 product, can supply one. Its raster can go through the same sampling as the other rasters in `terrain.py`.
