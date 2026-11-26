# health_infra_state

Built by `pipeline/build_health_infra.py` from "Health Dynamics of India (Infrastructure & Human Resources) 2024-25" (the successor of Rural Health Statistics), MoHFW Statistics Division, status 31 March 2025. PDF: https://www.mohfw-dohfw.gov.in/static/uploads/2026/10/ad371537b4765ba9d19b44c338e099d6.pdf (raw/health/infra/mohfw1.pdf).

- 36 of 36 states/UTs. Fields: sub-centres, PHCs, CHCs (rural, urban, total); sub-divisional and district hospitals; hospitals functioning as medical colleges; standalone medical colleges; beds in those; allopathic doctors sanctioned and in position at rural PHCs.
- Checks: sums equal the printed All-India totals for sub-centres (176,021), PHCs (32,411), CHCs (6,492) and district hospital beds (163,058). The PHC doctor sum is 29,081 against 29,092 printed (Chandigarh and Delhi are not applicable; the 11 difference is not explained and may come from rounding in the source).
- Public facilities only. No per-capita rates: no population for 2025 is in the repository.
- Registered doctors (National Health Profile) are not included.

## Sources tried and not used
- National Health Profile 2022: http://cbhidghs.mohfw.gov.in/sites/default/files/2024-09/national-health-profile-2022.pdf returned an HTML page (56 KB), not the PDF. The e-National Health Profile page also gave HTML only. Registered doctors by state were therefore not built.
- Indiastat, Dataful: paywalled or login, not tried further.
