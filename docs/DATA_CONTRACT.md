# Data contract for normalized datasets

The pipeline has these layers. Each layer reads only from the layer before it.

1. `raw/<topic>/` — downloaded source files, unchanged. Git ignores this folder.
2. `pipeline/fetch_<topic>.py` — downloads into `raw/`. It must be re-runnable.
3. `pipeline/build_<topic>.py` — parses `raw/` and writes `data/normalized/<dataset_id>.json`.
4. `pipeline/grid.py`, `pipeline/aggregate.py` — put normalized data on the hex grid.
5. `pipeline/publish.py` — writes the frontend files in `site/data/`.

Use the project virtual environment: `.venv/bin/python -I pipeline/<script>.py`.
Available packages: numpy, shapely, pyshp, pillow, tifffile, openpyxl, xlrd, requests.
Use `uv pip install --python .venv <pkg>` if you need another package.

## Normalized file format

`data/normalized/<dataset_id>.json`:

```json
{
  "meta": {
    "id": "census2011_district",
    "name": "Census of India 2011 – district Primary Census Abstract",
    "source_org": "Office of the Registrar General & Census Commissioner, India",
    "url": "https://… (the URL that the fetch script downloads)",
    "landing_url": "https://… (human page that describes the dataset)",
    "published": "2013-04-30",
    "reference_year": "2011",
    "resolution": "district2011 | district2020 | state | city | point | grid",
    "license": "…",
    "update_frequency": "decennial | annual | one-off | …",
    "kind": "official | modelled | satellite | historical | curated",
    "limitations": "…",
    "method": "What the build script does: filters, joins, unit changes, formulas.",
    "accessed": "2026-11-26",
    "redistributed_via": "optional: mirror used if the official site was not reachable"
  },
  "fields": {
    "population": {"name": "Population", "unit": "persons", "type": "count | rate | value | text",
                   "description": "…", "higher_is": "better | worse | neutral"}
  },
  "rows": [
    {"key": "…join key…", "name": "…", "state": "MH", "population": 12345, "...": null}
  ]
}
```

Rules:

- A missing value is `null`. Do not estimate, interpolate, or fill a value.
- One file has one reference year. If a source has many years, write the latest year and,
  if it is useful, a second file or a `series` field (`{"2011-12": v, …}`) with clear year keys.
- Keep source units. If you convert units, say so in `meta.method`.
- `type: count` values can be summed over areas. `type: rate` values cannot (percent, per capita, ratio).

## Join keys (`rows[].key`)

- `district2011`: the Census 2011 district code `censuscode` in `data/ref/districts2011.csv`.
- `district2020`: `"<state>|<district>"` with the exact names in `data/ref/districts2020.csv`.
  Report the source rows that you cannot match. Do not force a match.
- `state`: the two-letter `id` in `data/ref/states.csv` (aliases are in that file).
- `city`: a slug such as `mumbai`. Give `lat`, `lon`, `state`.
- `point`: a stable id from the source (or a slug). Give `lat`, `lon`, `name`, `category`, `state` if known.

Every row has `state` (two-letter id) when the state is known.

## Coverage report

Each build script prints matched / unmatched counts. Put the result and every source that you
could not get (URL, error, what you tried) in `data/meta/<dataset_id>.md`.
