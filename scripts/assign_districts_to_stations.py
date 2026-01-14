#!/usr/bin/env python3
"""
Assign City Council districts to transit stations via spatial join.
"""

import json
from pathlib import Path
from math import radians, cos, sin, asin, sqrt

BASE = Path(__file__).parent.parent
DATA_RAW = BASE / 'data' / 'raw'
DATA_PROC = BASE / 'data' / 'processed'

def point_in_polygon(x, y, polygon_coords):
    """Ray casting algorithm for point-in-polygon test"""
    # Handle both Polygon and MultiPolygon
    if not polygon_coords:
        return False

    # If MultiPolygon, check each polygon
    if isinstance(polygon_coords[0][0][0], list):
        # This is a MultiPolygon [[[[x,y]...]]]
        for poly in polygon_coords:
            if point_in_polygon_single(x, y, poly[0]):
                return True
        return False
    else:
        # Single Polygon [[[x,y]...]]
        return point_in_polygon_single(x, y, polygon_coords[0])

def point_in_polygon_single(x, y, poly):
    """Ray casting for a single polygon ring"""
    n = len(poly)
    inside = False

    p1x, p1y = poly[0]
    for i in range(1, n + 1):
        p2x, p2y = poly[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y

    return inside

print("Loading City Council districts...")
with open(DATA_RAW / 'city_council_districts.geojson', 'r') as f:
    districts_data = json.load(f)

districts = []
for feature in districts_data['features']:
    districts.append({
        'number': feature['properties'].get('DISTRICT') or feature['properties'].get('district'),
        'geometry': feature['geometry']
    })

print(f"✓ Loaded {len(districts)} districts")

print("\nLoading BSL/MFL stations...")
with open(DATA_PROC / 'dvrpc_bsl_mfl_trolley.geojson', 'r') as f:
    stations_data = json.load(f)

print(f"✓ Loaded {len(stations_data['features'])} stations")

print("\nAssigning districts to stations...")
assigned = 0
for feature in stations_data['features']:
    coords = feature['geometry']['coordinates']
    station_name = feature['properties']['Station_Na']

    # Find which district this station is in
    for district in districts:
        if point_in_polygon(coords[0], coords[1], district['geometry']['coordinates']):
            feature['properties']['DISTRICT'] = str(district['number'])
            assigned += 1
            print(f"  {station_name:30s} -> District {district['number']}")
            break
    else:
        feature['properties']['DISTRICT'] = 'Unknown'
        print(f"  {station_name:30s} -> NOT FOUND")

print(f"\n✓ Assigned {assigned}/{len(stations_data['features'])} stations to districts")

# Save updated GeoJSON
output_file = DATA_PROC / 'dvrpc_bsl_mfl_trolley.geojson'
with open(output_file, 'w') as f:
    json.dump(stations_data, f, indent=2)

print(f"✓ Saved updated stations to {output_file}")
