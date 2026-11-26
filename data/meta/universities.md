# universities

Build: `pipeline/build_infra_univ.py` (inputs: Wikidata SPARQL pulls from `pipeline/fetch_infra.py`, NIRF 2025 HTML).

312 rows. Rows per category: IIT 23, IIM 20, NIT 28, IISER 7, IISc 1, AIIMS 20, IIIT 27, central_university 41, institute_national_importance (other) 22, ISRO 13, CSIR 24, DAE 6, DRDO 18, research_institute 5, other_nirf 57 (NIRF top 100 institutions that are in no other category).

NIRF: the 2025 Overall ranking (latest edition reachable; the 2026 page returns 404). All 100 institutions have rank and score. Ties exist (rank 27 and rank 64 have two institutions each; no rank 28 or 65). NIRF names that did not match Wikidata labels by text were matched by hand (`pipeline/nirf2025_qids.json`, checked against the NIRF state). Three institutions have no coordinate in Wikidata (KIIT, Christ University, MMMUT): they use the point of the place where they lie (`coord_precision` = locality). Wikidata has a wrong longitude for NIT Rourkela; the build script overrides it with 22.2536 N, 84.9014 E.

Not complete: IITs (23 of 23) and IISERs (7 of 7) are complete. NITs are 28 of 31, IIMs are 20 of 21, and central universities are 41 of about 54, because the Wikidata label or coordinate is missing. CSIR has 24 labs of about 37; DRDO has 18 labs. ISRO centres: 13 (Wikidata). Coordinates of DRDO and ISRO items are often the parent city point.

## Sources tried and not reached
- NIRF `nirfindia.org` returned HTTP 403 for the default curl User-Agent; a browser User-Agent works (HTML table parsed). `https://www.nirfindia.org/Rankings/2026/OverallRanking.html`: HTTP 404.
- Wikidata `wbsearchentities` returned HTTP 429 when called quickly; slowed down.
- A full transitive Wikidata query for all subclasses of university timed out (HTTP 504) and was dropped.
