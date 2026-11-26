# district_gdp

Only one state: Maharashtra, 2022-23 (First Revised Estimates), base 2011-12, current prices, INR crore. Resolution: district2020.
Source: Directorate of Economics and Statistics, Maharashtra, `https://mahaces.maharashtra.gov.in/files/report/DDP_2022-23_002.pdf`, Statement 49 (continued). Build: `pipeline/build_district_gdp.py`.

Coverage: 35 Maharashtra districts in `data/ref/districts2020.csv`; 33 have values. Null: Thane and Palghar (the source gives one combined value of 528,619 crore for "Thane including Palghar"; not split). Mumbai is city plus suburban, as in the reference file. Source names Chhatrapati Sambhaji Nagar and Dharashiv mapped to Aurangabad and Osmanabad.
Check: each row satisfies GDVA + taxes - subsidies = GDDP; the sum of districts plus Thane/Palghar equals the Maharashtra total (3,645,884) within rounding.

No national or all-state district product dataset exists from an official source. Other state PDFs found but NOT parsed (no time; layout differs per state):
- Arunachal Pradesh: `https://ecostatistics.arunachal.gov.in/vali_admin/images/state_publication/603118Estimate%20of%20District%20Domestic%20Product%202019-20%20to%202022-23.pdf`
- Nagaland: `http://statistics.nagaland.gov.in/storage/statistical_data/2019/530-Tak3yVrEuLTJ.pdf`
- Puducherry: `https://statistics.py.gov.in/sites/default/files/sss-district-domestic-product.pdf`
- Third-party XLSX (Dataful, paid or login, not tried): Telangana 20294, Tamil Nadu 20293, Madhya Pradesh 20287, Andhra Pradesh 20282; collection `https://dataful.in/collections/830/`.
