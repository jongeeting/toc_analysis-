#!/usr/bin/env python3
"""
Cluster building permits near transit stations and generate development scores.
Replaces DVRPC's outdated 2007-2017 permit data with current 2020-2025 activity.
"""

import json
import csv
from pathlib import Path
from collections import defaultdict
import re
from math import radians, cos, sin, asin, sqrt

print("\n" + "="*80)
print("BUILDING PERMIT CLUSTERING ANALYSIS (2020-2025)")
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

def is_multifamily(scope_text):
    """Determine if permit is for multifamily construction based on scope"""
    if not scope_text:
        return False

    scope = scope_text.lower()

    # Exclude single family explicitly
    if re.search(r'\bsingle[\s-]family\b', scope) and not re.search(r'\btwo\b|\bthree\b|\bfour\b|\bmultiple\b', scope):
        return False

    # Strong indicators of multifamily
    multifamily_keywords = [
        'apartment', 'multi-family', 'multifamily',
        'mixed-use', 'mixed use',
        r'\btwo[\s-]family\b', r'\bthree[\s-]family\b', r'\bfour[\s-]family\b',
        'duplex', 'triplex', 'quadplex',
        'dwelling unit', 'residential unit',
        r'\d+\s*unit', r'\d+\s*dwelling',
        'condominium'
    ]

    for keyword in multifamily_keywords:
        if re.search(keyword, scope):
            return True

    # Check for patterns like "TWO (2) FAMILY" or "2 DWELLING UNITS"
    if re.search(r'\b(two|three|four|five|six|seven|eight|nine|ten|\d+)\s*\(?\d*\)?\s*(family|dwelling|residential)', scope):
        # But not if it says "single family"
        if not re.search(r'\bsingle[\s-]family\b', scope):
            return True

    # Check for multiple stories (4+ typically indicates multifamily)
    story_match = re.search(r'(\d+)\s*story', scope)
    if story_match and int(story_match.group(1)) >= 4:
        return True

    return False

def extract_unit_count(scope_text):
    """Try to extract number of dwelling units from permit scope"""
    if not scope_text:
        return 1

    scope = scope_text.lower()

    # Look for explicit unit counts like "14 residential units" or "four (4) dwelling units"
    unit_patterns = [
        r'(\d+)\s+residential\s+units?',
        r'(\d+)\s+dwelling\s+units?',
        r'(\d+)\s+units?',
        r'\((\d+)\)\s+dwelling',
        r'\((\d+)\)\s+residential',
    ]

    for pattern in unit_patterns:
        match = re.search(pattern, scope)
        if match:
            return int(match.group(1))

    # Check for family type
    if 'two family' in scope or 'two-family' in scope or 'duplex' in scope:
        return 2
    if 'three family' in scope or 'three-family' in scope or 'triplex' in scope:
        return 3
    if 'four family' in scope or 'four-family' in scope or 'quadplex' in scope:
        return 4

    # Default to 1 unit if we can't determine
    return 1

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

# Load building permits
print("\nLoading building permits (2020-2025)...")
permits = []
with open(DATA_RAW / 'philly_permits_new_construction_2020_2025.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Filter to actual building permits only (not plumbing, electrical, mechanical)
        permit_num = row['permitnumber']
        if permit_num.startswith(('PP-', 'EP-', 'MP-', 'FP-', 'SP-')):
            continue  # Skip plumbing, electrical, mechanical, fire, sprinkler permits

        if row['lng'] and row['lat']:
            try:
                permits.append({
                    'permit_number': row['permitnumber'],
                    'address': row['address'],
                    'type': row['typeofwork'],
                    'scope': row['approvedscopeofwork'],
                    'date': row['permitissuedate'],
                    'lng': float(row['lng']),
                    'lat': float(row['lat']),
                    'is_multifamily': is_multifamily(row['approvedscopeofwork'])
                })
            except (ValueError, TypeError):
                continue

print(f"✓ Loaded {len(permits)} building permits (excluding mechanical/plumbing/electrical)")

# Filter to multifamily and add unit counts
multifamily_permits = []
for p in permits:
    if p['is_multifamily']:
        p['units'] = extract_unit_count(p['scope'])
        multifamily_permits.append(p)

print(f"✓ Identified {len(multifamily_permits)} potential multifamily permits")

# Cluster permits within 0.25 miles (402 meters) of each station
print("\nClustering permits near stations (0.25 mile radius)...")
station_permits = defaultdict(list)
station_units = defaultdict(int)
buffer_meters = 402  # 0.25 miles

for station in stations:
    nearby_permits = []
    seen_addresses = set()
    total_units = 0

    for permit in multifamily_permits:
        dist = haversine(station['lng'], station['lat'],
                        permit['lng'], permit['lat'])

        if dist <= buffer_meters:
            # Deduplicate by address (multiple permits for same building)
            addr_key = permit['address'].strip().upper()
            if addr_key not in seen_addresses:
                seen_addresses.add(addr_key)
                total_units += permit['units']
                nearby_permits.append({
                    'permit': permit['permit_number'],
                    'address': permit['address'],
                    'distance_m': round(dist, 1),
                    'date': permit['date'][:10],  # Just YYYY-MM-DD
                    'units': permit['units']
                })

    station_permits[station['name']] = nearby_permits
    station_units[station['name']] = total_units

# Generate permit scores
print("\nCalculating permit density scores...")
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
print("\n" + "="*80)
print("TOP 20 STATIONS BY RECENT DEVELOPMENT ACTIVITY (2020-2025)")
print("="*80 + "\n")
print(f"{'Rank':<6} {'Station':<28} {'Dist':<6} {'Units 20-25':<12} {'Units 07-17':<12} {'Change'}")
print("-" * 85)

for i, result in enumerate(results[:20], 1):
    change_str = f"+{result['Change_from_DVRPC']}" if result['Change_from_DVRPC'] >= 0 else str(result['Change_from_DVRPC'])
    print(f"{i:<6} {result['Station'][:26]:<28} {str(result['District']):<6} "
          f"{result['Units_2020_2025']:<12} {result['DVRPC_Units_2007_2017']:<12} {change_str}")

# Show stations with biggest changes
print("\n" + "="*80)
print("BIGGEST CHANGES FROM DVRPC DATA")
print("="*80 + "\n")

# Filter to stations with meaningful DVRPC data for comparison
comparable = [r for r in results if r['DVRPC_Units_2007_2017'] > 0 or r['Permits_2020_2025'] > 0]
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

# Save nearby permits detail for top stations
print("\nGenerating detailed permit lists for top 10 stations...")
detail_output = OUTPUTS / 'top_stations_permits_detail.txt'

with open(detail_output, 'w') as f:
    for result in results[:10]:
        station_name = result['Station']
        permits_list = station_permits[station_name]

        f.write(f"\n{'='*70}\n")
        f.write(f"{station_name} ({result['Line']}) - {len(permits_list)} permits\n")
        f.write(f"{'='*70}\n\n")

        if permits_list:
            for permit in sorted(permits_list, key=lambda x: x['date'], reverse=True):
                units_str = f" ({permit['units']} units)" if permit.get('units', 1) > 1 else ""
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

print("\n" + "="*80)
print("SUMMARY STATISTICS")
print("="*80)
print(f"\nTotal multifamily units near stations (2020-2025): {total_units_2020_2025}")
print(f"Total multifamily permits near stations (2020-2025): {total_permits_2020_2025}")
print(f"Average units per permit: {total_units_2020_2025/total_permits_2020_2025:.1f}" if total_permits_2020_2025 > 0 else "")
print(f"\nTotal units from DVRPC data (2007-2017): {total_dvrpc_2007_2017}")
print(f"Change: {total_units_2020_2025 - total_dvrpc_2007_2017:+d} units")
print(f"Percent of DVRPC total: {(total_units_2020_2025/total_dvrpc_2007_2017*100):.1f}%" if total_dvrpc_2007_2017 > 0 else "")
print(f"\nStations with recent unit development (2020-2025): {stations_with_recent}/{len(results)}")
print(f"Stations with DVRPC data (2007-2017): {stations_with_dvrpc}/{len(results)}")

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80 + "\n")
