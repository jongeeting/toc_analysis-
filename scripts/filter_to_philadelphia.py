#!/usr/bin/env python3
"""
Filter regional rail stations and trolley stops to Philadelphia city limits only.
Uses City Council districts boundary as the Philadelphia boundary.
"""

import json
from pathlib import Path

BASE = Path(__file__).parent.parent
DATA_RAW = BASE / 'data' / 'raw'
DATA_PROC = BASE / 'data' / 'processed'

def point_in_philadelphia(lon, lat, districts):
    """Check if a point is within any Philadelphia district"""
    for district in districts:
        if point_in_polygon(lon, lat, district['geometry']['coordinates']):
            return True
    return False

def point_in_polygon(x, y, polygon_coords):
    """Ray casting algorithm for point-in-polygon test"""
    if not polygon_coords:
        return False

    # Handle both Polygon and MultiPolygon
    if isinstance(polygon_coords[0][0][0], list):
        # MultiPolygon
        for poly in polygon_coords:
            if point_in_polygon_single(x, y, poly[0]):
                return True
        return False
    else:
        # Single Polygon
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

# Load Philadelphia boundary (using City Council districts)
print("Loading Philadelphia city boundary...")
with open(DATA_RAW / 'city_council_districts.geojson') as f:
    districts_data = json.load(f)

print(f"✓ Loaded {len(districts_data['features'])} districts as Philadelphia boundary")

# Filter Regional Rail to Philadelphia only
print("\nFiltering Regional Rail stations to Philadelphia...")
with open(DATA_RAW / 'septa_regional_rail_stations.geojson') as f:
    rr_data = json.load(f)

rr_philly = []
rr_suburbs = []

for station in rr_data:
    lon = float(station['location_lon'])
    lat = float(station['location_lat'])

    if point_in_philadelphia(lon, lat, districts_data['features']):
        rr_philly.append(station)
    else:
        rr_suburbs.append(station)

print(f"  In Philadelphia: {len(rr_philly)} stations")
print(f"  In suburbs: {len(rr_suburbs)} stations (excluded)")

# Save Philadelphia-only RR stations
output_file = DATA_PROC / 'septa_regional_rail_philadelphia.geojson'
with open(output_file, 'w') as f:
    json.dump(rr_philly, f, indent=2)

print(f"✓ Saved Philadelphia RR stations to {output_file}")

# Verify trolley stops are in Philadelphia
print("\nVerifying trolley stops are in Philadelphia...")
with open(DATA_PROC / 'philadelphia_trolley_stops.geojson') as f:
    trolley_data = json.load(f)

trolley_in = 0
trolley_out = 0

for feature in trolley_data['features']:
    coords = feature['geometry']['coordinates']
    if point_in_philadelphia(coords[0], coords[1], districts_data['features']):
        trolley_in += 1
    else:
        trolley_out += 1

print(f"  In Philadelphia: {trolley_in} stops")
print(f"  Outside Philadelphia: {trolley_out} stops")

if trolley_out > 0:
    print("  ⚠ Warning: Some trolley stops are outside Philadelphia - should filter")
else:
    print("  ✓ All trolley stops are within Philadelphia")

# Show which RR stations are included
print(f"\nPhiladelphia Regional Rail Stations ({len(rr_philly)}):")
for station in sorted(rr_philly, key=lambda x: x['location_name']):
    print(f"  - {station['location_name']}")

print("\n✓ Filtering complete")
