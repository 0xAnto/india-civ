# industrial_clusters

Not built. No dataset written.
Reason: the official lists have no coordinates, and a reliable geocode source was not set up in the time available.
- Operational SEZ list (Ministry of Commerce): `https://sezindia.gov.in/sites/default/files/operational_SEZ/Operational%20SEZs%20in%20India%20277.pdf` (also versions 270, 276, 280): columns developer, location (place name), type. The search result confirmed this; the files were not downloaded.
- Notified SEZ list: `https://sezindia.gov.in/sites/default/files/notifed/Notified%20351.pdf` (name, location, type, state code, area).
- MSME cluster list: not searched.
Next step: download the operational list, parse the place names, and match them to Wikidata items by name and state. A city centroid would show the town, not the zone, so say so in the meta.
