#!/usr/bin/env python3
"""
Comprehensive TOD analysis including ALL transit modes:
- BSL (Broad Street Line) - 15 min peak, 20 min off-peak
- MFL (Market-Frankford Line) - 6 min peak, 15 min off-peak
- Trolleys (Routes 10, 11, 13, 15, 34, 36) - 10-15 min service
- Regional Rail - Hourly or worse (harder political sell)

Shows incremental capture for each mode to inform policy scope decisions.
"""

import json
import csv
import re
from pathlib import Path
from math import radians, cos, sin, asin, sqrt
from collections import defaultdict

print("\n" + "="*80)
print("COMPREHENSIVE TOD ANALYSIS - ALL SEPTA MODES")
print("BSL + MFL + Trolleys + Regional Rail")
print("="*80 + "\n")

BASE = Path(__file__).parent.parent
DATA_RAW = BASE / 'data' / 'raw'
DATA_PROC = BASE / 'data' / 'processed'
OUTPUTS = BASE / 'outputs'

def haversine(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return 6371000 * c

def extract_unit_count(scope_text):
    if not scope_text:
        return None
    scope = scope_text.lower()
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
            if count > 1:
                return count
    return None

# Load all transit modes
print("Loading transit stations...")

# 1. BSL/MFL (already processed)
with open(DATA_PROC / 'dvrpc_bsl_mfl_trolley.geojson') as f:
    bsl_mfl_data = json.load(f)

bsl_mfl_stations = []
for feature in bsl_mfl_data['features']:
    props = feature['properties']
    coords = feature['geometry']['coordinates']
    bsl_mfl_stations.append({
        'mode': 'BSL' if 'Broad' in props['LINE'] else 'MFL',
        'name': props['Station_Na'],
        'line': props['LINE'],
        'lng': coords[0],
        'lat': coords[1],
        'district': props.get('DISTRICT', 'Unknown')
    })

print(f"✓ BSL/MFL: {len(bsl_mfl_stations)} stations")

# 2. Trolleys
with open(DATA_PROC / 'philadelphia_trolley_stops.geojson') as f:
    trolley_data = json.load(f)

trolley_stops = []
for feature in trolley_data['features']:
    props = feature['properties']
    coords = feature['geometry']['coordinates']
    trolley_stops.append({
        'mode': 'Trolley',
        'name': props.get('StopName', 'Unnamed'),
        'line': f"Route {props.get('LineAbbr', 'Unknown')}",
        'lng': coords[0],
        'lat': coords[1]
    })

print(f"✓ Trolleys: {len(trolley_stops)} stops")

# 3. Regional Rail
try:
    with open(DATA_RAW / 'septa_regional_rail_stations.geojson') as f:
        rr_data = json.load(f)

    rr_stations = []
    for station in rr_data:
        # SEPTA API format
        if 'location_lat' in station and 'location_lon' in station:
            rr_stations.append({
                'mode': 'Regional Rail',
                'name': station.get('location_name', 'Unnamed'),
                'line': 'Regional Rail',
                'lng': float(station['location_lon']),
                'lat': float(station['location_lat'])
            })

    print(f"✓ Regional Rail: {len(rr_stations)} stations")
except Exception as e:
    print(f"! Regional Rail data error: {e}")
    rr_stations = []

# Load R-2 multifamily permits
print("\nLoading R-2 multifamily permits...")
permits = []
with open(DATA_RAW / 'philly_permits_ALL_newconst_2020_2025.csv') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if 'R-2' not in row.get('occupancytype', ''):
            continue
        if row['permitnumber'].startswith(('PP-', 'EP-', 'MP-', 'FP-', 'SP-')):
            continue
        if row['lng'] and row['lat']:
            try:
                unit_count = extract_unit_count(row['approvedscopeofwork'])
                permits.append({
                    'lng': float(row['lng']),
                    'lat': float(row['lat']),
                    'address': row['address'],
                    'units': unit_count if unit_count else 3
                })
            except (ValueError, TypeError):
                pass

print(f"✓ Loaded {len(permits)} R-2 multifamily permits")

# Analyze at 1/4 mile radius
radius_m = 402  # 1/4 mile

print("\n" + "="*80)
print("CLUSTERING PERMITS WITHIN 1/4 MILE BY MODE")
print("="*80)

def cluster_permits(stations, mode_name):
    """Cluster permits around stations, deduplicating by address"""
    total_permits = 0
    total_units = 0
    seen_addresses_global = set()  # Track across all stations to avoid double-counting

    for station in stations:
        seen_local = set()
        for permit in permits:
            dist = haversine(station['lng'], station['lat'], permit['lng'], permit['lat'])
            if dist <= radius_m:
                addr = permit['address'].strip().upper()
                if addr not in seen_local:
                    seen_local.add(addr)
                    if addr not in seen_addresses_global:
                        seen_addresses_global.add(addr)
                        total_units += permit['units']
                        total_permits += 1

    return total_permits, total_units, seen_addresses_global

# Analyze each mode
results = {}

print("\nMode-by-mode analysis (1/4 mile radius):")
print("-" * 50)

# BSL/MFL combined
bsl_permits, bsl_units, bsl_addrs = cluster_permits(bsl_mfl_stations, 'BSL/MFL')
results['BSL/MFL'] = {'permits': bsl_permits, 'units': bsl_units, 'stations': len(bsl_mfl_stations)}
print(f"BSL/MFL ({len(bsl_mfl_stations)} stations):        {bsl_permits:4d} permits, {bsl_units:6d} units")

# Trolleys (exclude permits already counted at BSL/MFL)
trolley_permits, trolley_units, trolley_addrs = cluster_permits(trolley_stops, 'Trolleys')
new_trolley_addrs = trolley_addrs - bsl_addrs
new_trolley_permits = len([a for a in new_trolley_addrs])
new_trolley_units = sum(p['units'] for p in permits if p['address'].strip().upper() in new_trolley_addrs)

results['Trolleys'] = {
    'permits': new_trolley_permits,
    'units': new_trolley_units,
    'stations': len(trolley_stops),
    'overlap_permits': trolley_permits - new_trolley_permits,
    'overlap_units': trolley_units - new_trolley_units
}
print(f"Trolleys ({len(trolley_stops)} stops):        {new_trolley_permits:4d} NEW permits, {new_trolley_units:6d} NEW units")
print(f"                              ({trolley_permits - new_trolley_permits} permits overlap with BSL/MFL)")

# Regional Rail (exclude permits already counted)
if rr_stations:
    rr_permits, rr_units, rr_addrs = cluster_permits(rr_stations, 'Regional Rail')
    all_rapid_addrs = bsl_addrs | new_trolley_addrs
    new_rr_addrs = rr_addrs - all_rapid_addrs
    new_rr_permits = len([a for a in new_rr_addrs])
    new_rr_units = sum(p['units'] for p in permits if p['address'].strip().upper() in new_rr_addrs)

    results['Regional Rail'] = {
        'permits': new_rr_permits,
        'units': new_rr_units,
        'stations': len(rr_stations),
        'overlap_permits': rr_permits - new_rr_permits,
        'overlap_units': rr_units - new_rr_units
    }
    print(f"Regional Rail ({len(rr_stations)} stations):   {new_rr_permits:4d} NEW permits, {new_rr_units:6d} NEW units")
    print(f"                              ({rr_permits - new_rr_permits} permits overlap with rapid transit/trolleys)")

# Summary
print("\n" + "="*80)
print("CUMULATIVE TOTALS BY POLICY SCOPE")
print("="*80)

cumulative_permits = bsl_permits
cumulative_units = bsl_units

print(f"\nOption 1: BSL/MFL ONLY (30 stations)")
print(f"  Captures: {cumulative_permits:4d} permits, {cumulative_units:6d} units")

cumulative_permits += new_trolley_permits
cumulative_units += new_trolley_units
print(f"\nOption 2: BSL/MFL + TROLLEYS ({len(bsl_mfl_stations) + len(trolley_stops)} stations/stops)")
print(f"  Captures: {cumulative_permits:4d} permits, {cumulative_units:6d} units")
print(f"  Gain vs BSL/MFL only: +{new_trolley_permits} permits, +{new_trolley_units} units (+{new_trolley_units/bsl_units*100:.0f}%)")

if rr_stations:
    cumulative_permits += new_rr_permits
    cumulative_units += new_rr_units
    print(f"\nOption 3: BSL/MFL + TROLLEYS + REGIONAL RAIL (all {len(bsl_mfl_stations) + len(trolley_stops) + len(rr_stations)} stations)")
    print(f"  Captures: {cumulative_permits:4d} permits, {cumulative_units:6d} units")
    print(f"  Gain vs BSL/MFL+Trolleys: +{new_rr_permits} permits, +{new_rr_units} units (+{new_rr_units/(bsl_units+new_trolley_units)*100:.0f}%)")

# Political analysis
print("\n" + "="*80)
print("POLITICAL FEASIBILITY ANALYSIS")
print("="*80)

print("\n✓ STRONG CASE (BSL/MFL + Trolleys):")
print("  - High-frequency service (6-20 min)")
print("  - 581 total stations/stops")
print(f"  - Captures {bsl_units + new_trolley_units:,} units")
print("  - Clear transit-oriented development case")

if rr_stations:
    print("\n? HARDER SELL (Adding Regional Rail):")
    print("  - Hourly or worse service frequency")
    print(f"  - Adds {len(rr_stations)} more stations")
    print(f"  - Only adds {new_rr_units:,} MORE units (+{new_rr_units/(bsl_units+new_trolley_units)*100:.0f}%)")
    print("  - Might dilute the policy or face pushback")
    print("  - Could save for Phase 2 or state bill")

# Save summary
output_file = OUTPUTS / 'all_modes_comparison.csv'
with open(output_file, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Mode', 'Stations', 'New_Permits', 'New_Units', 'Overlap_Permits', 'Overlap_Units', 'Service_Frequency'])
    writer.writerow(['BSL/MFL', results['BSL/MFL']['stations'], results['BSL/MFL']['permits'],
                     results['BSL/MFL']['units'], 0, 0, '6-20 min'])
    writer.writerow(['Trolleys', results['Trolleys']['stations'], results['Trolleys']['permits'],
                     results['Trolleys']['units'], results['Trolleys']['overlap_permits'],
                     results['Trolleys']['overlap_units'], '10-15 min'])
    if 'Regional Rail' in results:
        writer.writerow(['Regional Rail', results['Regional Rail']['stations'], results['Regional Rail']['permits'],
                         results['Regional Rail']['units'], results['Regional Rail']['overlap_permits'],
                         results['Regional Rail']['overlap_units'], 'Hourly+'])

print(f"\n✓ Saved comparison to {output_file}")

print("\n" + "="*80)
print("RECOMMENDED POLICY SCOPE")
print("="*80)

print("\nBASED ON SERVICE LEVELS & DEVELOPMENT CAPTURE:")
print(f"\n  PRIMARY: BSL + MFL + TROLLEYS")
print(f"    → {bsl_units + new_trolley_units:,} units at {len(bsl_mfl_stations) + len(trolley_stops)} high-frequency transit points")
print(f"\n  SECONDARY (optional): Add Regional Rail")
print(f"    → +{new_rr_units if rr_stations else 0:,} more units, but weaker service argument")

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80 + "\n")
