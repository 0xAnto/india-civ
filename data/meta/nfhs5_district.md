# nfhs5_district

NFHS-5 (2019-21) district fact sheet indicators. Built by `pipeline/build_health.py` (fetch: `pipeline/fetch_health.py`).

## Source
Mirror of the official IIPS/MoHFW PDF fact sheets: `jvargh7/nfhs5_factsheets` (MIT licence), 705 districts, 104 indicators. Cross-check: `pratapvardhan/NFHS-5` (CC BY 4.0, 341 districts from 21 states): 34,134 of 34,422 shared values agree (99.2 percent). The differences are in a few duplicate-numbered or parse-damaged rows and were not investigated one by one.
The mirror `pratapvardhan/NFHS-5` alone is not enough: it has no Phase 2 states (UP, MP, Rajasthan, Odisha and others).

## Coverage
- Source districts: 705. Matched to districts2020.csv: 693 (98.3 percent of source). Output rows: 693 of 724 districts2020 rows (95.7 percent of districts2020 rows have data).
- Unmatched source rows (12), left out on purpose: the 11 Delhi districts (districts2020.csv has one row, "Delhi") and Maharashtra "Mumbai Suburban" (not in districts2020.csv). NFHS "Mumbai" (the island city) matches the name "Mumbai" (code 519, the only Mumbai polygon in raw/boundaries) and is kept. Caveat: if that polygon covers the suburban area too, the value describes only part of it.
- districts2020 rows with no data (31): created after NFHS-5 (Arunachal: Kamle, Lepa Rada, Lower Siang, Pakke Kessang, Shi Yomi; Gujarat: Vav-Tharad; MP: Niwari; Manipur: 7 new districts; Mizoram: Hnahthial, Khawzawl; Tamil Nadu: 5 new districts; Telangana: Mulugu, Narayanpet; West Bengal: Alipurduar, Jhargram, Kalimpong), Chandigarh and Lakshadweep (no district fact sheet), Delhi, and J&K Mirpur and Muzaffarabad (not surveyed).
- Name matching: explicit alias table `ALIAS` in `pipeline/build_health.py` (about 150 renamed or respelled districts).
- Renamed districts mapped to current names: Mewat to Nuh, Faizabad to Ayodhya, Kanshiram Nagar to Kasganj, Mahamaya Nagar to Hathras, Jyotiba Phule Nagar to Amroha, Dibang Valley to Upper Dibang Valley. These are the same area; the Dantewada match follows the districts2020.csv name.
- Districts that were split after NFHS-5 keep the parent's value on the parent name only. Boundaries of the parent changed, so the value describes the old area.

## Indicators
31 indicators chosen by NFHS fact sheet number (see `IND` in the build script). `higher_is` is set for each field. Values of "Percentage not shown; based on fewer than 25 unweighted cases" are null. Values flagged "Based on 25-49 unweighted cases" are kept.
The two blood sugar and blood pressure indicators for men and women have the same text in the mirror; the build uses the number (88/94 women, 91/97 men).

## Sources tried and not used
- http://rchiips.org/nfhs/nfhs5.shtml: HTTP 404. https://rchiips.org/nfhs/NFHS-5_FCTS/Uttar_Pradesh.pdf: no connection (TLS/connect error). The official PDFs were not read directly.
- https://data.gov.in/catalog/district-wise-nfhs-5: page loads (HTTP 200), but it was not used because no direct file link was tested. Not a failure of the data, only of this run.
