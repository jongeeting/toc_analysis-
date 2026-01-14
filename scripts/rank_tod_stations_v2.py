#!/usr/bin/env python3
"""
Rank BSL/MFL stations for TOD designation based on multiple factors.
Heavily weights current development activity and market momentum.

Outputs:
- Top 20 stations citywide
- Top 4-5 stations per City Council district

Strategy:
- Plan A: Citywide rule-based ordinance
- Plan B: Each CM designates 3-4 stations in their district
"""

import json
import csv
from pathlib import Path
from collections import defaultdict

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

# Load multi-line connectivity analysis (for reference, but we won't use it since stations aren't actually transfers)
with open(OUTPUTS / 'top_tod_stations_enhanced.csv', 'r') as f:
    reader = csv.DictReader(f)
    connectivity_data = {row['Station']: row for row in reader}

# Build comprehensive dataset - EACH STATION IS SEPARATE
stations = []
for feature in stations_data['features']:
    props = feature['properties']
    station_name = props['Station_Na']
    line = props['LINE']

    # Create unique key: station name + line
    station_key = f"{station_name} ({line})"

    # Get permit data (keyed by station name only, not line)
    permit_info = permit_data.get(station_name, {})

    # Get connectivity data
    conn_info = connectivity_data.get(station_name, {})

    stations.append({
        'name': station_name,
        'line': line,
        'unique_id': station_key,
        'district': props.get('DISTRICT', 'Unknown'),
        'dvrpc_existing': float(props.get('ExistingOr', 0)),
        'dvrpc_future': float(props.get('FuturePote', 0)),
        'dvrpc_combined': float(props.get('DVRPC_Combined', 0)),
        'dvrpc_units_2007_2017': int(float(permit_info.get('DVRPC_Units_2007_2017', 0))),
        'units_2020_2026': int(float(permit_info.get('Units_2020_2025', 0))),
        'permits_2020_2026': int(float(permit_info.get('Permits_2020_2025', 0))),
        'change_from_dvrpc': int(float(permit_info.get('Change_from_DVRPC', 0))),
        'pct_change': float(permit_info.get('Pct_Change', 0)),
    })

print(f"✓ Loaded data for {len(stations)} stations")

# Calculate composite TOD scores
print("\nCalculating composite TOD scores...")
print("\nScoring methodology (NO multi-line bonuses - stations are NOT transfers):")
print("  - Recent Development Activity (50 pts): Units built 2020-2026")
print("  - Market Momentum (25 pts): Growth vs DVRPC baseline")
print("  - Existing TOD Fundamentals (15 pts): DVRPC Existing Orientation")
print("  - Future Market Potential (10 pts): DVRPC Future Potential")
print("  = Total: 100 points\n")

for station in stations:
    # 1. Recent Development Activity (0-50 points) - INCREASED WEIGHT
    # Scale: 0 units = 0 pts, 500+ units = 50 pts
    recent_dev_score = min(50, (station['units_2020_2026'] / 500) * 50)

    # 2. Market Momentum (0-25 points) - INCREASED WEIGHT
    # Positive growth gets points, decline gets 0-5
    if station['change_from_dvrpc'] >= 0:
        momentum_score = min(25, 5 + (station['change_from_dvrpc'] / 500) * 20)
    else:
        # Penalize major declines, but not too harshly if there's still activity
        if station['units_2020_2026'] > 200:
            momentum_score = 5  # Still has significant activity
        else:
            momentum_score = max(0, 5 + (station['change_from_dvrpc'] / 500) * 5)

    # 3. Existing TOD Fundamentals (0-15 points)
    # DVRPC Existing Orientation: 0-4 scale → 0-15 points
    existing_score = (station['dvrpc_existing'] / 4) * 15

    # 4. Future Market Potential (0-10 points)
    # DVRPC Future Potential: 0-4 scale → 0-10 points
    future_score = (station['dvrpc_future'] / 4) * 10

    # Calculate total
    total_score = (
        recent_dev_score +
        momentum_score +
        existing_score +
        future_score
    )

    station['recent_dev_score'] = round(recent_dev_score, 1)
    station['momentum_score'] = round(momentum_score, 1)
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

# ============================================================================
# CITYWIDE TOP 20
# ============================================================================
print("="*95)
print("TOP 20 STATIONS CITYWIDE (Recommended for Plan A: Citywide Ordinance)")
print("="*95)
print(f"{'Rank':<6} {'Station':<28} {'Line':<10} {'Dist':<5} {'Units':<7} {'Score':<7} {'Tier'}")
print("-"*95)

for i, station in enumerate(stations[:20], 1):
    tier_short = station['tier'].split(' - ')[0]
    print(f"{i:<6} {station['name'][:26]:<28} {station['line'][:8]:<10} {station['district']:<5} "
          f"{station['units_2020_2026']:<7} {station['total_score']:<7.1f} {tier_short}")

# ============================================================================
# TOP 4-5 PER DISTRICT
# ============================================================================
print("\n" + "="*95)
print("TOP 4-5 STATIONS PER COUNCIL DISTRICT (Plan B: District-by-District)")
print("="*95)

# Group stations by district
by_district = defaultdict(list)
for station in stations:
    if station['district'] != 'Unknown':
        by_district[station['district']].append(station)

# Sort districts numerically
for district in sorted(by_district.keys(), key=lambda x: int(x)):
    district_stations = sorted(by_district[district], key=lambda x: x['total_score'], reverse=True)

    print(f"\n{'='*95}")
    print(f"DISTRICT {district} - Top Stations")
    print(f"{'='*95}")
    print(f"{'Rank':<6} {'Station':<28} {'Line':<10} {'Units':<7} {'Score':<7} {'Tier'}")
    print("-"*95)

    # Show top 5 or all if fewer than 5
    for i, station in enumerate(district_stations[:5], 1):
        tier_short = station['tier'].split(' - ')[0]
        print(f"{i:<6} {station['name'][:26]:<28} {station['line'][:8]:<10} "
              f"{station['units_2020_2026']:<7} {station['total_score']:<7.1f} {tier_short}")

    total_units = sum(s['units_2020_2026'] for s in district_stations[:5])
    print(f"\nDistrict {district} Summary: {len(district_stations)} total stations, "
          f"top 5 have {total_units} units")

# ============================================================================
# DETAILED BREAKDOWN FOR CITYWIDE TOP 10
# ============================================================================
print("\n" + "="*95)
print("CITYWIDE TOP 10 - DETAILED SCORE BREAKDOWN")
print("="*95)

for i, station in enumerate(stations[:10], 1):
    print(f"\n{i}. {station['name']} - {station['line']} - District {station['district']}")
    print(f"   Total Score: {station['total_score']}/100 - {station['tier']}")
    print(f"   ├─ Recent Development (50 max):    {station['recent_dev_score']:5.1f} pts  ({station['units_2020_2026']} units, {station['permits_2020_2026']} permits)")
    print(f"   ├─ Market Momentum (25 max):       {station['momentum_score']:5.1f} pts  ({station['change_from_dvrpc']:+d} vs DVRPC)")
    print(f"   ├─ Existing TOD Fundamentals (15): {station['existing_score']:5.1f} pts  (DVRPC: {station['dvrpc_existing']:.2f}/4)")
    print(f"   └─ Future Market Potential (10):   {station['future_score']:5.1f} pts  (DVRPC: {station['dvrpc_future']:.2f}/4)")

# ============================================================================
# SAVE COMPREHENSIVE RESULTS
# ============================================================================
# Save full citywide rankings
output_file = OUTPUTS / 'tod_station_rankings_citywide.csv'
with open(output_file, 'w', newline='') as f:
    fieldnames = [
        'Rank', 'Station', 'Line', 'District', 'Tier', 'Total_Score',
        'Recent_Dev_Score', 'Momentum_Score', 'Existing_Score', 'Future_Score',
        'Units_2020_2026', 'Change_from_DVRPC',
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
            'Existing_Score': station['existing_score'],
            'Future_Score': station['future_score'],
            'Units_2020_2026': station['units_2020_2026'],
            'Change_from_DVRPC': station['change_from_dvrpc'],
            'DVRPC_Existing_Orientation': station['dvrpc_existing'],
            'DVRPC_Future_Potential': station['dvrpc_future']
        })

print(f"\n✓ Saved citywide rankings to {output_file}")

# Save district-by-district recommendations
output_file_districts = OUTPUTS / 'tod_station_rankings_by_district.csv'
with open(output_file_districts, 'w', newline='') as f:
    fieldnames = [
        'District', 'District_Rank', 'Station', 'Line', 'Total_Score',
        'Units_2020_2026', 'Change_from_DVRPC', 'Tier'
    ]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()

    for district in sorted(by_district.keys(), key=lambda x: int(x)):
        district_stations = sorted(by_district[district], key=lambda x: x['total_score'], reverse=True)
        for rank, station in enumerate(district_stations, 1):
            writer.writerow({
                'District': district,
                'District_Rank': rank,
                'Station': station['name'],
                'Line': station['line'],
                'Total_Score': station['total_score'],
                'Units_2020_2026': station['units_2020_2026'],
                'Change_from_DVRPC': station['change_from_dvrpc'],
                'Tier': station['tier']
            })

print(f"✓ Saved district rankings to {output_file_districts}")

# ============================================================================
# SUMMARY STATISTICS
# ============================================================================
print("\n" + "="*95)
print("SUMMARY STATISTICS")
print("="*95)

tier1 = [s for s in stations if s['tier'] == 'Tier 1 - High Priority']
tier2 = [s for s in stations if s['tier'] == 'Tier 2 - Strong Candidate']

total_units_tier1 = sum(s['units_2020_2026'] for s in tier1)
total_units_tier2 = sum(s['units_2020_2026'] for s in tier2)
total_units_all = sum(s['units_2020_2026'] for s in stations)

print(f"\nCITYWIDE:")
print(f"  Tier 1 (High Priority):     {len(tier1):2d} stations | {total_units_tier1:5d} units")
print(f"  Tier 2 (Strong Candidate):  {len(tier2):2d} stations | {total_units_tier2:5d} units")
print(f"  Top 20 stations:            {sum(s['units_2020_2026'] for s in stations[:20]):5d} units")

print(f"\nBY DISTRICT:")
for district in sorted(by_district.keys(), key=lambda x: int(x)):
    district_stations = by_district[district]
    top5_units = sum(s['units_2020_2026'] for s in sorted(district_stations, key=lambda x: x['total_score'], reverse=True)[:5])
    total_units_dist = sum(s['units_2020_2026'] for s in district_stations)
    print(f"  District {district}: {len(district_stations):2d} stations total | Top 5: {top5_units:5d} units | All: {total_units_dist:5d} units")

print("\n" + "="*95)
print("ANALYSIS COMPLETE")
print("="*95 + "\n")
