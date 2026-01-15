#!/usr/bin/env python3
"""
Analyze trolley stops with permit clustering at 1/4 mile radius.
Assign council districts and rank stops.
"""

import json
import csv
import re
import math
from collections import defaultdict

def haversine(lon1, lat1, lon2, lat2):
    """Calculate distance between two points in meters"""
    R = 6371000  # Earth radius in meters
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

def point_in_polygon(lon, lat, polygon_coords):
    """Check if point is inside polygon using ray casting"""
    if polygon_coords[0][0] == polygon_coords[0][-1]:
        polygon_coords = polygon_coords[0][:-1]
    else:
        polygon_coords = polygon_coords[0]

    n = len(polygon_coords)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon_coords[i]
        xj, yj = polygon_coords[j]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside

def extract_unit_count(scope_text):
    """Extract unit count from permit scope"""
    if not scope_text:
        return 0

    scope_upper = scope_text.upper()

    # Explicit unit counts
    patterns = [
        r'(\d+)\s*(?:RESIDENTIAL\s+)?UNIT',
        r'(\d+)\s*DWELLING',
        r'(\d+)\s*STORY.*?(\d+)\s*UNIT',
    ]

    for pattern in patterns:
        match = re.search(pattern, scope_upper)
        if match:
            return int(match.group(1))

    # Count building types
    if 'TWO FAMILY' in scope_upper or 'DUPLEX' in scope_upper:
        return 2
    if 'THREE FAMILY' in scope_upper or 'TRIPLEX' in scope_upper:
        return 3
    if 'FOUR FAMILY' in scope_upper:
        return 4

    # Default multifamily assumption
    return 10

def get_council_district(lon, lat, districts):
    """Assign council district to stop"""
    for district in districts:
        if point_in_polygon(lon, lat, district['geometry']['coordinates']):
            return district['properties']['DISTRICT']
    return None

# Load trolley stops
print("Loading trolley stops...")
with open('data/processed/philadelphia_trolley_stops.geojson', 'r') as f:
    trolley_data = json.load(f)

trolley_stops = []
for feature in trolley_data['features']:
    props = feature['properties']
    coords = feature['geometry']['coordinates']
    trolley_stops.append({
        'stop_id': props.get('StopId', ''),
        'stop_name': props.get('StopName', ''),
        'route': props.get('LineAbbr', ''),
        'lon': coords[0],
        'lat': coords[1]
    })

print(f"Loaded {len(trolley_stops)} trolley stops")

# Load council districts
print("Loading council districts...")
with open('data/raw/city_council_districts.geojson', 'r') as f:
    districts_geojson = json.load(f)
    districts = districts_geojson['features']

# Load permits
print("Loading permits...")

permits = []
with open('data/raw/philly_permits_ALL_newconst_2020_2025.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Filter to R-2 occupancy type (multifamily >2 units)
        occ_type = row.get('occupancytype', '')
        if 'R-2' not in occ_type:
            continue

        # Skip mechanical/plumbing/electrical permits
        permit_num = row.get('permitnumber', '')
        if permit_num.startswith(('PP-', 'EP-', 'MP-', 'FP-', 'SP-')):
            continue

        if row.get('lng') and row.get('lat'):
            try:
                lat = float(row['lat'])
                lng = float(row['lng'])
                unit_count = extract_unit_count(row.get('approvedscopeofwork', ''))

                permits.append({
                    'lat': lat,
                    'lng': lng,
                    'address': row.get('address', ''),
                    'units': unit_count,
                    'date': row.get('permitissuedate', ''),
                    'scope': row.get('approvedscopeofwork', '')
                })
            except (ValueError, TypeError):
                continue

print(f"Parsed {len(permits)} R-2 permits")

# Cluster permits around each trolley stop at 1/4 mile (402 meters)
buffer_meters = 402
stop_results = []

print("\nAnalyzing trolley stops (this may take a while - 506 stops)...")

for i, stop in enumerate(trolley_stops):
    if (i + 1) % 100 == 0:
        print(f"  Processed {i + 1}/{len(trolley_stops)} stops...")

    stop_name = stop['stop_name']
    stop_route = stop['route']
    stop_lat = stop['lat']
    stop_lon = stop['lon']

    # Assign council district
    district = get_council_district(stop_lon, stop_lat, districts)

    # Cluster permits
    stop_permits = []
    seen_addresses = set()
    total_units = 0

    for permit in permits:
        dist = haversine(stop_lon, stop_lat, permit['lng'], permit['lat'])
        if dist <= buffer_meters:
            # Deduplicate by address
            addr_key = permit['address'].strip().upper()
            if addr_key not in seen_addresses:
                seen_addresses.add(addr_key)
                stop_permits.append(permit)
                total_units += permit['units']

    # Only include stops with activity
    if total_units > 0:
        stop_results.append({
            'stop_id': stop['stop_id'],
            'stop_name': stop_name,
            'route': stop_route,
            'district': district,
            'lat': stop_lat,
            'lon': stop_lon,
            'permits': len(stop_permits),
            'units': total_units
        })

# Sort by units descending
stop_results.sort(key=lambda x: x['units'], reverse=True)

print(f"\nCompleted analysis!")
print(f"Found {len(stop_results)} trolley stops with development activity (out of {len(trolley_stops)} total)")

# Output rankings
print("\n" + "="*80)
print("TROLLEY STOP RANKINGS - 1/4 MILE RADIUS (Top 20)")
print("="*80)
print(f"\n{'Rank':<6} {'Stop Name':<40} {'Route':<8} {'District':<10} {'Permits':<10} {'Units':<10}")
print("-"*90)

for i, result in enumerate(stop_results[:20], 1):
    district = result['district'] if result['district'] else 'Unknown'
    print(f"{i:<6} {result['stop_name'][:39]:<40} {result['route']:<8} {district:<10} {result['permits']:<10} {result['units']:<10}")

# Group by district
by_district = defaultdict(list)
for result in stop_results:
    if result['district']:
        by_district[result['district']].append(result)

# Save detailed results to JSON
output_json = {
    'radius_meters': buffer_meters,
    'radius_description': '1/4 mile (402 meters)',
    'total_stops': len(trolley_stops),
    'stops_with_activity': len(stop_results),
    'total_permits_captured': sum(r['permits'] for r in stop_results),
    'total_units_captured': sum(r['units'] for r in stop_results),
    'stop_rankings': stop_results,
    'by_district': {k: v for k, v in by_district.items()}
}

with open('outputs/trolley_stops_analysis.json', 'w') as f:
    json.dump(output_json, f, indent=2)

# Save to CSV
with open('outputs/trolley_stops_rankings.csv', 'w', newline='') as f:
    fieldnames = ['Rank', 'Stop_Name', 'Route', 'District', 'Permits_2020_2025', 'Units_2020_2025', 'Latitude', 'Longitude']
    writer = csv.DictWriter(f, fieldnames=fieldnames)

    writer.writeheader()
    for i, result in enumerate(stop_results, 1):
        writer.writerow({
            'Rank': i,
            'Stop_Name': result['stop_name'],
            'Route': result['route'],
            'District': result['district'] if result['district'] else 'Unknown',
            'Permits_2020_2025': result['permits'],
            'Units_2020_2025': result['units'],
            'Latitude': round(result['lat'], 6),
            'Longitude': round(result['lon'], 6)
        })

print(f"\n\nResults saved to:")
print(f"  - outputs/trolley_stops_analysis.json (detailed)")
print(f"  - outputs/trolley_stops_rankings.csv (spreadsheet)")
print(f"\nTotal trolley stops analyzed: {len(trolley_stops)}")
print(f"Stops with development activity: {len(stop_results)}")
print(f"Total permits captured: {sum(r['permits'] for r in stop_results)}")
print(f"Total units captured: {sum(r['units'] for r in stop_results)}")
