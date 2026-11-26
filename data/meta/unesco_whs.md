# unesco_whs

Source: UNESCO open data portal, dataset `whc001`, `https://data.unesco.org/api/explore/v2.1/catalog/datasets/whc001/exports/csv?where=iso_codes%20like%20%22in%22`. Build: `pipeline/build_infra_heritage.py`.

45 rows: cultural 37, natural 7, mixed 1 (Khangchendzonga). Includes recent inscriptions up to 2026 (Sarnath, 2026). One site (Le Corbusier) is transboundary; only the Chandigarh component is used. 6 multi-part sites have `component_coords`. Wikidata QID is joined by the UNESCO id (P757).

## Sources tried and not reached
- `https://whc.unesco.org/en/list/xml` and `https://whc.unesco.org/en/statesparties/in/xml`: HTTP 403 (Cloudflare challenge "Just a moment...") with curl and with a browser User-Agent. The open data portal was used.
- Tentative list: not in the portal datasets (the `whc001` dataset has inscribed sites only), and the Wikidata query for the tentative list returned zero rows. The tentative list is not included.
