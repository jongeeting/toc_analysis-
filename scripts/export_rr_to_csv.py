#!/usr/bin/env python3
"""Export Regional Rail analysis to CSV format"""

import json
import csv

# Load RR data
with open('outputs/regional_rail_analysis.json', 'r') as f:
    data = json.load(f)

# Export to CSV
with open('outputs/regional_rail_rankings.csv', 'w', newline='') as f:
    writer = csv.writer(f)

    # Header
    writer.writerow([
        'Rank',
        'Station',
        'District',
        'Permits_2020_2025',
        'Units_2020_2025',
        'Latitude',
        'Longitude'
    ])

    # Data rows
    for i, station in enumerate(data['station_rankings'], 1):
        writer.writerow([
            i,
            station['station'],
            station['district'] if station['district'] else 'Unknown',
            station['permits'],
            station['units'],
            round(station['lat'], 6),
            round(station['lon'], 6)
        ])

print(f"Exported {len(data['station_rankings'])} Regional Rail stations to outputs/regional_rail_rankings.csv")
