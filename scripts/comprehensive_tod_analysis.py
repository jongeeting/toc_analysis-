#!/usr/bin/env python3
"""
Comprehensive Philadelphia TOC Analysis - BSL/MFL/Trolleys
Extracts trolley stops, combines with subway stations, calculates multi-line connectivity,
and generates City Council district political analysis.
"""

import json
import geopandas as gpd
import pandas as pd
from pathlib import Path
from collections import defaultdict
from shapely.geometry import Point
import warnings
warnings.filterwarnings('ignore')

print("\n" + "="*80)
print("PHILADELPHIA TRANSIT-ORIENTED COMMUNITIES ANALYSIS")
print("BSL / MFL / Trolleys - City Council Political Targeting")
print("="*80 + "\n")

# Paths
BASE = Path(__file__).parent.parent
DATA_RAW = BASE / 'data' / 'raw'
DATA_PROC = BASE / 'data' / 'processed'
DATA_PROC.mkdir(exist_ok=True)

# ============================================================================
# 1. Load DVRPC BSL/MFL Stations with TOD Scores
# ============================================================================
print("Loading DVRPC TOD scores for BSL/MFL...")
dvrpc_bsl_mfl = gpd.read_file(DATA_PROC / 'dvrpc_bsl_mfl_trolley.geojson')
print(f"  ✓ {len(dvrpc_bsl_mfl)} BSL/MFL stations with DVRPC TOD scores")

# ============================================================================
# 2. Extract Trolley Stops from SEPTA Data
# ============================================================================
print("\nExtracting Philadelphia trolley stops...")
with open(DATA_RAW / 'septa_all_transit_stops.geojson', 'r') as f:
    septa_all = json.load(f)

# Filter to trolley routes: T1-T5 (Routes 10,34,13,11,36) and G1 (Route 15)
trolley_codes = ['T1', 'T2', 'T3', 'T4', 'T5', 'G1']
trolley_features = []

for feature in septa_all['features']:
    line_abbr = feature['properties'].get('LineAbbr', '')
    if line_abbr in trolley_codes:
        trolley_features.append(feature)

print(f"  ✓ {len(trolley_features)} trolley stops extracted")

# Create GeoDataFrame
trolley_gdf = gpd.GeoDataFrame.from_features(trolley_features, crs='EPSG:4326')

# Map route codes to names
route_names = {
    'T1': 'Route 10 (Lancaster)',
    'T2': 'Route 34 (Baltimore)',
    'T3': 'Route 13 (Chester)',
    'T4': 'Route 11 (Woodland)',
    'T5': 'Route 36 (Elmwood)',
    'G1': 'Route 15 (Girard)'
}
trolley_gdf['RouteName'] = trolley_gdf['LineAbbr'].map(route_names)

print("\nTrolley Stops by Route:")
for code, name in route_names.items():
    count = len(trolley_gdf[trolley_gdf['LineAbbr'] == code])
    print(f"  {name:30} {count:3} stops")

# Save trolley stops
trolley_gdf.to_file(DATA_PROC / 'philadelphia_trolley_stops.geojson', driver='GeoJSON')
print(f"\n  ✓ Saved to {DATA_PROC / 'philadelphia_trolley_stops.geojson'}")

# ============================================================================
# 3. Multi-Line Connectivity Analysis
# ============================================================================
print("\n" + "="*80)
print("MULTI-LINE CONNECTIVITY ANALYSIS")
print("="*80 + "\n")

print("Identifying transfer stations and multi-line intersections...")

# For BSL/MFL: stations are discrete - find ones that are close to each other or named similarly
# For trolleys: group nearby stops (within 100m) to find transfer points

# Start with BSL/MFL stations - they're already unique stations
bsl_mfl_connectivity = defaultdict(list)
for idx, row in dvrpc_bsl_mfl.iterrows():
    station = row['Station_Na']
    line = row['LINE']
    bsl_mfl_connectivity[station].append(line)

# Find multi-line stations
multi_line_stations = {k: v for k, v in bsl_mfl_connectivity.items() if len(set(v)) > 1}

print(f"\nBSL/MFL Transfer Stations (serving multiple lines):")
for station, lines in sorted(multi_line_stations.items()):
    unique_lines = list(set(lines))
    print(f"  {station:30} {len(unique_lines)} lines: {', '.join(unique_lines)}")

# Add connectivity score to DVRPC data
dvrpc_bsl_mfl['num_lines'] = dvrpc_bsl_mfl['Station_Na'].map(
    lambda x: len(set(bsl_mfl_connectivity.get(x, [line])))
)

# For trolley stops: find major transfer points by clustering nearby stops
# Buffer 100m to find overlapping service areas
print("\nAnalyzing trolley transfer points...")

trolley_transfer_points = []
processed_stops = set()

for idx, stop in trolley_gdf.iterrows():
    if idx in processed_stops:
        continue

    # Find all stops within 100m
    point = stop.geometry
    buffer = point.buffer(0.001)  # ~100m in degrees

    nearby = trolley_gdf[trolley_gdf.geometry.within(buffer)]
    routes_here = nearby['LineAbbr'].unique()

    if len(routes_here) > 1:
        # This is a transfer point
        route_names_here = [route_names[r] for r in routes_here]
        trolley_transfer_points.append({
            'location': stop['StopName'],
            'geometry': point,
            'routes': route_names_here,
            'num_routes': len(routes_here)
        })
        processed_stops.update(nearby.index)

print(f"\nMajor Trolley Transfer Points ({len(trolley_transfer_points)} locations):")
for tp in sorted(trolley_transfer_points, key=lambda x: x['num_routes'], reverse=True)[:15]:
    print(f"  {tp['location']:50} {tp['num_routes']} routes")

# ============================================================================
# 4. City Council District Analysis
# ============================================================================
print("\n" + "="*80)
print("CITY COUNCIL DISTRICT ANALYSIS")
print("="*80 + "\n")

# Load Council districts
council_districts = gpd.read_file(DATA_RAW / 'city_council_districts.geojson')
print(f"Loaded {len(council_districts)} City Council districts")

# Spatial join BSL/MFL stations with districts
if dvrpc_bsl_mfl.crs != council_districts.crs:
    dvrpc_bsl_mfl = dvrpc_bsl_mfl.to_crs(council_districts.crs)

stations_by_district = gpd.sjoin(dvrpc_bsl_mfl, council_districts, how='left', predicate='within')

# Spatial join trolley stops with districts
if trolley_gdf.crs != council_districts.crs:
    trolley_gdf = trolley_gdf.to_crs(council_districts.crs)

trolley_by_district = gpd.sjoin(trolley_gdf, council_districts, how='left', predicate='within')

# Summary by district
print("\nSTATIONS PER CITY COUNCIL DISTRICT:\n")
print(f"{'District':<12} {'BSL/MFL':<12} {'Trolley Stops':<15} {'Multi-Line':<12} {'Total'}")
print("-" * 70)

district_summary = []
for district in sorted(council_districts['DISTRICT'].unique()):
    bsl_mfl_count = len(stations_by_district[stations_by_district['DISTRICT'] == district])
    trolley_count = len(trolley_by_district[trolley_by_district['DISTRICT'] == district])
    multi_line_count = len(stations_by_district[
        (stations_by_district['DISTRICT'] == district) & (stations_by_district['num_lines'] > 1)
    ])
    total = bsl_mfl_count + trolley_count

    print(f"{district:<12} {bsl_mfl_count:<12} {trolley_count:<15} {multi_line_count:<12} {total}")

    district_summary.append({
        'District': district,
        'BSL_MFL_Stations': bsl_mfl_count,
        'Trolley_Stops': trolley_count,
        'Multi_Line_Stations': multi_line_count,
        'Total_Transit_Points': total
    })

# Save district summary
pd.DataFrame(district_summary).to_csv(DATA_PROC / 'district_transit_summary.csv', index=False)
print(f"\n✓ Saved to {DATA_PROC / 'district_transit_summary.csv'}")

# ============================================================================
# 5. Enhanced TOD Scoring with Multi-Line Connectivity
# ============================================================================
print("\n" + "="*80)
print("ENHANCED TOD READINESS SCORING")
print("="*80 + "\n")

# Combine DVRPC scores with multi-line connectivity bonus
# Multi-line stations get bonus points for connectivity value

stations_by_district['connectivity_bonus'] = stations_by_district['num_lines'].apply(
    lambda x: min((x - 1) * 10, 20)  # Up to 20 bonus points for multi-line stations
)

stations_by_district['enhanced_score'] = (
    stations_by_district['DVRPC_Combined'] * 10 +  # Scale DVRPC 0-8 score to 0-80
    stations_by_district['connectivity_bonus']      # Add 0-20 connectivity bonus
)

# Top stations by enhanced score
top_stations = stations_by_district.nlargest(15, 'enhanced_score')[[
    'Station_Na', 'LINE', 'DISTRICT', 'num_lines', 'DVRPC_Combined',
    'connectivity_bonus', 'enhanced_score', 'ExistingOr', 'FuturePote'
]].copy()

print("TOP 15 STATIONS - Enhanced TOD Readiness (DVRPC + Multi-Line Connectivity):\n")
print(f"{'Rank':<6} {'Station':<30} {'District':<10} {'Lines':<7} {'Score':<8} {'DVRPC':<8} {'Bonus'}")
print("-" * 90)

for i, (idx, row) in enumerate(top_stations.iterrows(), 1):
    print(f"{i:<6} {row['Station_Na'][:28]:<30} {str(row['DISTRICT']):<10} {row['num_lines']:<7} "
          f"{row['enhanced_score']:<8.1f} {row['DVRPC_Combined']:<8.2f} +{row['connectivity_bonus']:.0f}")

# Save enhanced scores
top_stations.to_csv(DATA_PROC / 'top_tod_stations_enhanced.csv', index=False)
stations_by_district.to_file(DATA_PROC / 'bsl_mfl_stations_analysis.geojson', driver='GeoJSON')

print(f"\n✓ Saved to {DATA_PROC / 'top_tod_stations_enhanced.csv'}")
print(f"✓ Saved to {DATA_PROC / 'bsl_mfl_stations_analysis.geojson'}")

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80 + "\n")

print("Key Outputs:")
print(f"  • {DATA_PROC / 'philadelphia_trolley_stops.geojson'}")
print(f"  • {DATA_PROC / 'district_transit_summary.csv'}")
print(f"  • {DATA_PROC / 'top_tod_stations_enhanced.csv'}")
print(f"  • {DATA_PROC / 'bsl_mfl_stations_analysis.geojson'}")
print()
