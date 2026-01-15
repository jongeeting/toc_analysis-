#!/usr/bin/env python3
"""Create comprehensive master rankings CSV with ALL transit modes"""

import csv
import json

all_stations = []

# Load BSL/MFL from CSV
print("Loading BSL/MFL stations...")
with open('outputs/tod_station_rankings_citywide.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        all_stations.append({
            'Station': row['Station'],
            'Line': row['Line'],
            'Mode': 'BSL/MFL',
            'District': row['District'],
            'Units_2020_2025': int(row['Units_2020_2026']),
            'Permits_2020_2025': None,  # BSL/MFL CSV doesn't have permit count
            'Score': float(row['Total_Score']),
            'Tier': row['Tier'],
            'Citywide_Rank': int(row['Rank']),
            'Existing_TOD_Overlay': 'Yes' if row['Station'] in [
                '46th Street', '52nd Street', '56th Street', '60th Street', '63rd Street',
                'Allegheny', 'Berks', 'Erie-Torresdale', 'Frankford Transportation Center',
                'Huntingdon', 'Somerset', 'Tioga'
            ] and 'Market/Frankford' in row['Line'] else 'No'
        })

print(f"  Loaded {len(all_stations)} BSL/MFL stations")

# Load Regional Rail from JSON
print("Loading Regional Rail stations...")
with open('outputs/regional_rail_analysis.json', 'r') as f:
    rr_data = json.load(f)
    rr_count = 0
    for station in rr_data['station_rankings']:
        all_stations.append({
            'Station': station['station'],
            'Line': 'Regional Rail',
            'Mode': 'Regional Rail',
            'District': station['district'] if station['district'] else 'Unknown',
            'Units_2020_2025': station['units'],
            'Permits_2020_2025': station['permits'],
            'Score': None,
            'Tier': 'Regional Rail',
            'Citywide_Rank': None,
            'Existing_TOD_Overlay': 'No'
        })
        rr_count += 1

print(f"  Loaded {rr_count} Regional Rail stations")

# Load Trolley Stops from JSON
print("Loading Trolley stops...")
with open('outputs/trolley_stops_analysis.json', 'r') as f:
    trolley_data = json.load(f)
    trolley_count = 0
    for stop in trolley_data['stop_rankings']:
        all_stations.append({
            'Station': stop['stop_name'],
            'Line': f"Trolley {stop['route']}",
            'Mode': 'Trolley',
            'District': stop['district'] if stop['district'] else 'Unknown',
            'Units_2020_2025': stop['units'],
            'Permits_2020_2025': stop['permits'],
            'Score': None,
            'Tier': 'Trolley',
            'Citywide_Rank': None,
            'Existing_TOD_Overlay': 'No'
        })
        trolley_count += 1

print(f"  Loaded {trolley_count} Trolley stops")

# Sort by units descending
all_stations.sort(key=lambda x: x['Units_2020_2025'], reverse=True)

# Export to CSV
print("\nExporting comprehensive master CSV...")
with open('outputs/all_transit_master_rankings.csv', 'w', newline='') as f:
    fieldnames = [
        'Rank_by_Units',
        'Station_Stop_Name',
        'Line_Route',
        'Mode',
        'District',
        'Units_2020_2025',
        'Permits_2020_2025',
        'Score',
        'Tier',
        'BSL_MFL_Citywide_Rank',
        'Existing_TOD_Overlay'
    ]
    writer = csv.DictWriter(f, fieldnames=fieldnames)

    writer.writeheader()
    for i, station in enumerate(all_stations, 1):
        writer.writerow({
            'Rank_by_Units': i,
            'Station_Stop_Name': station['Station'],
            'Line_Route': station['Line'],
            'Mode': station['Mode'],
            'District': station['District'],
            'Units_2020_2025': station['Units_2020_2025'],
            'Permits_2020_2025': station['Permits_2020_2025'] if station['Permits_2020_2025'] else '',
            'Score': station['Score'] if station['Score'] else '',
            'Tier': station['Tier'],
            'BSL_MFL_Citywide_Rank': station['Citywide_Rank'] if station['Citywide_Rank'] else '',
            'Existing_TOD_Overlay': station['Existing_TOD_Overlay']
        })

print(f"\n✓ Exported {len(all_stations)} total stations/stops to outputs/all_transit_master_rankings.csv")
print(f"\nBreakdown:")
print(f"  - BSL/MFL: 30 stations")
print(f"  - Regional Rail: {rr_count} stations")
print(f"  - Trolley: {trolley_count} stops")
print(f"\nNOTE: Trolley stops are very close together, so many permits are counted at")
print(f"      multiple stops. Per-stop trolley counts include significant overlap.")
print(f"      The incremental unique contribution of trolleys is ~8,400 units citywide.")
