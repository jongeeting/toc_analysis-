#!/usr/bin/env python3
"""
Parse DVRPC TOD JavaScript data files and extract GeoJSON for BSL/MFL/trolley stations.
Focus on subway and trolley modes (exclude Regional Rail).
"""

import json
import re
from pathlib import Path

# Read the DVRPC TOD scores JavaScript file
data_dir = Path(__file__).parent.parent / 'data' / 'raw'
js_file = data_dir / 'dvrpc_tod_scores.js'

print("Parsing DVRPC TOD data...")

with open(js_file, 'r') as f:
    content = f.read()

# The file is a GeoJSON FeatureCollection directly (no variable assignment needed)
# Just parse it as JSON
try:
    geojson_data = json.loads(content)
    print(f"✓ Loaded {len(geojson_data['features'])} total stations from DVRPC")
except json.JSONDecodeError:
    # If there's a JavaScript variable assignment, extract the JSON part
    match = re.search(r'=\s*({.*})\s*;?$', content, re.DOTALL)
    if match:
        geojson_data = json.loads(match.group(1))
        print(f"✓ Loaded {len(geojson_data['features'])} total stations from DVRPC")
    else:
        raise ValueError("Could not parse JavaScript file")

# Filter to Subway, Subway-Elevated, and Surface Trolley only
# Exclude: Commuter Rail (Regional Rail), Light Rail (NJ RiverLine), Rapid Transit (PATCO - NJ)
subway_trolley_types = ['Subway', 'Subway-Elevated', 'Surface Trolley']

# Also include Norristown High Speed Line (it's a trolley/light rail but coded as Commuter Rail)
trolley_lines = ['Route 101 Trolley', 'Route 102 Trolley', 'Route 101 & 102 Trolley Lines',
                 'Route 11 & 13 Trolley Lines', 'Norristown High Speed Line']

filtered_features = []
for feature in geojson_data['features']:
    station_type = feature['properties'].get('TYPE', '')
    county = feature['properties'].get('COUNTY', '')
    line = feature['properties'].get('LINE', '')

    # Keep Philadelphia county stations that are:
    # 1. Subway/Subway-Elevated (BSL, MFL), OR
    # 2. Surface Trolley, OR
    # 3. Specific trolley lines even if coded differently
    is_subway_trolley = station_type in subway_trolley_types
    is_trolley_line = line in trolley_lines
    is_philly = county == 'Philadelphia'

    if is_philly and (is_subway_trolley or is_trolley_line):
        filtered_features.append(feature)

print(f"✓ Filtered to {len(filtered_features)} BSL/MFL/trolley stations in Philadelphia")

# Create new GeoJSON with filtered features
bsl_mfl_trolley_geojson = {
    'type': 'FeatureCollection',
    'features': filtered_features
}

# Save to processed data
output_file = data_dir.parent / 'processed' / 'dvrpc_bsl_mfl_trolley.geojson'
output_file.parent.mkdir(parents=True, exist_ok=True)

with open(output_file, 'w') as f:
    json.dump(bsl_mfl_trolley_geojson, f, indent=2)

print(f"✓ Saved to {output_file}")

# Summary statistics
print("\n" + "="*70)
print("DVRPC TOD SCORES - BSL/MFL/TROLLEY STATIONS")
print("="*70)

# Group by line
line_counts = {}
for feature in filtered_features:
    line = feature['properties'].get('LINE', 'Unknown')
    line_counts[line] = line_counts.get(line, 0) + 1

print("\nStations by Line:")
for line, count in sorted(line_counts.items()):
    print(f"  {line}: {count} stations")

# Show score distribution
existing_scores = [f['properties'].get('ExistingOr', 0) for f in filtered_features]
future_scores = [f['properties'].get('FuturePote', 0) for f in filtered_features]

print(f"\nDVRPC TOD Scores (1-4 scale):")
print(f"  Existing Orientation - Avg: {sum(existing_scores)/len(existing_scores):.2f}")
print(f"  Future Potential - Avg: {sum(future_scores)/len(future_scores):.2f}")

# Top 10 by combined score
for feature in filtered_features:
    existing = feature['properties'].get('ExistingOr', 0)
    future = feature['properties'].get('FuturePote', 0)
    feature['properties']['DVRPC_Combined'] = existing + future

sorted_features = sorted(filtered_features, key=lambda x: x['properties']['DVRPC_Combined'], reverse=True)

print("\nTop 10 Stations by DVRPC Combined Score:")
for i, feature in enumerate(sorted_features[:10], 1):
    props = feature['properties']
    print(f"  {i}. {props['Station_Na']:30} {props['DVRPC_Combined']:.2f} (ExO: {props['ExistingOr']:.2f}, FP: {props['FuturePote']:.2f})")

print("="*70 + "\n")
