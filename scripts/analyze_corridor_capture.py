#!/usr/bin/env python3
"""
Calculate what percentage of development activity the priority corridors capture.
"""

import csv
import json

# Load BSL/MFL stations
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
            'score': float(row['Total_Score']),
            'existing_tod': row['Existing_TOD_Overlay']
        })

# Define priority corridors (updated per user request)
corridors = {
    'tier1': [
        {
            'name': 'North Philadelphia MFL (Kensington Corridor)',
            'stations': ['York-Dauphin', 'Berks', 'Somerset', 'Huntingdon', 'Church']
        },
        {
            'name': 'Girard Multi-Modal Corridor',
            'stations': ['Girard']  # Both Girard BSL and MFL
        },
        {
            'name': 'West Philadelphia MFL',
            'stations': ['46th Street', '52nd Street', '56th Street', '60th Street', '63rd Street']
        }
    ],
    'tier2': [
        {
            'name': 'North Broad Street BSL (Girard to North Philly)',
            'stations': ['Girard', 'Susquehanna-Dauphin', 'Allegheny', 'Erie', 'Hunting Park']
            # Note: User wants to keep Erie + North Philly Amtrak together for development synergy
        },
        {
            'name': 'Lancaster Avenue Multi-Modal Corridor',
            'stations': ['46th Street']  # Anchor (trolley analysis separate)
        }
    ],
    'tier3': [
        {
            'name': 'South Broad Street BSL',
            'stations': ['Ellsworth-Federal', 'Snyder', 'Tasker-Morris', 'Oregon', 'AT&T Station']
        }
    ]
}

# Calculate corridor totals (handling duplicates like Girard appearing in multiple corridors)
all_corridor_stations = set()
tier_totals = {}

for tier_name, tier_corridors in corridors.items():
    tier_units = 0
    tier_stations_set = set()

    for corridor in tier_corridors:
        corridor_units = 0
        for station_name in corridor['stations']:
            # Find all matching stations (e.g., both Girards)
            matches = [s for s in stations if s['station'] == station_name]
            for match in matches:
                if match['station'] not in tier_stations_set:
                    corridor_units += match['units']
                    tier_stations_set.add(match['station'])
                    all_corridor_stations.add(match['station'])

        corridor['units'] = corridor_units
        tier_units += corridor_units

    tier_totals[tier_name] = {
        'units': tier_units,
        'stations': len(tier_stations_set)
    }

# Calculate totals
total_bsl_mfl_units = sum(s['units'] for s in stations)
total_corridor_units = sum(t['units'] for t in tier_totals.values())

print("=" * 80)
print("CORRIDOR CAPTURE RATE ANALYSIS")
print("=" * 80)
print()

print(f"Total BSL/MFL Development (All 30 stations): {total_bsl_mfl_units:,} units")
print()

# Show by tier
print("TIER 1 CORRIDORS (Must Include):")
print("-" * 80)
for corridor in corridors['tier1']:
    pct = (corridor['units'] / total_bsl_mfl_units * 100) if total_bsl_mfl_units > 0 else 0
    print(f"  {corridor['name']:50s} {corridor['units']:5,} units ({pct:4.1f}%)")
print(f"  {'TIER 1 SUBTOTAL':50s} {tier_totals['tier1']['units']:5,} units ({tier_totals['tier1']['units']/total_bsl_mfl_units*100:4.1f}%)")
print()

print("TIER 2 CORRIDORS (Strong Candidates):")
print("-" * 80)
for corridor in corridors['tier2']:
    pct = (corridor['units'] / total_bsl_mfl_units * 100) if total_bsl_mfl_units > 0 else 0
    print(f"  {corridor['name']:50s} {corridor['units']:5,} units ({pct:4.1f}%)")
print(f"  {'TIER 2 SUBTOTAL':50s} {tier_totals['tier2']['units']:5,} units ({tier_totals['tier2']['units']/total_bsl_mfl_units*100:4.1f}%)")
print()

print("TIER 3 CORRIDORS (Coverage/Equity):")
print("-" * 80)
for corridor in corridors['tier3']:
    pct = (corridor['units'] / total_bsl_mfl_units * 100) if total_bsl_mfl_units > 0 else 0
    print(f"  {corridor['name']:50s} {corridor['units']:5,} units ({pct:4.1f}%)")
print(f"  {'TIER 3 SUBTOTAL':50s} {tier_totals['tier3']['units']:5,} units ({tier_totals['tier3']['units']/total_bsl_mfl_units*100:4.1f}%)")
print()

print("=" * 80)
print("CUMULATIVE CAPTURE RATES")
print("=" * 80)
print()

tier1_total = tier_totals['tier1']['units']
tier1_2_total = tier_totals['tier1']['units'] + tier_totals['tier2']['units']
all_tiers_total = total_corridor_units

print(f"Tier 1 Only:         {tier1_total:5,} units ({tier1_total/total_bsl_mfl_units*100:5.1f}%)")
print(f"Tiers 1 + 2:         {tier1_2_total:5,} units ({tier1_2_total/total_bsl_mfl_units*100:5.1f}%)")
print(f"All 3 Tiers:         {all_tiers_total:5,} units ({all_tiers_total/total_bsl_mfl_units*100:5.1f}%)")
print()

# Compare to top-N cutoffs
print("=" * 80)
print("COMPARISON: CORRIDORS vs. TOP-N STATIONS")
print("=" * 80)
print()

# Calculate top-N
sorted_stations = sorted(stations, key=lambda x: x['rank'])
top_10_units = sum(s['units'] for s in sorted_stations[:10])
top_15_units = sum(s['units'] for s in sorted_stations[:15])
top_20_units = sum(s['units'] for s in sorted_stations[:20])

print(f"Top 10 stations:     {top_10_units:5,} units ({top_10_units/total_bsl_mfl_units*100:5.1f}%)")
print(f"Top 15 stations:     {top_15_units:5,} units ({top_15_units/total_bsl_mfl_units*100:5.1f}%)")
print(f"Top 20 stations:     {top_20_units:5,} units ({top_20_units/total_bsl_mfl_units*100:5.1f}%)")
print()
print(f"Tier 1 Corridors:    {tier1_total:5,} units ({tier1_total/total_bsl_mfl_units*100:5.1f}%) - similar to top 15")
print(f"Tiers 1+2 Corridors: {tier1_2_total:5,} units ({tier1_2_total/total_bsl_mfl_units*100:5.1f}%) - similar to top 20")
print()

# Add note about trolleys
print("=" * 80)
print("NOTE: TROLLEY CORRIDORS ADD SIGNIFICANT DEVELOPMENT")
print("=" * 80)
print()
print("These BSL/MFL corridor totals do NOT include:")
print("  - Girard Avenue trolley corridor: ~1,804 additional units (Route 15)")
print("  - Lancaster Avenue trolley corridor: ~3,030+ additional units (Routes 10/11/13/34/36)")
print("  - North Philadelphia Amtrak/SEPTA RR: ~186 units (per user request)")
print()
print("When multi-modal corridors are included, total development capture")
print("significantly exceeds BSL/MFL-only analysis.")
print()

# Detailed station list by corridor
print("=" * 80)
print("DETAILED STATION BREAKDOWN BY CORRIDOR")
print("=" * 80)
print()

for tier_name, tier_corridors in corridors.items():
    print(f"{tier_name.upper()}:")
    print()
    for corridor in tier_corridors:
        print(f"  {corridor['name']} ({corridor['units']} units):")
        for station_name in corridor['stations']:
            matches = [s for s in stations if s['station'] == station_name]
            for match in matches:
                tod_marker = "★" if match['existing_tod'] == 'Yes' else " "
                print(f"    {tod_marker} {match['station']:30s} | Rank #{match['rank']:2d} | "
                      f"{match['units']:4d} units | {match['line']}")
        print()

# Export summary
export = {
    'total_bsl_mfl_units': total_bsl_mfl_units,
    'corridor_approach': {
        'tier1_units': tier_totals['tier1']['units'],
        'tier1_pct': round(tier_totals['tier1']['units'] / total_bsl_mfl_units * 100, 1),
        'tier1_2_units': tier1_2_total,
        'tier1_2_pct': round(tier1_2_total / total_bsl_mfl_units * 100, 1),
        'all_tiers_units': all_tiers_total,
        'all_tiers_pct': round(all_tiers_total / total_bsl_mfl_units * 100, 1)
    },
    'top_n_comparison': {
        'top_10': {'units': top_10_units, 'pct': round(top_10_units / total_bsl_mfl_units * 100, 1)},
        'top_15': {'units': top_15_units, 'pct': round(top_15_units / total_bsl_mfl_units * 100, 1)},
        'top_20': {'units': top_20_units, 'pct': round(top_20_units / total_bsl_mfl_units * 100, 1)}
    }
}

with open('outputs/corridor_capture_analysis.json', 'w') as f:
    json.dump(export, f, indent=2)

print("✓ Saved to outputs/corridor_capture_analysis.json")
