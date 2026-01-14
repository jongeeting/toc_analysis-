#!/usr/bin/env python3
"""
Comprehensive Philadelphia TOC Analysis - BSL/MFL/Trolleys
No dependencies version - uses only standard library and JSON manipulation
"""

import json
from pathlib import Path
from collections import defaultdict
from math import radians, cos, sin, asin, sqrt

print("\n" + "="*80)
print("PHILADELPHIA TRANSIT-ORIENTED COMMUNITIES ANALYSIS")
print("BSL / MFL / Trolleys - City Council Political Targeting")
print("="*80 + "\n")

# Paths
BASE = Path(__file__).parent.parent
DATA_RAW = BASE / 'data' / 'raw'
DATA_PROC = BASE / 'data' / 'processed'
OUTPUTS = BASE / 'outputs'
OUTPUTS.mkdir(exist_ok=True)

def haversine(lon1, lat1, lon2, lat2):
    """Calculate distance between two points in meters"""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    m = 6371000 * c  # Radius of earth in meters
    return m

def point_in_polygon(point, polygon):
    """Check if point is in polygon using ray casting algorithm"""
    x, y = point
    n = len(polygon)
    inside = False
    p1x, p1y = polygon[0]
    for i in range(n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside

# ============================================================================
# 1. Load DVRPC BSL/MFL Stations with TOD Scores
# ============================================================================
print("Loading DVRPC TOD scores for BSL/MFL...")
with open(DATA_PROC / 'dvrpc_bsl_mfl_trolley.geojson', 'r') as f:
    dvrpc_data = json.load(f)

dvrpc_stations = dvrpc_data['features']
print(f"  ✓ {len(dvrpc_stations)} BSL/MFL stations with DVRPC TOD scores")

# ============================================================================
# 2. Load Trolley Stops
# ============================================================================
print("\nLoading Philadelphia trolley stops...")
with open(DATA_PROC / 'philadelphia_trolley_stops.geojson', 'r') as f:
    trolley_data = json.load(f)

trolley_stops = trolley_data['features']
print(f"  ✓ {len(trolley_stops)} trolley stops loaded")

# Count by route
route_names = {
    'T1': 'Route 10 (Lancaster)',
    'T2': 'Route 34 (Baltimore)',
    'T3': 'Route 13 (Chester)',
    'T4': 'Route 11 (Woodland)',
    'T5': 'Route 36 (Elmwood)',
    'G1': 'Route 15 (Girard)'
}

route_counts = defaultdict(int)
for stop in trolley_stops:
    route = stop['properties']['LineAbbr']
    route_counts[route] += 1

print("\nTrolley Stops by Route:")
for code, name in route_names.items():
    print(f"  {name:30} {route_counts[code]:3} stops")

# ============================================================================
# 3. Load City Council Districts
# ============================================================================
print("\nLoading City Council districts...")
with open(DATA_RAW / 'city_council_districts.geojson', 'r') as f:
    districts_data = json.load(f)

districts = districts_data['features']
print(f"  ✓ {len(districts)} City Council districts loaded")

# ============================================================================
# 4. Multi-Line Connectivity Analysis for BSL/MFL
# ============================================================================
print("\n" + "="*80)
print("MULTI-LINE CONNECTIVITY ANALYSIS")
print("="*80 + "\n")

print("Identifying BSL/MFL transfer stations...")

# Group stations by name to find multi-line stations
station_lines = defaultdict(set)
station_coords = {}
station_props = {}

for station in dvrpc_stations:
    name = station['properties']['Station_Na']
    line = station['properties']['LINE']
    coords = tuple(station['geometry']['coordinates'])

    station_lines[name].add(line)
    station_coords[name] = coords
    station_props[name] = station['properties']

# Find multi-line stations
multi_line_stations = {name: lines for name, lines in station_lines.items() if len(lines) > 1}

if multi_line_stations:
    print(f"\nBSL/MFL Transfer Stations ({len(multi_line_stations)} found):")
    for name, lines in sorted(multi_line_stations.items()):
        print(f"  {name:30} {len(lines)} lines: {', '.join(sorted(lines))}")
else:
    print("\nNo direct BSL/MFL transfer stations found in DVRPC data.")
    print("(Note: DVRPC may list transfer stations separately by line)")

# Check for nearby stations (within 200m) that could be transfers
print("\nChecking for nearby station pairs (potential transfers within 200m)...")
transfer_pairs = []
station_list = list(station_coords.items())

for i, (name1, coord1) in enumerate(station_list):
    for name2, coord2 in station_list[i+1:]:
        if name1 != name2:
            dist = haversine(coord1[0], coord1[1], coord2[0], coord2[1])
            if dist < 200:  # Within 200 meters
                lines1 = station_lines[name1]
                lines2 = station_lines[name2]
                if lines1 != lines2:  # Different lines
                    transfer_pairs.append((name1, name2, dist, lines1, lines2))

if transfer_pairs:
    print(f"\nNearby Station Pairs (Potential Transfers): {len(transfer_pairs)}")
    for name1, name2, dist, lines1, lines2 in sorted(transfer_pairs, key=lambda x: x[2])[:10]:
        print(f"  {name1} ↔ {name2}")
        print(f"    Distance: {dist:.0f}m | Lines: {', '.join(lines1)} ↔ {', '.join(lines2)}")

# ============================================================================
# 5. Trolley Transfer Points
# ============================================================================
print("\nAnalyzing trolley transfer points...")

# Find clusters of trolley stops serving multiple routes (within 100m)
trolley_transfers = []
processed = set()

for i, stop1 in enumerate(trolley_stops):
    if i in processed:
        continue

    coord1 = stop1['geometry']['coordinates']
    route1 = stop1['properties']['LineAbbr']
    routes_here = {route1}

    # Find nearby stops
    for j, stop2 in enumerate(trolley_stops):
        if i != j and j not in processed:
            coord2 = stop2['geometry']['coordinates']
            dist = haversine(coord1[0], coord1[1], coord2[0], coord2[1])

            if dist < 100:  # Within 100m
                routes_here.add(stop2['properties']['LineAbbr'])

    if len(routes_here) > 1:
        trolley_transfers.append({
            'location': stop1['properties']['StopName'],
            'coords': coord1,
            'routes': sorted(routes_here),
            'num_routes': len(routes_here)
        })
        processed.add(i)

print(f"\nMajor Trolley Transfer Points: {len(trolley_transfers)}")
for tp in sorted(trolley_transfers, key=lambda x: x['num_routes'], reverse=True)[:20]:
    route_list = [route_names.get(r, r) for r in tp['routes']]
    print(f"  {tp['location'][:50]:50} {tp['num_routes']} routes")

# ============================================================================
# 6. Spatial Join with City Council Districts
# ============================================================================
print("\n" + "="*80)
print("CITY COUNCIL DISTRICT ANALYSIS")
print("="*80 + "\n")

print("Performing spatial joins...")

# Function to get district for a point
def get_district(lon, lat, districts):
    point = (lon, lat)
    for district in districts:
        geom = district['geometry']
        if geom['type'] == 'Polygon':
            if point_in_polygon(point, geom['coordinates'][0]):
                return district['properties']['DISTRICT']
        elif geom['type'] == 'MultiPolygon':
            for poly in geom['coordinates']:
                if point_in_polygon(point, poly[0]):
                    return district['properties']['DISTRICT']
    return None

# Assign districts to BSL/MFL stations
for station in dvrpc_stations:
    coords = station['geometry']['coordinates']
    district = get_district(coords[0], coords[1], districts)
    station['properties']['DISTRICT'] = district

# Assign districts to trolley stops
for stop in trolley_stops:
    coords = stop['geometry']['coordinates']
    district = get_district(coords[0], coords[1], districts)
    stop['properties']['DISTRICT'] = district

# Count by district
district_summary = {}
for district_feature in districts:
    district_num = district_feature['properties']['DISTRICT']

    bsl_mfl_count = sum(1 for s in dvrpc_stations if s['properties'].get('DISTRICT') == district_num)
    trolley_count = sum(1 for s in trolley_stops if s['properties'].get('DISTRICT') == district_num)

    # Count multi-line stations in this district
    multi_line_count = sum(1 for name, lines in station_lines.items()
                          if len(lines) > 1 and
                          any(s['properties']['Station_Na'] == name and
                              s['properties'].get('DISTRICT') == district_num
                              for s in dvrpc_stations))

    district_summary[district_num] = {
        'District': district_num,
        'BSL_MFL_Stations': bsl_mfl_count,
        'Trolley_Stops': trolley_count,
        'Multi_Line_Stations': multi_line_count,
        'Total': bsl_mfl_count + trolley_count
    }

print("\nSTATIONS PER CITY COUNCIL DISTRICT:\n")
print(f"{'District':<12} {'BSL/MFL':<12} {'Trolley Stops':<15} {'Multi-Line':<12} {'Total'}")
print("-" * 70)

for district_num in sorted(district_summary.keys()):
    d = district_summary[district_num]
    print(f"{d['District']:<12} {d['BSL_MFL_Stations']:<12} {d['Trolley_Stops']:<15} "
          f"{d['Multi_Line_Stations']:<12} {d['Total']}")

# Save district summary
import csv
with open(OUTPUTS / 'district_transit_summary.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['District', 'BSL_MFL_Stations', 'Trolley_Stops',
                                           'Multi_Line_Stations', 'Total'])
    writer.writeheader()
    for district_num in sorted(district_summary.keys()):
        writer.writerow(district_summary[district_num])

print(f"\n✓ Saved to {OUTPUTS / 'district_transit_summary.csv'}")

# ============================================================================
# 7. Enhanced TOD Scoring
# ============================================================================
print("\n" + "="*80)
print("ENHANCED TOD READINESS SCORING")
print("="*80 + "\n")

# Add connectivity scoring to stations
enhanced_stations = []
for name in station_coords.keys():
    props = station_props[name]
    num_lines = len(station_lines[name])

    # Connectivity bonus: +10 per additional line (max +20)
    connectivity_bonus = min((num_lines - 1) * 10, 20)

    # DVRPC combined score (0-8 scale)
    dvrpc_combined = props.get('DVRPC_Combined', props.get('ExistingOr', 0) + props.get('FuturePote', 0))

    # Enhanced score: DVRPC scaled to 80 + connectivity bonus (0-20)
    enhanced_score = (dvrpc_combined * 10) + connectivity_bonus

    enhanced_stations.append({
        'Station': name,
        'Line': ', '.join(sorted(station_lines[name])),
        'District': props.get('DISTRICT', 'N/A'),
        'Num_Lines': num_lines,
        'DVRPC_Score': dvrpc_combined,
        'Connectivity_Bonus': connectivity_bonus,
        'Enhanced_Score': enhanced_score,
        'Existing_Orientation': props.get('ExistingOr', 0),
        'Future_Potential': props.get('FuturePote', 0)
    })

# Sort by enhanced score
enhanced_stations.sort(key=lambda x: x['Enhanced_Score'], reverse=True)

print("TOP 15 STATIONS - Enhanced TOD Readiness (DVRPC + Multi-Line Connectivity):\n")
print(f"{'Rank':<6} {'Station':<30} {'District':<10} {'Lines':<7} {'Score':<8} {'DVRPC':<8} {'Bonus'}")
print("-" * 90)

for i, station in enumerate(enhanced_stations[:15], 1):
    print(f"{i:<6} {station['Station'][:28]:<30} {str(station['District']):<10} "
          f"{station['Num_Lines']:<7} {station['Enhanced_Score']:<8.1f} "
          f"{station['DVRPC_Score']:<8.2f} +{station['Connectivity_Bonus']:.0f}")

# Save enhanced scores
with open(OUTPUTS / 'top_tod_stations_enhanced.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['Station', 'Line', 'District', 'Num_Lines',
                                           'DVRPC_Score', 'Connectivity_Bonus', 'Enhanced_Score',
                                           'Existing_Orientation', 'Future_Potential'])
    writer.writeheader()
    writer.writerows(enhanced_stations)

print(f"\n✓ Saved to {OUTPUTS / 'top_tod_stations_enhanced.csv'}")

# ============================================================================
# 8. Political Summary
# ============================================================================
print("\n" + "="*80)
print("POLITICAL SUMMARY")
print("="*80 + "\n")

total_stations = len(dvrpc_stations)
total_trolley_stops = len(trolley_stops)
districts_with_bsl_mfl = sum(1 for d in district_summary.values() if d['BSL_MFL_Stations'] > 0)
districts_with_trolley = sum(1 for d in district_summary.values() if d['Trolley_Stops'] > 0)

print(f"Total BSL/MFL Stations: {total_stations}")
print(f"Total Trolley Stops: {total_trolley_stops}")
print(f"Total Transit Access Points: {total_stations + total_trolley_stops}")
print(f"\nDistricts with BSL/MFL service: {districts_with_bsl_mfl}/10")
print(f"Districts with trolley service: {districts_with_trolley}/10")
print(f"\nMulti-line stations (highest priority): {len([s for s in enhanced_stations if s['Num_Lines'] > 1])}")
print(f"High DVRPC score stations (≥6.0): {len([s for s in enhanced_stations if s['DVRPC_Score'] >= 6.0])}")

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80 + "\n")

print("Outputs saved to outputs/:")
print(f"  • district_transit_summary.csv - Stations per Council district")
print(f"  • top_tod_stations_enhanced.csv - Top TOD-ready stations with scoring")
print()
