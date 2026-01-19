#!/usr/bin/env python3
"""
Identify priority transit corridors (consecutive station segments) for TOC policy.
Focuses on geographic segments rather than individual isolated stations.
"""

import csv
import json
from collections import defaultdict

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

# Group by line
bsl_stations = sorted([s for s in stations if 'Broad Street' in s['line']],
                      key=lambda x: x['rank'])
mfl_stations = sorted([s for s in stations if 'Market/Frankford' in s['line']],
                      key=lambda x: x['rank'])

print("=" * 80)
print("PRIORITY TRANSIT CORRIDORS ANALYSIS")
print("=" * 80)
print()

# Define corridor segments manually based on geography and data
corridors = [
    {
        'name': 'South Broad Street BSL',
        'line': 'Broad Street Line',
        'segment': 'Ellsworth-Federal to AT&T Station',
        'stations': ['Ellsworth-Federal', 'Snyder', 'Tasker-Morris', 'Oregon', 'AT&T Station'],
        'districts': ['D1', 'D2'],
        'rationale': 'South Philly corridor with Ellsworth-Federal (#6 citywide)'
    },
    {
        'name': 'North Broad Street BSL (Girard Corridor)',
        'line': 'Broad Street Line',
        'segment': 'Girard to Erie',
        'stations': ['Girard', 'Susquehanna-Dauphin', 'Allegheny', 'Erie', 'Hunting Park'],
        'districts': ['D5', 'D8'],
        'rationale': 'Girard BSL (#2 citywide) anchors North Philly development corridor'
    },
    {
        'name': 'West Philadelphia MFL',
        'line': 'Market/Frankford Line',
        'segment': '46th Street to 63rd Street',
        'stations': ['46th Street', '52nd Street', '56th Street', '60th Street', '63rd Street'],
        'districts': ['D3', 'D4'],
        'rationale': '46th Street (#1 citywide), all have existing 500ft TOD'
    },
    {
        'name': 'North Philadelphia MFL (Kensington Corridor)',
        'line': 'Market/Frankford Line',
        'segment': 'York-Dauphin to Huntingdon',
        'stations': ['York-Dauphin', 'Berks', 'Somerset', 'Huntingdon', 'Church'],
        'districts': ['D1', 'D7'],
        'rationale': 'York-Dauphin (#4) + Berks (#5) = top development corridor'
    },
    {
        'name': 'Girard Avenue Multi-Modal Corridor',
        'line': 'BSL + MFL + Trolley Route 15',
        'segment': 'Girard BSL to waterfront (includes trolley)',
        'stations': ['Girard (BSL)', 'Girard (MFL)', 'Girard trolley stops (continuous)'],
        'districts': ['D1', 'D4', 'D5'],
        'rationale': 'Three transit modes, #2 and #3 citywide, 3,436 total corridor units'
    },
    {
        'name': 'Lancaster Avenue Multi-Modal Corridor',
        'line': 'MFL + Trolley Routes 10/11/13/34/36',
        'segment': '46th Street to 30th Street (includes trolley)',
        'stations': ['46th Street (MFL)', 'Lancaster trolley stops (continuous)', '30th Street (RR)'],
        'districts': ['D3'],
        'rationale': 'Trolley stops dominate D3 top 5, continuous high-density development'
    }
]

# Calculate stats for each corridor
for corridor in corridors:
    matching_stations = [s for s in stations if s['station'] in corridor['stations']]

    total_units = sum(s['units'] for s in matching_stations)
    avg_score = sum(s['score'] for s in matching_stations) / len(matching_stations) if matching_stations else 0
    num_existing_tod = sum(1 for s in matching_stations if s['existing_tod'] == 'Yes')

    corridor['stats'] = {
        'total_units': total_units,
        'num_stations': len(matching_stations),
        'avg_score': round(avg_score, 1),
        'existing_tod_count': num_existing_tod,
        'station_details': matching_stations
    }

# Sort corridors by total units (descending)
corridors.sort(key=lambda x: x['stats']['total_units'], reverse=True)

# Print corridor summaries
print("RECOMMENDED PRIORITY CORRIDORS (Ranked by Development Activity)")
print("=" * 80)
print()

for i, corridor in enumerate(corridors, 1):
    stats = corridor['stats']
    print(f"{i}. {corridor['name']}")
    print(f"   Line: {corridor['line']}")
    print(f"   Segment: {corridor['segment']}")
    print(f"   Districts: {', '.join(corridor['districts'])}")
    print(f"   Total Units: {stats['total_units']:,}")
    print(f"   Stations: {stats['num_stations']}")
    print(f"   Avg Composite Score: {stats['avg_score']}")
    print(f"   Existing TOD: {stats['existing_tod_count']} of {stats['num_stations']} stations")
    print(f"   Rationale: {corridor['rationale']}")
    print()

# Detailed station breakdown
print("=" * 80)
print("DETAILED STATION BREAKDOWN BY CORRIDOR")
print("=" * 80)
print()

for corridor in corridors:
    print(f"{corridor['name']} ({corridor['segment']})")
    print("-" * 80)

    if 'Multi-Modal' in corridor['name']:
        print("  (Multi-modal corridor - includes trolley/RR components)")
        print()
        continue

    for station in corridor['stats']['station_details']:
        tod_marker = "★" if station['existing_tod'] == 'Yes' else " "
        print(f"  {tod_marker} {station['station']:30s} | Rank #{station['rank']:2d} | "
              f"{station['units']:4d} units | Score: {station['score']:5.1f} | {station['district']}")

    print()

# Strategic recommendations
print("=" * 80)
print("STRATEGIC CORRIDOR RECOMMENDATIONS")
print("=" * 80)
print()

print("TIER 1 - MUST INCLUDE (Highest Development + Political Viability):")
print("  1. North Philadelphia MFL (York-Dauphin to Huntingdon)")
print("     - Ranks #4 and #5 citywide in single corridor")
print("     - 1,632 units across 5 stations")
print("     - 4 existing TOD overlays (just expand radius)")
print()
print("  2. Girard Avenue Multi-Modal Corridor")
print("     - Ranks #2 and #3 citywide")
print("     - 3,436 total units across BSL + MFL + Trolley")
print("     - Spans D1/D4/D5 but clear geographic identity")
print()
print("  3. West Philadelphia MFL (46th to 63rd)")
print("     - #1 station citywide (46th Street)")
print("     - ALL stations have existing 500ft TOD")
print("     - Single district (D3) - politically simple")
print()

print("TIER 2 - STRONG CANDIDATES (Good Development, Some Complexity):")
print("  4. Lancaster Avenue Multi-Modal Corridor")
print("     - Trolley stops dominate D3 district rankings")
print("     - 3,030+ units in D3 top 5")
print("     - Requires trolley corridor policy")
print()
print("  5. North Broad Street BSL (Girard to Erie)")
print("     - Anchored by Girard BSL (#2 citywide)")
print("     - Spans D5/D8 boundary")
print("     - 1,194 units across 5 stations")
print()

print("TIER 3 - COVERAGE/EQUITY (Lower Activity, Geographic Coverage):")
print("  6. South Broad Street BSL")
print("     - Anchored by Ellsworth-Federal (#6 citywide)")
print("     - Spans D1/D2 boundary")
print("     - 455 units (mostly at Ellsworth-Federal)")
print()

# Export corridor data
export = {
    'corridors': [],
    'total_corridor_units': sum(c['stats']['total_units'] for c in corridors),
    'total_corridor_stations': sum(c['stats']['num_stations'] for c in corridors)
}

for c in corridors:
    export['corridors'].append({
        'name': c['name'],
        'line': c['line'],
        'segment': c['segment'],
        'districts': c['districts'],
        'total_units': c['stats']['total_units'],
        'num_stations': c['stats']['num_stations'],
        'avg_score': c['stats']['avg_score'],
        'existing_tod_count': c['stats']['existing_tod_count'],
        'rationale': c['rationale']
    })

with open('outputs/priority_corridors.json', 'w') as f:
    json.dump(export, f, indent=2)

print()
print("✓ Saved to outputs/priority_corridors.json")
