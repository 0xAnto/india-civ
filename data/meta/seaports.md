# seaports

Build: `pipeline/build_infra_ports.py`. 36 rows: 12 major ports, 23 hand-picked non-major ports, 1 planned port (Vadhavan).

Cargo (FY 2025-26, April 2025 - March 2026, advance estimates, tonnes) for the 12 major ports comes from the MoPSW report "Cargo handled at Major Ports, March 2026": `https://shipmin.gov.in/sites/default/files/Cargo%20handled%20at%20Major%20Ports%20March%202026.pdf`. The 12 port values sum to the report total of 914,727,195 t (checked in the script). SMP Kolkata includes the Kolkata Dock System and Haldia Dock Complex (one port, one row). The report also shows the previous year (FY 2024-25), which is in `cargo_tonnes_prev`. Port names were kept as in the report (Deendayal = Kandla, JNPA = Nhava Sheva, Kamarajar = Ennore, VOC = Tuticorin).

Non-major ports: the ministry reports cargo per State Maritime Board / Directorate (11 bodies, 69 ports), not per port (`.../Cargo%20handled%20at%20Non-Major%20Ports%20March%202026.pdf`). So non-major ports have no cargo value. State totals (FY 2025-26, tonnes): Gujarat Maritime Board 485,247,822; Maharashtra Maritime Board 70,556,110; Andhra Pradesh 116,765,871; Odisha 52,952,277; all non-major 753,069,232.

Coordinates: Wikidata items (CC0), picked by hand.

## Sources tried and not reached
- NGA World Port Index CSV: `https://msi.nga.mil/api/publications/download?type=view&key=16920959/SFH00000/UpdatedPub150.csv` returned an HTML error page (24 KB, not CSV). `https://msi.nga.mil/api/publications/world-port-index?output=csv` returned HTTP 503. `https://pub150.nga.mil/` did not resolve (DNS). So the non-major list is not from WPI and is incomplete.
- Indian Ports Association `https://ipa.nic.in/` and `https://ipa.gov.in/`, `https://ports.gov.in/`: connection timeout / DNS failure. The MoPSW (shipmin.gov.in) report was used instead.
