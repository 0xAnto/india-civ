# plfs_state

Reference period: calendar year 2025 (PLFS Annual Report 2025, revised file of 2026-05-29; press note 2026-03-27).
Usual status (ps+ss), age 15 and above, rural+urban. Unit: percent.
Fields: LFPR, WPR, unemployment rate (persons, male, female), urban and rural unemployment rate, worker shares by industry (agriculture A, industry B-F, manufacturing C, construction F, services G-T).
Source: `https://www.mospi.gov.in/uploads/publications_reports/publications_reports1780040415321_0624fb13-fb47-40bc-b470-7c7e9635c3ef_PLFS_2025_F_REV_29052026.pdf` (653 pages, parsed with pdftotext -layout; Appendix A Tables 16.0, 17.0, 18.0 and 27).

Coverage: 36 of 36 states and UTs. Null: rural unemployment rate for Chandigarh (no rural sample).
Eye checks against the PDF text: Andhra Pradesh LFPR 60.9, WPR 58.3; Bihar UR 3.8; Kerala UR 4.4; Lakshadweep UR 6.9. All-India row read by the build: LFPR 59.3, WPR 57.4, UR 3.1 (equals Highlights Tables 1 to 3). Industry shares sum to 100 for each state (asserted).
Caveat: PLFS design changed in January 2025; the small-state samples are small. Not comparable with the earlier July-June rounds.

Sources not reached: none. Not used: the 2023-24 annual report (superseded) and `indialabourobservatory.com` (third party). A search found no MoSPI XLSX copy of the tables.
