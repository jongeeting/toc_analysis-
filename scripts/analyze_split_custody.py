#!/usr/bin/env python3
"""
Analyze "split custody" boundary stations - tally permits/units on each side
of the council district boundary.
"""

import json
import csv
import math

def haversine(lon1, lat1, lon2, lat2):
    """Calculate distance between two points in meters"""
    R = 6371000
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

def point_in_polygon(lon, lat, polygon_coords):
    """Check if point is inside polygon"""
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

def get_district(lon, lat, districts):
    """Get council district for a point"""
    for district in districts:
        if point_in_polygon(lon, lat, district['geometry']['coordinates']):
            return district['properties']['DISTRICT']
    return None

def extract_unit_count(scope_text):
    """Extract unit count from permit scope"""
    import re
    if not scope_text:
        return 0

    scope_upper = scope_text.upper()

    patterns = [
        r'(\d+)\s*(?:RESIDENTIAL\s+)?UNIT',
        r'(\d+)\s*DWELLING',
    ]

    for pattern in patterns:
        match = re.search(pattern, scope_upper)
        if match:
            return int(match.group(1))

    if 'TWO FAMILY' in scope_upper or 'DUPLEX' in scope_upper:
        return 2
    if 'THREE FAMILY' in scope_upper or 'TRIPLEX' in scope_upper:
        return 3
    if 'FOUR FAMILY' in scope_upper:
        return 4

    return 10

# Load boundary stations
print("Loading boundary stations...")
with open('outputs/boundary_stations.json', 'r') as f:
    boundary_data = json.load(f)

boundary_stations = boundary_data['boundary_stations']
print(f"Found {len(boundary_stations)} boundary stations")

# Load districts
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
        occ_type = row.get('occupancytype', '')
        if 'R-2' not in occ_type:
            continue

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
                })
            except (ValueError, TypeError):
                continue

print(f"Loaded {len(permits)} R-2 permits")

# For each boundary station, split permits by district
print("\nAnalyzing split custody for boundary stations...")
buffer_meters = 402  # 1/4 mile

split_results = []

for boundary_station in boundary_stations:
    station_name = boundary_station['station']
    station_line = boundary_station['line']

    # Get station coordinates
    # Need to look up from appropriate source
    station_lon = None
    station_lat = None

    # Check BSL/MFL first
    with open('data/processed/dvrpc_bsl_mfl_trolley.geojson', 'r') as f:
        bsl_mfl_data = json.load(f)
        for feature in bsl_mfl_data['features']:
            if (feature['properties']['Station_Na'] == station_name and
                feature['properties']['LINE'] in station_line):
                station_lon = feature['geometry']['coordinates'][0]
                station_lat = feature['geometry']['coordinates'][1]
                break

    # If not found, check RR
    if station_lon is None:
        with open('data/processed/septa_regional_rail_philadelphia.geojson', 'r') as f:
            rr_data = json.load(f)
            for station in rr_data:
                if station['location_name'] == station_name:
                    station_lon = float(station['location_lon'])
                    station_lat = float(station['location_lat'])
                    break

    if station_lon is None:
        print(f"  WARNING: Could not find coordinates for {station_name}")
        continue

    # Find permits within 1/4 mile
    nearby_permits = []
    seen_addresses = set()

    for permit in permits:
        dist = haversine(station_lon, station_lat, permit['lng'], permit['lat'])
        if dist <= buffer_meters:
            addr_key = permit['address'].strip().upper()
            if addr_key not in seen_addresses:
                seen_addresses.add(addr_key)

                # Determine which district this permit is in
                permit_district = get_district(permit['lng'], permit['lat'], districts)

                nearby_permits.append({
                    'address': permit['address'],
                    'units': permit['units'],
                    'district': permit_district
                })

    # Tally by district
    by_district = {}
    for permit in nearby_permits:
        district = permit['district']
        if district:
            if district not in by_district:
                by_district[district] = {'permits': 0, 'units': 0}
            by_district[district]['permits'] += 1
            by_district[district]['units'] += permit['units']

    # Get expected districts from boundary data
    expected_districts = [d['district'] for d in boundary_station['districts']]

    split_results.append({
        'station': station_name,
        'line': station_line,
        'expected_districts': expected_districts,
        'total_permits': len(nearby_permits),
        'total_units': sum(p['units'] for p in nearby_permits),
        'by_district': by_district
    })

# Output results
print("\n" + "="*80)
print("SPLIT CUSTODY ANALYSIS - Permits/Units by District Side")
print("="*80)

for result in sorted(split_results, key=lambda x: x['total_units'], reverse=True):
    print(f"\n{result['station']} ({result['line']})")
    print(f"  Total: {result['total_permits']} permits, {result['total_units']} units")

    if result['by_district']:
        print(f"  Split by district:")
        for district in sorted(result['by_district'].keys()):
            data = result['by_district'][district]
            pct = (data['units'] / result['total_units'] * 100) if result['total_units'] > 0 else 0
            print(f"    District {district}: {data['permits']} permits, {data['units']} units ({pct:.1f}%)")
    else:
        print(f"  (No permits found within 1/4 mile)")

# Save to CSV
with open('outputs/split_custody_analysis.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow([
        'Station', 'Line', 'Expected_Districts', 'Total_Permits', 'Total_Units',
        'District_1_Permits', 'District_1_Units', 'District_1_Pct',
        'District_2_Permits', 'District_2_Units', 'District_2_Pct'
    ])

    for result in sorted(split_results, key=lambda x: x['total_units'], reverse=True):
        expected = '/'.join(result['expected_districts'])

        # Get data for each district
        districts = sorted(result['by_district'].keys()) if result['by_district'] else []

        d1_permits = d1_units = d1_pct = 0
        d2_permits = d2_units = d2_pct = 0

        if len(districts) >= 1:
            d1 = districts[0]
            d1_permits = result['by_district'][d1]['permits']
            d1_units = result['by_district'][d1]['units']
            d1_pct = (d1_units / result['total_units'] * 100) if result['total_units'] > 0 else 0

        if len(districts) >= 2:
            d2 = districts[1]
            d2_permits = result['by_district'][d2]['permits']
            d2_units = result['by_district'][d2]['units']
            d2_pct = (d2_units / result['total_units'] * 100) if result['total_units'] > 0 else 0

        writer.writerow([
            result['station'], result['line'], expected,
            result['total_permits'], result['total_units'],
            d1_permits, d1_units, f"{d1_pct:.1f}",
            d2_permits, d2_units, f"{d2_pct:.1f}"
        ])

print(f"\n\nSaved to outputs/split_custody_analysis.csv")
