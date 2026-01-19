#!/usr/bin/env python3
"""
Analyze concentration across ALL transit modes: BSL/MFL + Regional Rail + Trolleys
"""

import csv
import json

# Load all three modes
all_stations = []

# 1. Load BSL/MFL
print("Loading BSL/MFL stations...")
with open('outputs/bsl_mfl_rankings_with_frequency.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        all_stations.append({
            'name': row['Station'],
            'mode': 'BSL/MFL',
            'line': row['Line'],
            'district': row['District'],
            'units': int(row['Units_2020_2025']),
            'score': float(row['Total_Score']),
            'rank': int(row['Citywide_Rank'])
        })

# 2. Load Regional Rail
print("Loading Regional Rail stations...")
with open('outputs/regional_rail_rankings_with_frequency.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        all_stations.append({
            'name': row['Station'],
            'mode': 'Regional Rail',
            'line': 'RR',
            'district': row['District'],
            'units': int(row['Units_2020_2025']),
            'score': float(row['Total_Score']),
            'rank': int(row['RR_Rank'])
        })

# 3. Load Trolleys
print("Loading Trolley stops...")
with open('outputs/trolley_rankings_with_frequency.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        all_stations.append({
            'name': row['Stop_Name'],
            'mode': 'Trolley',
            'line': row['Route'],
            'district': row['District'],
            'units': int(row['Units_2020_2025']),
            'score': float(row['Total_Score']),
            'rank': int(row['Trolley_Rank'])
        })

# Sort by composite score (highest first)
all_stations.sort(key=lambda x: x['score'], reverse=True)

# Calculate totals
total_units = sum(s['units'] for s in all_stations)
total_count = len(all_stations)

# Count by mode
bsl_mfl_count = len([s for s in all_stations if s['mode'] == 'BSL/MFL'])
rr_count = len([s for s in all_stations if s['mode'] == 'Regional Rail'])
trolley_count = len([s for s in all_stations if s['mode'] == 'Trolley'])

print()
print("=" * 80)
print("CONCENTRATION ANALYSIS: ALL TRANSIT MODES")
print("=" * 80)
print()

print(f"Total across all {total_count} transit locations:")
print(f"  BSL/MFL: {bsl_mfl_count} stations")
print(f"  Regional Rail: {rr_count} stations")
print(f"  Trolleys: {trolley_count} stops")
print(f"  Total Units: {total_units:,}")
print()

# Analyze cutoffs
cutoffs = [10, 15, 20, 25, 50, 100]

results = []

print("=" * 80)
print("CONCENTRATION BY CUTOFF")
print("=" * 80)
print()

for cutoff in cutoffs:
    if cutoff > total_count:
        continue

    top_stations = all_stations[:cutoff]
    cutoff_units = sum(s['units'] for s in top_stations)
    pct = (cutoff_units / total_units * 100) if total_units > 0 else 0

    # Count by mode
    mode_counts = {
        'BSL/MFL': len([s for s in top_stations if s['mode'] == 'BSL/MFL']),
        'Regional Rail': len([s for s in top_stations if s['mode'] == 'Regional Rail']),
        'Trolley': len([s for s in top_stations if s['mode'] == 'Trolley'])
    }

    results.append({
        'cutoff': cutoff,
        'units': cutoff_units,
        'pct': pct,
        'mode_breakdown': mode_counts
    })

    print(f"Top {cutoff} stations/stops:")
    print(f"  Units: {cutoff_units:,} ({pct:.1f}%)")
    print(f"  Mode breakdown: {mode_counts['BSL/MFL']} BSL/MFL, {mode_counts['Regional Rail']} RR, {mode_counts['Trolley']} Trolley")
    print()

# Show bottom stations
bottom_half = all_stations[len(all_stations)//2:]
bottom_units = sum(s['units'] for s in bottom_half)
bottom_pct = (bottom_units / total_units * 100) if total_units > 0 else 0

print(f"Bottom {len(bottom_half)} stations/stops (lower 50%):")
print(f"  Units: {bottom_units:,} ({bottom_pct:.1f}%)")
print()

# Show top 25 with details
print("=" * 80)
print("TOP 25 STATIONS/STOPS ACROSS ALL MODES")
print("=" * 80)
print()

for i, s in enumerate(all_stations[:25], 1):
    print(f"{i:3d}. {s['name']:40s} ({s['mode']:15s}) - {s['units']:5d} units - Score: {s['score']:.1f}")

print()

# Mode distribution in top rankings
print("=" * 80)
print("MODE DISTRIBUTION IN TOP RANKINGS")
print("=" * 80)
print()

for cutoff in [10, 25, 50]:
    if cutoff > total_count:
        continue
    top = all_stations[:cutoff]
    bsl_mfl = len([s for s in top if s['mode'] == 'BSL/MFL'])
    rr = len([s for s in top if s['mode'] == 'Regional Rail'])
    trolley = len([s for s in top if s['mode'] == 'Trolley'])

    print(f"Top {cutoff}:")
    print(f"  BSL/MFL: {bsl_mfl} ({bsl_mfl/cutoff*100:.1f}%)")
    print(f"  Regional Rail: {rr} ({rr/cutoff*100:.1f}%)")
    print(f"  Trolley: {trolley} ({trolley/cutoff*100:.1f}%)")
    print()

# Export summary
summary = {
    'total_units_all_modes': int(total_units),
    'total_locations': total_count,
    'mode_counts': {
        'bsl_mfl': bsl_mfl_count,
        'regional_rail': rr_count,
        'trolley': trolley_count
    },
    'cutoff_analysis': results,
    'bottom_half_units': int(bottom_units),
    'bottom_half_pct': round(bottom_pct, 1)
}

with open('outputs/concentration_cutoffs_all_modes.json', 'w') as f:
    json.dump(summary, f, indent=2)

print("=" * 80)
print("✓ Saved to outputs/concentration_cutoffs_all_modes.json")
