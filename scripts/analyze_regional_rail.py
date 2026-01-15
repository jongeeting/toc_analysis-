#!/usr/bin/env python3
"""
Analyze Regional Rail stations with permit clustering at 1/4 mile radius.
Assign council districts and rank stations for districts with weak BSL/MFL coverage.
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
    """Assign council district to station"""
    for district in districts:
        if point_in_polygon(lon, lat, district['geometry']['coordinates']):
            return district['properties']['DISTRICT']
    return None

# Load Regional Rail stations
print("Loading Regional Rail stations...")
with open('data/processed/septa_regional_rail_philadelphia.geojson', 'r') as f:
    rr_stations = json.load(f)

print(f"Loaded {len(rr_stations)} Regional Rail stations")

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

# Cluster permits around each RR station at 1/4 mile (402 meters)
buffer_meters = 402
station_results = []

for station in rr_stations:
    station_name = station['location_name']
    station_lat = float(station['location_lat'])
    station_lon = float(station['location_lon'])

    # Assign council district
    district = get_council_district(station_lon, station_lat, districts)

    # Cluster permits
    station_permits = []
    seen_addresses = set()
    total_units = 0

    for permit in permits:
        dist = haversine(station_lon, station_lat, permit['lng'], permit['lat'])
        if dist <= buffer_meters:
            # Deduplicate by address
            addr_key = permit['address'].strip().upper()
            if addr_key not in seen_addresses:
                seen_addresses.add(addr_key)
                station_permits.append(permit)
                total_units += permit['units']

    station_results.append({
        'station': station_name,
        'district': district,
        'lat': station_lat,
        'lon': station_lon,
        'permits': len(station_permits),
        'units': total_units,
        'permit_details': station_permits[:5]  # Keep top 5 for reference
    })

# Sort by units descending
station_results.sort(key=lambda x: x['units'], reverse=True)

# Output overall rankings
print("\n" + "="*80)
print("REGIONAL RAIL STATION RANKINGS - 1/4 MILE RADIUS")
print("="*80)
print(f"\n{'Rank':<6} {'Station':<30} {'District':<10} {'Permits':<10} {'Units':<10}")
print("-"*80)

for i, result in enumerate(station_results, 1):
    district = result['district'] if result['district'] else 'Unknown'
    print(f"{i:<6} {result['station']:<30} {district:<10} {result['permits']:<10} {result['units']:<10}")

# Group by district
by_district = defaultdict(list)
for result in station_results:
    if result['district']:
        by_district[result['district']].append(result)

# Output rankings for districts 2, 4, 6, 8, 9 (weak BSL/MFL coverage)
weak_districts = ['2', '4', '6', '8', '9']

print("\n" + "="*80)
print("TOP REGIONAL RAIL STATIONS BY DISTRICT (Districts with weak BSL/MFL)")
print("="*80)

for district in sorted(weak_districts):
    if district in by_district:
        print(f"\nDistrict {district}:")
        print(f"{'Rank':<6} {'Station':<30} {'Permits':<10} {'Units':<10}")
        print("-"*70)

        for i, result in enumerate(by_district[district][:5], 1):  # Top 5 per district
            print(f"{i:<6} {result['station']:<30} {result['permits']:<10} {result['units']:<10}")
    else:
        print(f"\nDistrict {district}: No Regional Rail stations found")

# Save detailed results
output = {
    'radius_meters': buffer_meters,
    'radius_description': '1/4 mile (402 meters)',
    'total_stations': len(rr_stations),
    'total_permits_captured': sum(r['permits'] for r in station_results),
    'total_units_captured': sum(r['units'] for r in station_results),
    'station_rankings': station_results,
    'by_district': {k: v for k, v in by_district.items()}
}

with open('outputs/regional_rail_analysis.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f"\n\nDetailed results saved to outputs/regional_rail_analysis.json")
print(f"Total RR stations analyzed: {len(rr_stations)}")
print(f"Total permits captured: {sum(r['permits'] for r in station_results)}")
print(f"Total units captured: {sum(r['units'] for r in station_results)}")
