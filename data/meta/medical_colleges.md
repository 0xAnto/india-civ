# medical_colleges

Built by `pipeline/fetch_health_colleges.py` and `pipeline/build_health_colleges.py`.

- List: the public JSON behind the NMC "College and Course Search" page (course M.B.B.S.): 839 colleges, 140,664 seats. The older NMC list-of-colleges page has no machine-readable file.
- Coordinates: Wikidata SPARQL only. Items of class medical school, medical college in India, or Institute of Medical Sciences, and AIIMS institutes (class Institute of National Importance). About 250 such items have coordinates.
- Match: normalised name and city token, one NMC row to one QID. 82 of 839 NMC colleges matched (9.8 percent). 757 are unmatched and not in the output; they are listed in raw/health/mc/unmatched_nmc.csv. The low rate is a Wikidata coverage limit, not a matching limit. Eight matches have a token overlap score under 2 and may be wrong; they are listed with `match_score`.
- AIIMS: the NMC list has no AIIMS. 19 AIIMS institutions come from Wikidata with coordinates and QIDs (category `aiims`, state null). Not in Wikidata with coordinates: for example AIIMS Awantipora, Rewari, Manethi.
- Output: 101 rows (82 matched NMC colleges, 19 AIIMS).
- Do not use the count of rows as a count of medical colleges in a state.

## Sources tried and not used
- https://www.nmc.org.in/information-desk/for-students-to-study-in-india/college-and-course-search/: 404 (moved).
- The page /page/information-desk-for-students-to-study-in-india-list-of-college-teaching-mbbs: no list in the HTML.
