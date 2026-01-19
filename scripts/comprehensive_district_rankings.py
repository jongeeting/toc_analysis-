#!/usr/bin/env python3
"""
Create comprehensive top 4-5 rankings per district INCLUDING trolleys.
Handle boundary stations appearing in multiple districts' top 5.
"""

import csv
import json
from collections import defaultdict

# Load all three modes with scores
print("Loading all transit modes...")

# BSL/MFL with composite scores
bsl_mfl = []
with open('outputs/bsl_mfl_rankings_with_frequency.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        bsl_mfl.append({
            'name': row['Station'],
            'line': row['Line'],
            'mode': 'BSL/MFL',
            'district': row['District'],
            'units': int(row['Units_2020_2025']),
            'score': float(row['Total_Score']),
            'citywide_rank': int(row['Citywide_Rank']),
            'tier': row['Tier'],
            'existing_tod': row['Existing_TOD_Overlay']
        })

print(f"  Loaded {len(bsl_mfl)} BSL/MFL stations")

# Regional Rail with composite scores
rr = []
with open('outputs/regional_rail_rankings_with_frequency.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        rr.append({
            'name': row['Station'],
            'line': 'Regional Rail',
            'mode': 'RR',
            'district': row['District'],
            'units': int(row['Units_2020_2025']),
            'score': float(row['Total_Score']),
            'rr_rank': int(row['RR_Rank']),
            'tier': 'Regional Rail',
            'existing_tod': 'No'
        })

print(f"  Loaded {len(rr)} RR stations")

# Trolleys with composite scores
trolleys = []
with open('outputs/trolley_rankings_with_frequency.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        trolleys.append({
            'name': row['Stop_Name'],
            'line': f"Trolley {row['Route']}",
            'mode': 'Trolley',
            'district': row['District'],
            'units': int(row['Units_2020_2025']),
            'score': float(row['Total_Score']),
            'trolley_rank': int(row['Trolley_Rank']),
            'tier': 'Trolley',
            'existing_tod': 'No'
        })

print(f"  Loaded {len(trolleys)} trolley stops")

# Load boundary stations to handle split custody
with open('outputs/boundary_stations.json', 'r') as f:
    boundary_data = json.load(f)

# Create a map of boundary stations with their expected districts
boundary_map = {}
for b in boundary_data['boundary_stations']:
    key = (b['station'], b['line'])
    boundary_map[key] = {
        'districts': [d['district'] for d in b['districts']],
        'station_info': b
    }

print(f"  Loaded {len(boundary_map)} boundary stations")

# Load split custody analysis to see which district gets more benefit
split_custody = {}
with open('outputs/split_custody_analysis.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        station_name = row['Station']
        line = row['Line']
        key = (station_name, line)

        # Parse districts and units
        d1_units = int(row['District_1_Units']) if row['District_1_Units'] else 0
        d2_units = int(row['District_2_Units']) if row['District_2_Units'] else 0

        split_custody[key] = {
            'total_units': int(row['Total_Units']),
            'districts': {}
        }

        # We need to map which is which - use expected districts from boundary data
        if key in boundary_map:
            expected_districts = boundary_map[key]['districts']
            # Assign units to districts (this is approximate since CSV doesn't label which is which)
            if len(expected_districts) >= 2:
                # Assume larger value goes to first district alphabetically (rough heuristic)
                # Better: we should look at the actual analysis output
                # For now, store both values
                split_custody[key]['primary_units'] = max(d1_units, d2_units)
                split_custody[key]['secondary_units'] = min(d1_units, d2_units)

print(f"  Loaded split custody data for {len(split_custody)} boundary stations")

# Group all stations by district
by_district = defaultdict(list)

for station in bsl_mfl + rr + trolleys:
    district = station['district']
    if district and district != 'Unknown':
        by_district[district].append(station)

# For boundary stations, add to BOTH districts if they're in either's top 5
# We'll do this after initial ranking

print("\nRanking top stations per district...")

district_rankings = {}

for district in sorted(by_district.keys()):
    stations_list = by_district[district]

    # Sort by composite score
    stations_list.sort(key=lambda x: x['score'], reverse=True)

    # Take top 10 initially (we'll filter to top 5 after checking boundaries)
    top_10 = stations_list[:10]

    district_rankings[district] = {
        'all_stations': stations_list,
        'top_10': top_10
    }

# Now handle boundary stations
# If a boundary station appears in top 5 of EITHER district, add it to the other's list too
print("\nHandling boundary station split custody...")

# First pass: identify which boundary stations are in top 5 of any district
boundary_in_top_5 = set()

for district, data in district_rankings.items():
    for i, station in enumerate(data['top_10'][:5]):
        # Check if this is a boundary station
        key = (station['name'], station['line'])
        if key in boundary_map:
            # This boundary station is in top 5 for this district
            boundary_in_top_5.add(key)

            # Get the other district(s) this station borders
            expected_districts = boundary_map[key]['districts']
            for other_district in expected_districts:
                if other_district != district:
                    # Add this station to the other district's rankings too
                    # Check if it's already there
                    other_stations = district_rankings[other_district]['all_stations']
                    station_names = [s['name'] for s in other_stations]

                    if station['name'] not in station_names:
                        # Add it
                        print(f"  Adding {station['name']} to District {other_district} (boundary with D{district})")
                        district_rankings[other_district]['all_stations'].append(station)
                        # Re-sort
                        district_rankings[other_district]['all_stations'].sort(
                            key=lambda x: x['score'], reverse=True
                        )

# Final top 5 per district
print("\n" + "="*80)
print("TOP 5 STATIONS PER DISTRICT (All Modes: BSL/MFL + RR + Trolleys)")
print("="*80)

for district in sorted(district_rankings.keys()):
    data = district_rankings[district]
    top_5 = data['all_stations'][:5]

    print(f"\nDistrict {district}:")
    print(f"{'Rank':<6} {'Station/Stop':<40} {'Mode':<10} {'Score':<8} {'Units':<8} {'Boundary?':<12}")
    print("-"*90)

    for i, station in enumerate(top_5, 1):
        key = (station['name'], station['line'])
        is_boundary = "BOUNDARY" if key in boundary_map else ""

        # Truncate long names
        name = station['name'][:39] if station['name'] else "Unknown"

        print(f"{i:<6} {name:<40} {station['mode']:<10} {station['score']:<8.1f} "
              f"{station['units']:<8} {is_boundary:<12}")

# Export to CSV
print("\n\nExporting comprehensive district rankings...")

with open('outputs/district_rankings_all_modes.csv', 'w', newline='') as f:
    fieldnames = [
        'District', 'Rank', 'Station_Stop_Name', 'Line_Route', 'Mode',
        'Units_2020_2025', 'Composite_Score', 'Tier',
        'Citywide_Rank', 'Is_Boundary', 'Existing_TOD'
    ]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()

    for district in sorted(district_rankings.keys()):
        top_5 = district_rankings[district]['all_stations'][:5]

        for i, station in enumerate(top_5, 1):
            key = (station['name'], station['line'])
            is_boundary = 'Yes' if key in boundary_map else 'No'

            citywide_rank = station.get('citywide_rank', '')
            if not citywide_rank and 'rr_rank' in station:
                citywide_rank = f"RR #{station['rr_rank']}"
            elif not citywide_rank and 'trolley_rank' in station:
                citywide_rank = f"Trolley #{station['trolley_rank']}"

            writer.writerow({
                'District': district,
                'Rank': i,
                'Station_Stop_Name': station['name'],
                'Line_Route': station['line'],
                'Mode': station['mode'],
                'Units_2020_2025': station['units'],
                'Composite_Score': round(station['score'], 1),
                'Tier': station['tier'],
                'Citywide_Rank': citywide_rank,
                'Is_Boundary': is_boundary,
                'Existing_TOD': station['existing_tod']
            })

print("✓ Saved to outputs/district_rankings_all_modes.csv")

# Summary stats
print("\n" + "="*80)
print("SUMMARY BY MODE IN TOP 5s")
print("="*80)

mode_counts = defaultdict(int)
boundary_counts = defaultdict(int)

for district in district_rankings.keys():
    top_5 = district_rankings[district]['all_stations'][:5]
    for station in top_5:
        mode_counts[station['mode']] += 1

        key = (station['name'], station['line'])
        if key in boundary_map:
            boundary_counts[district] += 1

print(f"\nMode distribution across all districts' top 5:")
for mode, count in sorted(mode_counts.items()):
    print(f"  {mode}: {count} stations/stops")

print(f"\nBoundary stations in top 5 by district:")
for district in sorted(boundary_counts.keys()):
    count = boundary_counts[district]
    print(f"  District {district}: {count} boundary stations in top 5")
