# airports

Source: OurAirports `airports.csv` (public domain), joined with AAI traffic statistics for FY 2025-26 (April 2025 - March 2026). Build: `pipeline/build_infra_power_air.py`.

Rows: 170 (large 43, medium 98, small 29). Kept: all large and medium airports, plus small airports with scheduled service, plus any airport that AAI lists. Heliports are excluded.

Passengers: from AAI Annexure III C (total = international + domestic passengers) in the March 2026 traffic report, `https://www.aai.aero/sites/default/files/traffic-news/Mar2k26Annex3_0.pdf`. 145 AAI airport lines parsed. Their sum is 420,089,356, which equals the AAI grand total. 144 lines are joined to an OurAirports airport. The only line not carried is KANPUR (CIVIL) with 0 passengers. The AAI to OurAirports join uses a hand-made table for names that differ (`MANUAL` in the build script). Airports not in the AAI list have `passengers` = null. These are mostly private or military-run airports.

## Sources tried and not reached
- None failed for this dataset. AAI pages need a browser User-Agent for some paths. The first fetch of `https://www.aai.aero/en/business-opportunities/traffic-news` showed no PDF links; the working page is `.../aai-traffic-news`.
