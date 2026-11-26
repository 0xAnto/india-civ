# Reproducible pipeline. `make all` downloads, normalizes, grids and publishes everything.
# Needs: uv (Python 3.13 venv), poppler (pdftotext) for the PDF-based builders.
PY := ../.venv/bin/python
RUN := cd pipeline &&

.PHONY: all venv fetch normalize grid publish serve deploy clean-site

all: venv fetch normalize grid publish

venv:
	test -x .venv/bin/python || (uv venv --python 3.13 .venv && uv pip install --python .venv numpy shapely pyshp pillow tifffile imagecodecs openpyxl xlrd requests)

fetch:
	$(RUN) $(PY) fetch_rasters.py
	$(RUN) $(PY) fetch_population.py
	$(RUN) $(PY) fetch_economy.py
	$(RUN) $(PY) fetch_health.py
	$(RUN) $(PY) fetch_health_colleges.py
	$(RUN) $(PY) fetch_infra.py
	$(RUN) $(PY) fetch_osm_infra.py
	$(RUN) $(PY) fetch_resources.py
	$(RUN) $(PY) fetch_apy.py
	$(RUN) $(PY) fetch_history.py
	$(RUN) $(PY) fetch_census_series.py
	$(RUN) $(PY) fetch_gsdp_series.py

# Order matters: build_census2011_pca.py corrects build_census2011.py output;
# build_faith_sites.py adds Wikidata classes to asi_monuments.
normalize:
	$(RUN) $(PY) build_census2011.py
	$(RUN) $(PY) build_census2011_pca.py
	$(RUN) $(PY) build_cities.py
	$(RUN) $(PY) build_economy.py
	$(RUN) $(PY) build_district_gdp.py
	$(RUN) $(PY) build_health.py
	$(RUN) $(PY) build_health_srs.py
	$(RUN) $(PY) build_health_infra.py
	$(RUN) $(PY) build_health_colleges.py
	$(RUN) $(PY) build_infra_power_air.py
	$(RUN) $(PY) build_infra_ports.py
	$(RUN) $(PY) build_infra_lines.py
	$(RUN) $(PY) build_infra_univ.py
	$(RUN) $(PY) build_infra_heritage.py
	$(RUN) $(PY) build_faith_sites.py
	$(RUN) $(PY) build_crop_state.py
	$(RUN) $(PY) build_crop_district.py
	$(RUN) $(PY) build_forest_state.py
	$(RUN) $(PY) build_forest_district.py
	$(RUN) $(PY) build_minerals.py
	$(RUN) $(PY) build_renewable_state.py
	$(RUN) $(PY) build_fisheries_livestock.py
	$(RUN) $(PY) build_history.py
	$(RUN) $(PY) build_census_series.py
	$(RUN) $(PY) build_census_state_series.py
	$(RUN) $(PY) build_gsdp_series.py

grid:
	$(RUN) $(PY) common.py
	$(RUN) $(PY) grid.py
	$(RUN) $(PY) terrain.py
	$(RUN) $(PY) world.py

publish:
	$(RUN) $(PY) publish.py
	$(RUN) $(PY) strengths.py
	$(RUN) $(PY) check.py

serve:
	cd site && python3 -m http.server 8765
