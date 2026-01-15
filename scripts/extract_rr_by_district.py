#!/usr/bin/env python3
"""Extract Regional Rail rankings by district for top 4-5 per district"""

import json
from collections import defaultdict

with open('outputs/regional_rail_analysis.json', 'r') as f:
    rr_data = json.load(f)

by_district = defaultdict(list)

for station in rr_data['station_rankings']:
    district = station.get('district')
    if district:
        by_district[district].append({
            'station': station['station'],
            'units': station['units'],
            'permits': station['permits']
        })

# Print top 5 for each district
for district in sorted(by_district.keys()):
    print(f"\nDistrict {district}:")
    stations = by_district[district]
    for i, s in enumerate(stations[:5], 1):
        print(f"  {i}. {s['station']}: {s['units']} units ({s['permits']} permits)")
