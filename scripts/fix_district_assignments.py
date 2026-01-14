#!/usr/bin/env python3
"""
Manually correct district assignments for stations on the District 1/2 boundary
along Broad Street in South Philadelphia.

The automated spatial join assigned stations incorrectly because the boundary
runs down the MIDDLE of Broad Street and station coordinates are sensitive to
which side they're geocoded on.

Correction rules based on actual longitude positions:
- EAST of Broad Street (lon > -75.169): District 1
- WEST of Broad Street (lon < -75.170): District 2
"""

import json
from pathlib import Path

BASE = Path(__file__).parent.parent
DATA_PROC = BASE / 'data' / 'processed'

print("Loading stations...")
with open(DATA_PROC / 'dvrpc_bsl_mfl_trolley.geojson', 'r') as f:
    stations_data = json.load(f)

# Manual corrections based on longitude position
corrections = {
    'Ellsworth-Federal': '1',  # -75.167 = EAST of Broad → District 1
    'Tasker-Morris': '1',      # -75.169 = EAST of Broad → District 1
    'Snyder': '1',             # -75.170 = borderline, but EAST → District 1
    'Oregon': '2',             # -75.171 = WEST of Broad → District 2
    # AT&T Station is correct at District 2 (-75.173 = WEST)
}

print("\nApplying manual corrections:")
print("="*80)

corrected = 0
for feature in stations_data['features']:
    station_name = feature['properties']['Station_Na']
    current_district = feature['properties'].get('DISTRICT', 'Unknown')

    if station_name in corrections:
        new_district = corrections[station_name]
        if current_district != new_district:
            coords = feature['geometry']['coordinates']
            print(f"{station_name:25s} | {current_district} → {new_district} | lon {coords[0]:.6f}")
            feature['properties']['DISTRICT'] = new_district
            corrected += 1

print(f"\n✓ Corrected {corrected} station assignments")

# Save corrected data
output_file = DATA_PROC / 'dvrpc_bsl_mfl_trolley.geojson'
with open(output_file, 'w') as f:
    json.dump(stations_data, f, indent=2)

print(f"✓ Saved corrected stations to {output_file}")

# Show new district totals
print("\nRecalculating development by district...")
from collections import defaultdict

with open(BASE / 'outputs' / 'stations_permit_activity_comparison.csv') as f:
    lines = f.readlines()

district_units = defaultdict(int)
for line in lines[1:]:
    parts = line.strip().split(',')
    if len(parts) >= 6:
        station_name = parts[0]
        units = int(parts[5])

        # Find corrected district
        for feature in stations_data['features']:
            if feature['properties']['Station_Na'] == station_name:
                district = feature['properties'].get('DISTRICT', 'Unknown')
                district_units[district] += units
                break

print("\nNEW DISTRICT TOTALS:")
print("="*40)
for district in sorted(district_units.keys(), key=lambda x: int(x) if x.isdigit() else 999):
    print(f"District {district}: {district_units[district]:5d} units")
