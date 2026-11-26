# nfhs5_state

NFHS-5 (2019-21) state and UT indicators, Total (urban + rural) column. Built by `pipeline/build_health.py`.

- Source: `jvargh7/nfhs5_factsheets` states.csv (MIT), parsed from the official IIPS/MoHFW state fact sheets. Coverage: 36 of 36 states and UTs (Telangana, Ladakh, Lakshadweep included).
- State fact sheets number indicators differently from district fact sheets (131 vs 104). The table `STATE_NO` in the build script maps the numbers. Extra state-only fields: total fertility rate, neonatal, infant and under-five mortality (NFHS-5 survey estimates, not SRS).
- Spot check: Kerala IMR 4.4 and stunting 23.4 agree with the published fact sheet.
- Not used: the all-India row and urban/rural columns.

## Sources tried and not used
- http://rchiips.org/nfhs/nfhs5.shtml: HTTP 404. rchiips.org fact sheet PDFs: no connection. The mirror was used instead.
