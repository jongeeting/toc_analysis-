#!/usr/bin/env python3
"""Create master rankings CSV with all transit modes"""

import csv
import json

all_stations = []

# Load BSL/MFL from CSV
with open('outputs/tod_station_rankings_citywide.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        all_stations.append({
            'Station': row['Station'],
            'Line': row['Line'],
            'Mode': 'BSL/MFL',
            'District': row['District'],
            'Units_2020_2025': int(row['Units_2020_2026']),
            'Score': float(row['Total_Score']),
            'Tier': row['Tier'],
            'Citywide_Rank': int(row['Rank']),
            'Existing_TOD_Overlay': 'Yes' if row['Station'] in [
                '46th Street', '52nd Street', '56th Street', '60th Street', '63rd Street',
                'Allegheny', 'Berks', 'Erie-Torresdale', 'Frankford Transportation Center',
                'Huntingdon', 'Somerset', 'Tioga'
            ] and 'Market/Frankford' in row['Line'] else 'No'
        })

# Load Regional Rail from JSON
with open('outputs/regional_rail_analysis.json', 'r') as f:
    rr_data = json.load(f)
    for station in rr_data['station_rankings']:
        all_stations.append({
            'Station': station['station'],
            'Line': 'Regional Rail',
            'Mode': 'Regional Rail',
            'District': station['district'] if station['district'] else 'Unknown',
            'Units_2020_2025': station['units'],
            'Score': None,  # RR doesn't have DVRPC scores
            'Tier': 'Regional Rail',
            'Citywide_Rank': None,
            'Existing_TOD_Overlay': 'No'
        })

# Sort by units descending
all_stations.sort(key=lambda x: x['Units_2020_2025'], reverse=True)

# Export to CSV
with open('outputs/all_stations_master_rankings.csv', 'w', newline='') as f:
    fieldnames = [
        'Rank_by_Units',
        'Station',
        'Line',
        'Mode',
        'District',
        'Units_2020_2025',
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
            'Station': station['Station'],
            'Line': station['Line'],
            'Mode': station['Mode'],
            'District': station['District'],
            'Units_2020_2025': station['Units_2020_2025'],
            'Score': station['Score'] if station['Score'] else '',
            'Tier': station['Tier'],
            'BSL_MFL_Citywide_Rank': station['Citywide_Rank'] if station['Citywide_Rank'] else '',
            'Existing_TOD_Overlay': station['Existing_TOD_Overlay']
        })

print(f"Exported {len(all_stations)} total stations (BSL/MFL + Regional Rail)")
print(f"Saved to outputs/all_stations_master_rankings.csv")
