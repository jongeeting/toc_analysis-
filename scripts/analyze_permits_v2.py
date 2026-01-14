#!/usr/bin/env python3
"""
Cluster building permits near transit stations and generate development scores.
REVISED VERSION: Uses R-2 occupancy type instead of text parsing.
"""

import json
import csv
from pathlib import Path
from collections import defaultdict
import re
from math import radians, cos, sin, asin, sqrt

print("\n" + "="*80)
print("BUILDING PERMIT CLUSTERING ANALYSIS (2020-2025)")
print("Using R-2 Occupancy Type (Official Multifamily >2 Dwellings)")
print("="*80 + "\n")

# Paths
BASE = Path(__file__).parent.parent
DATA_RAW = BASE / 'data' / 'raw'
DATA_PROC = BASE / 'data' / 'processed'
OUTPUTS = BASE / 'outputs'

def haversine(lon1, lat1, lon2, lat2):
    """Calculate distance between two points in meters"""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return 6371000 * c  # meters

def extract_unit_count(scope_text):
    """Try to extract number of dwelling units from permit scope"""
    if not scope_text:
        return None

    scope = scope_text.lower()

    # Look for explicit unit counts
    unit_patterns = [
        r'(\d+)\s+residential\s+units?',
        r'(\d+)\s+dwelling\s+units?',
        r'\((\d+)\)\s+dwelling',
        r'\((\d+)\)\s+residential',
    ]

    for pattern in unit_patterns:
        match = re.search(pattern, scope)
        if match:
            count = int(match.group(1))
            if count > 1:  # Must be at least 2 units for multifamily
                return count

    return None  # Can't determine from scope

# Load BSL/MFL stations with DVRPC scores
print("Loading BSL/MFL stations with DVRPC TOD scores...")
with open(DATA_PROC / 'dvrpc_bsl_mfl_trolley.geojson', 'r') as f:
    stations_data = json.load(f)

stations = []
for feature in stations_data['features']:
    props = feature['properties']
    coords = feature['geometry']['coordinates']
    stations.append({
        'name': props['Station_Na'],
        'line': props['LINE'],
        'lng': coords[0],
        'lat': coords[1],
        'dvrpc_dev_data': props.get('Dev_Data', 0),
        'dvrpc_dev_score': props.get('Dev_Score', 0),
        'district': props.get('DISTRICT', 'N/A')
    })

print(f"✓ Loaded {len(stations)} BSL/MFL stations")

# Load building permits - filter to R-2 occupancy type
print("\nLoading R-2 multifamily permits (>2 dwellings, 2020-2025)...")
permits = []
with open(DATA_RAW / 'philly_permits_ALL_newconst_2020_2025.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # CRITICAL: Filter to R-2 occupancy type (multifamily >2 units)
        occ_type = row.get('occupancytype', '')
        if 'R-2' not in occ_type:
            continue

        # Skip mechanical/plumbing/electrical permits
        permit_num = row['permitnumber']
        if permit_num.startswith(('PP-', 'EP-', 'MP-', 'FP-', 'SP-')):
            continue

        if row['lng'] and row['lat']:
            try:
                unit_count = extract_unit_count(row['approvedscopeofwork'])
                permits.append({
                    'permit_number': row['permitnumber'],
                    'address': row['address'],
                    'type': row['typeofwork'],
                    'occupancy': row['occupancytype'],
                    'scope': row['approvedscopeofwork'],
                    'date': row['permitissuedate'],
                    'lng': float(row['lng']),
                    'lat': float(row['lat']),
                    'units': unit_count  # May be None if not extractable
                })
            except (ValueError, TypeError):
                continue

print(f"✓ Loaded {len(permits)} R-2 multifamily permits with valid locations")

# Cluster permits within 0.25 miles (402 meters) of each station
print("\nClustering permits near stations (0.25 mile radius)...")
station_permits = defaultdict(list)
station_units = defaultdict(int)
buffer_meters = 402  # 0.25 miles

for station in stations:
    nearby_permits = []
    seen_addresses = set()
    total_units = 0

    for permit in permits:
        dist = haversine(station['lng'], station['lat'],
                        permit['lng'], permit['lat'])

        if dist <= buffer_meters:
            # Deduplicate by address (multiple permits for same building)
            addr_key = permit['address'].strip().upper()
            if addr_key not in seen_addresses:
                seen_addresses.add(addr_key)

                # Estimate units if not explicitly stated
                if permit['units']:
                    units = permit['units']
                else:
                    # R-2 means >2 dwellings, assume average of 3 if not specified
                    units = 3

                total_units += units
                nearby_permits.append({
                    'permit': permit['permit_number'],
                    'address': permit['address'],
                    'distance_m': round(dist, 1),
                    'date': permit['date'][:10] if permit['date'] else '',
                    'units': units
                })

    station_permits[station['name']] = nearby_permits
    station_units[station['name']] = total_units

# Generate permit scores
print("\nCalculating development scores...")
results = []

for station in stations:
    unit_count = station_units[station['name']]
    permit_count = len(station_permits[station['name']])

    # Unit score: 0-40 points (0 units = 0, 100+ units = 40, linear scale)
    unit_score = min(40, (unit_count / 100) * 40)

    # Calculate change from DVRPC data
    dvrpc_count = station['dvrpc_dev_data']
    delta = unit_count - dvrpc_count

    results.append({
        'Station': station['name'],
        'Line': station['line'],
        'District': station['district'],
        'DVRPC_Units_2007_2017': int(dvrpc_count),
        'DVRPC_Dev_Score': station['dvrpc_dev_score'],
        'Units_2020_2025': unit_count,
        'Permits_2020_2025': permit_count,
        'Unit_Score': round(unit_score, 1),
        'Change_from_DVRPC': delta,
        'Pct_Change': round((delta / dvrpc_count * 100) if dvrpc_count > 0 else 999, 1)
    })

# Sort by recent units
results.sort(key=lambda x: x['Units_2020_2025'], reverse=True)

# Display top stations
print("\n" + "="*85)
print("TOP 20 STATIONS BY RECENT DEVELOPMENT ACTIVITY (2020-2025)")
print("="*85 + "\n")
print(f"{'Rank':<6} {'Station':<28} {'Dist':<6} {'Units 20-25':<12} {'Units 07-17':<12} {'Change'}")
print("-" * 85)

for i, result in enumerate(results[:20], 1):
    change_str = f"+{result['Change_from_DVRPC']}" if result['Change_from_DVRPC'] >= 0 else str(result['Change_from_DVRPC'])
    print(f"{i:<6} {result['Station'][:26]:<28} {str(result['District']):<6} "
          f"{result['Units_2020_2025']:<12} {result['DVRPC_Units_2007_2017']:<12} {change_str}")

# Show stations with biggest changes
print("\n" + "="*85)
print("BIGGEST CHANGES FROM DVRPC DATA")
print("="*85 + "\n")

# Filter to stations with meaningful data for comparison
comparable = [r for r in results if r['DVRPC_Units_2007_2017'] > 0 or r['Units_2020_2025'] > 0]
comparable.sort(key=lambda x: x['Change_from_DVRPC'], reverse=True)

print(f"{'Station':<28} {'Units 07-17':<12} {'Units 20-25':<12} {'Change':<10} {'%Change'}")
print("-" * 80)

for result in comparable[:15]:
    pct_str = f"{result['Pct_Change']:.0f}%" if result['Pct_Change'] < 999 else "NEW"
    change_str = f"+{result['Change_from_DVRPC']}" if result['Change_from_DVRPC'] >= 0 else str(result['Change_from_DVRPC'])
    print(f"{result['Station'][:26]:<28} {result['DVRPC_Units_2007_2017']:<12} "
          f"{result['Units_2020_2025']:<12} {change_str:<10} {pct_str}")

# Save results
output_file = OUTPUTS / 'stations_permit_activity_comparison.csv'
with open(output_file, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)

print(f"\n✓ Saved detailed results to {output_file}")

# Save nearby permits detail for top 10 stations
print("\nGenerating detailed permit lists for top 10 stations...")
detail_output = OUTPUTS / 'top_stations_permits_detail.txt'

with open(detail_output, 'w') as f:
    for result in results[:10]:
        station_name = result['Station']
        permits_list = station_permits[station_name]

        f.write(f"\n{'='*70}\n")
        f.write(f"{station_name} ({result['Line']}) - {result['Units_2020_2025']} units, {len(permits_list)} permits\n")
        f.write(f"{'='*70}\n\n")

        if permits_list:
            for permit in sorted(permits_list, key=lambda x: x['date'], reverse=True):
                units_str = f" ({permit['units']} units)" if permit.get('units', 3) > 1 else ""
                f.write(f"  {permit['date']}  |  {permit['address'][:40]:<40}  |  {permit['distance_m']}m{units_str}\n")
        else:
            f.write("  No multifamily permits found within 0.25 miles\n")

print(f"✓ Saved permit details to {detail_output}")

# Summary stats
total_units_2020_2025 = sum(r['Units_2020_2025'] for r in results)
total_permits_2020_2025 = sum(r['Permits_2020_2025'] for r in results)
total_dvrpc_2007_2017 = sum(r['DVRPC_Units_2007_2017'] for r in results)
stations_with_recent = len([r for r in results if r['Units_2020_2025'] > 0])
stations_with_dvrpc = len([r for r in results if r['DVRPC_Units_2007_2017'] > 0])

print("\n" + "="*85)
print("SUMMARY STATISTICS")
print("="*85)
print(f"\nCitywide R-2 multifamily permits (2020-2025): {len(permits)}")
print(f"\nTotal multifamily units near BSL/MFL stations (2020-2025): {total_units_2020_2025}")
print(f"Total multifamily permits near stations (2020-2025): {total_permits_2020_2025}")
print(f"Average units per permit: {total_units_2020_2025/total_permits_2020_2025:.1f}" if total_permits_2020_2025 > 0 else "")
print(f"\nTotal units from DVRPC data (2007-2017): {total_dvrpc_2007_2017}")
print(f"Change: {total_units_2020_2025 - total_dvrpc_2007_2017:+d} units")
print(f"Percent of DVRPC total: {(total_units_2020_2025/total_dvrpc_2007_2017*100):.1f}%" if total_dvrpc_2007_2017 > 0 else "")
print(f"\nStations with recent unit development (2020-2025): {stations_with_recent}/{len(results)}")
print(f"Stations with DVRPC data (2007-2017): {stations_with_dvrpc}/{len(results)}")

print("\n" + "="*85)
print("ANALYSIS COMPLETE")
print("="*85 + "\n")
