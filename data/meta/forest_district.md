# forest_district: ISFR 2023 district-wise forest cover

Files: data/normalized/forest_district.json. Script: pipeline/build_forest_district.py. Resolution: district2020.

## Source
India State of Forest Report 2023, Volume 2, tables 10.x.3. https://fsi.nic.in/uploads/isfr2023/isfr_book_eng-vol-2_2023.pdf

## Coverage
- Source rows read: 742. Matched to districts2020: 688 (exact name 668, close spelling 20). Unmatched: 54.
- Sum of matched district forest cover = about 643,000 km2 of 715,343 km2 national (90 percent). The gap comes from unmatched rows and from districts in the report that are not in the reference list.
- Unmatched rows are listed in raw/forest/forest_district_unmatched.json. Main reasons: new districts (Andhra Pradesh 2022 split, Mayiladuthurai, Hanumakonda, Saitual, and others), Delhi (11 source districts, one reference row), and rows where the PDF merges two hill-district names on one line.

Unmatched (state: source names):
- Andhra Pradesh: Alluri Sitharama Raju, Anakapalli, Annamayya, Bapatla, Eluru, Kakinada, Konaseema, Nandyal, NTR, Palnadu, Parvathipuram Manyam, Sri Potti Sriramulu Nellore, Sri Sathya Sai, Tirupati
- Arunachal Pradesh: Dibang Valley, East SiangH & Siang
- Chhattisgarh: Gaurela Pendra Marwahi
- Dadra & Nagar Haveli: Dadra & Nagar Haveli, Daman, Diu
- Delhi: Central Delhi, East Delhi, New Delhi, North Delhi, North-East Delhi, North-West Delhi, Shahdara, South Delhi, South-East Delhi, South-West Delhi, West Delhi
- Himachal Pradesh: Kinnaur H Kullu, Mandi H Shimla
- Jammu and Kashmir: Anantnag H Badgam, Ganderbal H Jammu, Ramban H Reasi
- Madhya Pradesh: Khandwa (East Nimar), Nimar)
- Maharashtra: Mumbai City, Mumbai Suburban
- Meghalaya: Eastern West Khasi Hills, Ri-Bhoi H South Garo Hills, South Garo Hills H South West Garo
- Mizoram: Lunglei H Mamit, Saitual, Siaha
- Nagaland: Peren H Phek
- Rajasthan: Chittaurgarh, Dhaulpur
- Tamil Nadu: Mayiladuthurai
- Telangana: Hanumakonda, Warangal
- Uttarakhand: Dehradun H Garhwal, Garhwal
