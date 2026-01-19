#!/usr/bin/env python3
"""
Analyze what percentage of permit/unit activity is captured at different station cutoffs.
"""

import csv
import json

# Load BSL/MFL rankings with frequency
stations = []
with open('outputs/bsl_mfl_rankings_with_frequency.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        stations.append({
            'rank': int(row['Citywide_Rank']),
            'station': row['Station'],
            'line': row['Line'],
            'district': row['District'],
            'units': int(row['Units_2020_2025']),
            'score': float(row['Total_Score'])
        })

# Already sorted by rank, which corresponds to composite score
# Calculate totals
total_units = sum(s['units'] for s in stations)

print("=" * 80)
print("CONCENTRATION ANALYSIS: BSL/MFL Stations")
print("=" * 80)
print()

print(f"Total across all {len(stations)} BSL/MFL stations:")
print(f"  Units: {total_units:,}")
print()

# Analyze cutoffs
cutoffs = [10, 15, 20, 25, 30]

results = []

for cutoff in cutoffs:
    top_stations = stations[:cutoff]
    cutoff_units = sum(s['units'] for s in top_stations)
    pct = (cutoff_units / total_units * 100) if total_units > 0 else 0

    results.append({
        'cutoff': cutoff,
        'units': cutoff_units,
        'pct': pct
    })

    print(f"Top {cutoff} stations:")
    print(f"  Units: {cutoff_units:,} ({pct:.1f}%)")
    print()

# Show the bottom stations
bottom_15 = stations[15:]
bottom_units = sum(s['units'] for s in bottom_15)
bottom_pct = (bottom_units / total_units * 100) if total_units > 0 else 0

print(f"Bottom 15 stations (ranks 16-30):")
print(f"  Units: {bottom_units:,} ({bottom_pct:.1f}%)")
print()

print("=" * 80)
print("STATION NAMES BY CUTOFF")
print("=" * 80)
print()

for cutoff in [10, 15, 20]:
    print(f"Top {cutoff} Stations:")
    top_stations = stations[:cutoff]
    for s in top_stations:
        print(f"  {s['rank']:2d}. {s['station']:30s} ({s['line']:25s}) - {s['units']:4d} units")
    print()

# Export summary
summary = {
    'total_units_bsl_mfl': int(total_units),
    'total_stations': len(stations),
    'cutoff_analysis': results,
    'bottom_15_units': int(bottom_units),
    'bottom_15_pct': round(bottom_pct, 1)
}

with open('outputs/concentration_cutoffs.json', 'w') as f:
    json.dump(summary, f, indent=2)

print("✓ Saved to outputs/concentration_cutoffs.json")
