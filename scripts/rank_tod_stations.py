#!/usr/bin/env python3
"""
Rank BSL/MFL stations for TOD designation based on multiple factors.
Heavily weights current development activity and market momentum.
"""

import json
import csv
from pathlib import Path

print("\n" + "="*80)
print("TOD STATION RANKING - COMPREHENSIVE ANALYSIS")
print("Prioritizing Current Development Activity & Market Momentum")
print("="*80 + "\n")

# Paths
BASE = Path(__file__).parent.parent
DATA_PROC = BASE / 'data' / 'processed'
OUTPUTS = BASE / 'outputs'

# Load station data with DVRPC scores
print("Loading station data...")
with open(DATA_PROC / 'dvrpc_bsl_mfl_trolley.geojson', 'r') as f:
    stations_data = json.load(f)

# Load permit analysis results
with open(OUTPUTS / 'stations_permit_activity_comparison.csv', 'r') as f:
    reader = csv.DictReader(f)
    permit_data = {row['Station']: row for row in reader}

# Load multi-line connectivity analysis
with open(OUTPUTS / 'top_tod_stations_enhanced.csv', 'r') as f:
    reader = csv.DictReader(f)
    connectivity_data = {row['Station']: row for row in reader}

# Build comprehensive dataset
stations = []
for feature in stations_data['features']:
    props = feature['properties']
    station_name = props['Station_Na']

    # Get permit data
    permit_info = permit_data.get(station_name, {})

    # Get connectivity data
    conn_info = connectivity_data.get(station_name, {})

    stations.append({
        'name': station_name,
        'line': props['LINE'],
        'district': props.get('DISTRICT', 'N/A'),
        'dvrpc_existing': float(props.get('ExistingOr', 0)),
        'dvrpc_future': float(props.get('FuturePote', 0)),
        'dvrpc_combined': float(props.get('DVRPC_Combined', 0)),
        'dvrpc_units_2007_2017': int(float(permit_info.get('DVRPC_Units_2007_2017', 0))),
        'units_2020_2026': int(float(permit_info.get('Units_2020_2025', 0))),
        'permits_2020_2026': int(float(permit_info.get('Permits_2020_2025', 0))),
        'change_from_dvrpc': int(float(permit_info.get('Change_from_DVRPC', 0))),
        'pct_change': float(permit_info.get('Pct_Change', 0)),
        'num_lines': int(conn_info.get('Num_Lines', 1)),
        'connectivity_bonus': float(conn_info.get('Connectivity_Bonus', 0))
    })

print(f"✓ Loaded data for {len(stations)} stations")

# Calculate composite TOD scores
print("\nCalculating composite TOD scores...")
print("\nScoring methodology:")
print("  - Recent Development Activity (40 pts): Units built 2020-2026")
print("  - Market Momentum (20 pts): Growth vs DVRPC baseline")
print("  - Multi-Line Connectivity (20 pts): Transfer stations prioritized")
print("  - Existing TOD Fundamentals (10 pts): DVRPC Existing Orientation")
print("  - Future Market Potential (10 pts): DVRPC Future Potential")
print("  = Total: 100 points\n")

for station in stations:
    # 1. Recent Development Activity (0-40 points)
    # Scale: 0 units = 0 pts, 500+ units = 40 pts
    recent_dev_score = min(40, (station['units_2020_2026'] / 500) * 40)

    # 2. Market Momentum (0-20 points)
    # Positive growth gets points, decline gets 0
    # Scale: 0 change = 5 pts (neutral), +500 units = 20 pts
    if station['change_from_dvrpc'] >= 0:
        momentum_score = min(20, 5 + (station['change_from_dvrpc'] / 500) * 15)
    else:
        # Penalize major declines, but not too harshly if there's still activity
        if station['units_2020_2026'] > 200:
            # Still has significant activity despite decline
            momentum_score = 5
        else:
            momentum_score = max(0, 5 + (station['change_from_dvrpc'] / 500) * 5)

    # 3. Multi-Line Connectivity (0-20 points)
    # 1 line = 0 pts, 2 lines = 20 pts
    connectivity_score = (station['num_lines'] - 1) * 20

    # 4. Existing TOD Fundamentals (0-10 points)
    # DVRPC Existing Orientation: 0-4 scale → 0-10 points
    existing_score = (station['dvrpc_existing'] / 4) * 10

    # 5. Future Market Potential (0-10 points)
    # DVRPC Future Potential: 0-4 scale → 0-10 points
    future_score = (station['dvrpc_future'] / 4) * 10

    # Calculate total
    total_score = (
        recent_dev_score +
        momentum_score +
        connectivity_score +
        existing_score +
        future_score
    )

    station['recent_dev_score'] = round(recent_dev_score, 1)
    station['momentum_score'] = round(momentum_score, 1)
    station['connectivity_score'] = round(connectivity_score, 1)
    station['existing_score'] = round(existing_score, 1)
    station['future_score'] = round(future_score, 1)
    station['total_score'] = round(total_score, 1)

    # Calculate tier
    if total_score >= 70:
        station['tier'] = 'Tier 1 - High Priority'
    elif total_score >= 50:
        station['tier'] = 'Tier 2 - Strong Candidate'
    elif total_score >= 30:
        station['tier'] = 'Tier 3 - Moderate Candidate'
    else:
        station['tier'] = 'Tier 4 - Lower Priority'

# Sort by total score
stations.sort(key=lambda x: x['total_score'], reverse=True)

# Display results by tier
print("="*95)
print("TIER 1: HIGH PRIORITY TOD STATIONS (70+ points)")
print("="*95)
print(f"{'Rank':<6} {'Station':<26} {'Line':<8} {'Dist':<5} {'Units':<7} {'Score':<7} {'Multi-Line'}")
print("-"*95)

tier1 = [s for s in stations if s['tier'] == 'Tier 1 - High Priority']
for i, station in enumerate(tier1, 1):
    multi = "✓" if station['num_lines'] > 1 else ""
    print(f"{i:<6} {station['name'][:24]:<26} {station['line'][:6]:<8} {str(station['district']):<5} "
          f"{station['units_2020_2026']:<7} {station['total_score']:<7} {multi}")

print(f"\nTier 1 Summary: {len(tier1)} stations")

print("\n" + "="*95)
print("TIER 2: STRONG CANDIDATE STATIONS (50-69 points)")
print("="*95)
print(f"{'Rank':<6} {'Station':<26} {'Line':<8} {'Dist':<5} {'Units':<7} {'Score':<7} {'Multi-Line'}")
print("-"*95)

tier2 = [s for s in stations if s['tier'] == 'Tier 2 - Strong Candidate']
for i, station in enumerate(tier2, 1):
    multi = "✓" if station['num_lines'] > 1 else ""
    print(f"{i:<6} {station['name'][:24]:<26} {station['line'][:6]:<8} {str(station['district']):<5} "
          f"{station['units_2020_2026']:<7} {station['total_score']:<7} {multi}")

print(f"\nTier 2 Summary: {len(tier2)} stations")

print("\n" + "="*95)
print("TIER 3: MODERATE CANDIDATE STATIONS (30-49 points)")
print("="*95)
print(f"{'Rank':<6} {'Station':<26} {'Line':<8} {'Dist':<5} {'Units':<7} {'Score'}")
print("-"*95)

tier3 = [s for s in stations if s['tier'] == 'Tier 3 - Moderate Candidate']
for i, station in enumerate(tier3, 1):
    print(f"{i:<6} {station['name'][:24]:<26} {station['line'][:6]:<8} {str(station['district']):<5} "
          f"{station['units_2020_2026']:<7} {station['total_score']}")

print(f"\nTier 3 Summary: {len(tier3)} stations")

# Detailed breakdown for top 10
print("\n" + "="*95)
print("TOP 10 STATIONS - DETAILED SCORE BREAKDOWN")
print("="*95)

for i, station in enumerate(stations[:10], 1):
    print(f"\n{i}. {station['name']} ({station['line']}) - District {station['district']}")
    print(f"   Total Score: {station['total_score']}/100 - {station['tier']}")
    print(f"   ├─ Recent Development (40 max):    {station['recent_dev_score']:5.1f} pts  ({station['units_2020_2026']} units, {station['permits_2020_2026']} permits)")
    print(f"   ├─ Market Momentum (20 max):       {station['momentum_score']:5.1f} pts  ({station['change_from_dvrpc']:+d} vs DVRPC)")
    print(f"   ├─ Multi-Line Connectivity (20):   {station['connectivity_score']:5.1f} pts  ({station['num_lines']} line{'s' if station['num_lines'] > 1 else ''})")
    print(f"   ├─ Existing TOD Fundamentals (10): {station['existing_score']:5.1f} pts  (DVRPC: {station['dvrpc_existing']:.2f}/4)")
    print(f"   └─ Future Market Potential (10):   {station['future_score']:5.1f} pts  (DVRPC: {station['dvrpc_future']:.2f}/4)")

# Save comprehensive results
output_file = OUTPUTS / 'tod_station_rankings_comprehensive.csv'
with open(output_file, 'w', newline='') as f:
    fieldnames = [
        'Rank', 'Station', 'Line', 'District', 'Tier', 'Total_Score',
        'Recent_Dev_Score', 'Momentum_Score', 'Connectivity_Score',
        'Existing_Score', 'Future_Score',
        'Units_2020_2026', 'Change_from_DVRPC', 'Num_Lines',
        'DVRPC_Existing_Orientation', 'DVRPC_Future_Potential'
    ]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()

    for rank, station in enumerate(stations, 1):
        writer.writerow({
            'Rank': rank,
            'Station': station['name'],
            'Line': station['line'],
            'District': station['district'],
            'Tier': station['tier'],
            'Total_Score': station['total_score'],
            'Recent_Dev_Score': station['recent_dev_score'],
            'Momentum_Score': station['momentum_score'],
            'Connectivity_Score': station['connectivity_score'],
            'Existing_Score': station['existing_score'],
            'Future_Score': station['future_score'],
            'Units_2020_2026': station['units_2020_2026'],
            'Change_from_DVRPC': station['change_from_dvrpc'],
            'Num_Lines': station['num_lines'],
            'DVRPC_Existing_Orientation': station['dvrpc_existing'],
            'DVRPC_Future_Potential': station['dvrpc_future']
        })

print(f"\n✓ Saved comprehensive rankings to {output_file}")

# Generate summary statistics
print("\n" + "="*95)
print("SUMMARY STATISTICS")
print("="*95)

total_units_tier1 = sum(s['units_2020_2026'] for s in tier1)
total_units_tier2 = sum(s['units_2020_2026'] for s in tier2)
total_units_all = sum(s['units_2020_2026'] for s in stations)

multi_line_tier1 = len([s for s in tier1 if s['num_lines'] > 1])

print(f"\nTier 1 (High Priority):     {len(tier1):2d} stations | {total_units_tier1:5d} units ({total_units_tier1/total_units_all*100:.1f}% of total)")
print(f"Tier 2 (Strong Candidate):  {len(tier2):2d} stations | {total_units_tier2:5d} units ({total_units_tier2/total_units_all*100:.1f}% of total)")
print(f"Tier 3 (Moderate):          {len(tier3):2d} stations")
print(f"\nTier 1 + Tier 2 combined:   {len(tier1)+len(tier2):2d} stations | {total_units_tier1+total_units_tier2:5d} units ({(total_units_tier1+total_units_tier2)/total_units_all*100:.1f}% of total)")

print(f"\nMulti-line stations in Tier 1: {multi_line_tier1}/{len(tier1)}")

print("\n" + "="*95)
print("ANALYSIS COMPLETE")
print("="*95 + "\n")
