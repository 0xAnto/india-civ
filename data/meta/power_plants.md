# power_plants

Source: WRI Global Power Plant Database v1.3, `global_power_plant_database.csv` (CC BY 4.0). Build: `pipeline/build_infra_power_air.py`.

Coverage: 1589 India rows, all with coordinates, all assigned a state. Total 316,089 MW (data of about 2018-2019, so newer plants are missing). Fuel (rows): Solar 851, Coal 253, Hydro 233, Wind 108, Gas 68, Biomass 50, Oil 17, Nuclear 9. Commissioning year is present for 496 rows only (others are null). Generation columns of the source are not copied.

## Sources tried and not reached / not used
- CEA official plant list with coordinates: not found. CEA publishes capacity tables without coordinates (cea.nic.in), so it cannot replace WRI for a map. Not downloaded.
- Global Energy Monitor trackers (coal, solar, wind): the downloads are behind a request form (e-mail), so they were not used. No login-free file was found.
