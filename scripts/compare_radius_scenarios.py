#!/usr/bin/env python3
"""
Compare development capture at different radii to inform policy strategy.

Radii analyzed:
- 500 feet (152m): Current city TOD overlay distance
- 1/4 mile (402m): Mayor's proposal, easier local sell
- 1/2 mile (805m): Table preference, standard TOD, state bill coverage

Also identifies which stations already have TOD overlays.
"""

import json
import csv
from pathlib import Path
from math import radians, cos, sin, asin, sqrt
from collections import defaultdict

print("\n" + "="*80)
print("MULTI-RADIUS COMPARISON ANALYSIS")
print("500 ft vs 1/4 mile vs 1/2 mile")
print("="*80 + "\n")

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

# Load stations
print("Loading BSL/MFL stations...")
with open(DATA_PROC / 'dvrpc_bsl_mfl_trolley.geojson', 'r') as f:
    stations_data = json.load(f)

stations = []
for feature in stations_data['features']:
    props = feature['properties']
    coords = feature['geometry']['coordinates']
    stations.append({
        'name': props['Station_Na'],
        'line': props['LINE'],
        'district': props.get('DISTRICT', 'Unknown'),
        'lng': coords[0],
        'lat': coords[1]
    })

# Identify stations with existing TOD overlays
existing_tod_overlays = [
    '46th Street', '52nd Street', '56th Street', '60th Street', '63rd Street',
    'Allegheny', 'Berks', 'Erie-Torresdale', 'Frankford Transportation Center',
    'Huntingdon', 'Somerset', 'Tioga'
    # Note: Spring Garden not in our BSL/MFL dataset
]

for station in stations:
    station['has_tod_overlay'] = station['name'] in existing_tod_overlays

print(f"✓ Loaded {len(stations)} stations")
print(f"✓ {sum(s['has_tod_overlay'] for s in stations)} stations have existing TOD overlays")

# Load R-2 multifamily permits
print("\nLoading R-2 multifamily permits...")
permits = []
with open(DATA_RAW / 'philly_permits_ALL_newconst_2020_2025.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if 'R-2' not in row.get('occupancytype', ''):
            continue
        if row['permitnumber'].startswith(('PP-', 'EP-', 'MP-', 'FP-', 'SP-')):
            continue
        if row['lng'] and row['lat']:
            try:
                permits.append({
                    'lng': float(row['lng']),
                    'lat': float(row['lat']),
                    'address': row['address']
                })
            except (ValueError, TypeError):
                pass

print(f"✓ Loaded {len(permits)} R-2 multifamily permits")

# Define radii to compare
radii = {
    '500_feet': 152,      # Current city TOD overlay
    '1/4_mile': 402,      # Mayor's proposal (1,320 feet)
    '1/2_mile': 805       # Standard TOD / state bill
}

print("\n" + "="*80)
print("CLUSTERING PERMITS AT DIFFERENT RADII")
print("="*80)

# For each radius, count permits near each station
results_by_radius = {}

for radius_name, radius_meters in radii.items():
    print(f"\n{radius_name.replace('_', ' ').title()}: {radius_meters}m...")

    station_permits = defaultdict(list)

    for station in stations:
        seen_addresses = set()

        for permit in permits:
            dist = haversine(station['lng'], station['lat'], permit['lng'], permit['lat'])

            if dist <= radius_meters:
                addr_key = permit['address'].strip().upper()
                if addr_key not in seen_addresses:
                    seen_addresses.add(addr_key)
                    station_permits[station['name']].append(permit)

    # Estimate units (assume 3 units per R-2 permit if not specified)
    station_units = {}
    for station_name, permit_list in station_permits.items():
        station_units[station_name] = len(permit_list) * 3

    results_by_radius[radius_name] = station_units

    total_permits = sum(len(p) for p in station_permits.values())
    total_units = sum(station_units.values())
    print(f"  Total permits: {total_permits}, Estimated units: {total_units}")

# Create comparison table
print("\n" + "="*80)
print("STATION-BY-STATION COMPARISON")
print("="*80)
print(f"\n{'Station':<28} {'Line':<10} {'Dist':<5} {'TOD?':<5} {'500ft':<8} {'1/4mi':<8} {'1/2mi':<8} {'Gain (1/2mi)'}")
print("-"*95)

# Combine all results
comparison = []
for station in sorted(stations, key=lambda s: results_by_radius['1/2_mile'].get(s['name'], 0), reverse=True):
    name = station['name']
    units_500ft = results_by_radius['500_feet'].get(name, 0)
    units_quarter = results_by_radius['1/4_mile'].get(name, 0)
    units_half = results_by_radius['1/2_mile'].get(name, 0)

    tod_marker = "YES" if station['has_tod_overlay'] else ""
    gain_from_quarter = units_half - units_quarter

    print(f"{name[:26]:<28} {station['line'][:8]:<10} {station['district']:<5} {tod_marker:<5} "
          f"{units_500ft:<8} {units_quarter:<8} {units_half:<8} +{gain_from_quarter}")

    comparison.append({
        'Station': name,
        'Line': station['line'],
        'District': station['district'],
        'Has_Existing_TOD_Overlay': 'Yes' if station['has_tod_overlay'] else 'No',
        'Units_500ft': units_500ft,
        'Units_Quarter_Mile': units_quarter,
        'Units_Half_Mile': units_half,
        'Gain_Quarter_to_Half': gain_from_quarter
    })

# Summary statistics
print("\n" + "="*80)
print("SUMMARY STATISTICS")
print("="*80)

total_500ft = sum(r['Units_500ft'] for r in comparison)
total_quarter = sum(r['Units_Quarter_Mile'] for r in comparison)
total_half = sum(r['Units_Half_Mile'] for r in comparison)

print(f"\nTOTAL UNITS CAPTURED:")
print(f"  500 feet (current TOD overlay):      {total_500ft:5d} units")
print(f"  1/4 mile (mayor's proposal):         {total_quarter:5d} units ({total_quarter/total_500ft:.1f}x current)")
print(f"  1/2 mile (standard TOD/state bill):  {total_half:5d} units ({total_half/total_500ft:.1f}x current)")

print(f"\nINCREMENTAL GAINS:")
print(f"  Expanding 500ft → 1/4 mile:  +{total_quarter - total_500ft:5d} units (+{(total_quarter-total_500ft)/total_500ft*100:.0f}%)")
print(f"  Expanding 1/4 mile → 1/2 mile: +{total_half - total_quarter:5d} units (+{(total_half-total_quarter)/total_quarter*100:.0f}%)")
print(f"  Expanding 500ft → 1/2 mile:   +{total_half - total_500ft:5d} units (+{(total_half-total_500ft)/total_500ft*100:.0f}%)")

# Existing TOD overlay analysis
tod_overlay_stations = [r for r in comparison if r['Has_Existing_TOD_Overlay'] == 'Yes']
print(f"\nEXISTING TOD OVERLAY STATIONS ({len(tod_overlay_stations)} stations):")
print(f"  Current (500ft):      {sum(r['Units_500ft'] for r in tod_overlay_stations):5d} units")
print(f"  If expanded to 1/4mi: {sum(r['Units_Quarter_Mile'] for r in tod_overlay_stations):5d} units")
print(f"  If expanded to 1/2mi: {sum(r['Units_Half_Mile'] for r in tod_overlay_stations):5d} units")

# Save results
output_file = OUTPUTS / 'radius_comparison_analysis.csv'
with open(output_file, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=comparison[0].keys())
    writer.writeheader()
    writer.writerows(comparison)

print(f"\n✓ Saved detailed comparison to {output_file}")

# Political messaging
print("\n" + "="*80)
print("POLITICAL MESSAGING SCENARIOS")
print("="*80)

print("\n1. EASIEST SELL (Expand existing TOD overlays 500ft → 1/4 mile):")
print(f"   'Take the {len(tod_overlay_stations)} stations that ALREADY have TOD zoning")
print(f"    and expand from 500 feet to 1/4 mile (what the mayor proposed).'")
print(f"   Captures: {sum(r['Units_Quarter_Mile'] for r in tod_overlay_stations):,} units")

print("\n2. MODERATE SELL (1/4 mile at ALL BSL/MFL stations):")
print(f"   'Apply 1/4 mile TOD zones at all {len(stations)} BSL/MFL stations")
print(f"    (mayor's proposal distance, expanded coverage).'")
print(f"   Captures: {total_quarter:,} units")

print("\n3. STATE BILL CASE (1/2 mile at ALL SEPTA stations):")
print(f"   'State bill would create 1/2 mile zones at ALL SEPTA stations.")
print(f"    Just for BSL/MFL, that's {total_half - total_quarter:,} MORE units than 1/4 mile.'")
print(f"   BSL/MFL captures: {total_half:,} units")
print(f"   (Plus trolleys, regional rail, etc. - much larger total)")

print("\n4. COUNTER-ARGUMENT TO DISTRICTS 5 & 7:")
print(f"   'Your districts (5 & 7) have explosive growth already happening.")
print(f"    TOD policy helps MANAGE it and ensure affordability benefits,")
print(f"    not CAUSE it - the market is already building here.'")

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80 + "\n")
