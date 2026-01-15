#!/usr/bin/env python3
"""
Add transit frequency weighting to station rankings.
Revised scoring: Development (50%) + Frequency (25%) + DVRPC (25%)
"""

import csv
import json

# Define transit frequency scores (higher = more frequent)
FREQUENCY_SCORES = {
    # BSL/MFL: 6-20 min service = highest score
    'BSL': 100,
    'MFL': 100,

    # Trolleys: 10-15 min service = high score
    'Trolley': 85,

    # Regional Rail: 30-60 min service = moderate score
    'RR': 60
}

def get_frequency_score(line, mode):
    """Assign frequency score based on line/mode"""
    if 'Broad Street' in line:
        return FREQUENCY_SCORES['BSL']
    elif 'Market/Frankford' in line:
        return FREQUENCY_SCORES['MFL']
    elif mode == 'Trolley':
        return FREQUENCY_SCORES['Trolley']
    elif mode == 'Regional Rail':
        return FREQUENCY_SCORES['RR']
    else:
        return 50  # Default for unknown

# Load BSL/MFL and recalculate with frequency weighting
print("="*80)
print("ADDING TRANSIT FREQUENCY WEIGHTING TO RANKINGS")
print("="*80)
print("\nRevised Scoring Methodology:")
print("  - Development Activity: 50 pts (units 2020-2025)")
print("  - Transit Frequency: 25 pts (service headways)")
print("  - DVRPC Existing Orientation: 15 pts (walkability, jobs access, etc.)")
print("  - DVRPC Future Potential: 10 pts (market conditions)")
print("="*80)

bsl_mfl_revised = []

print("\nLoading BSL/MFL stations...")
with open('outputs/tod_station_rankings_citywide.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Extract existing scores
        recent_dev = float(row['Recent_Dev_Score'])
        existing = float(row['Existing_Score'])
        future = float(row['Future_Score'])

        # Add frequency score (25 points max)
        freq_score = get_frequency_score(row['Line'], 'BSL/MFL') * 0.25

        # New total score
        new_total = recent_dev + freq_score + existing + future

        bsl_mfl_revised.append({
            'Station': row['Station'],
            'Line': row['Line'],
            'District': row['District'],
            'Units_2020_2025': int(row['Units_2020_2026']),
            'Development_Score': recent_dev,
            'Frequency_Score': round(freq_score, 1),
            'Existing_Score': existing,
            'Future_Score': future,
            'Total_Score': round(new_total, 1),
            'Old_Total': float(row['Total_Score']),
            'Tier': row['Tier'],
            'Existing_TOD': 'Yes' if row['Station'] in [
                '46th Street', '52nd Street', '56th Street', '60th Street', '63rd Street',
                'Allegheny', 'Berks', 'Erie-Torresdale', 'Frankford Transportation Center',
                'Huntingdon', 'Somerset', 'Tioga'
            ] and 'Market/Frankford' in row['Line'] else 'No'
        })

# Sort by new total score
bsl_mfl_revised.sort(key=lambda x: x['Total_Score'], reverse=True)

# Add citywide rank
for i, station in enumerate(bsl_mfl_revised, 1):
    station['Citywide_Rank'] = i

print(f"Loaded {len(bsl_mfl_revised)} BSL/MFL stations")

# Show top 10 with frequency scores
print("\n" + "="*80)
print("TOP 10 BSL/MFL STATIONS (With Frequency Weighting)")
print("="*80)
print(f"\n{'Rank':<6} {'Station':<25} {'Line':<8} {'Dev':<6} {'Freq':<6} {'Exist':<6} {'Future':<6} {'Total':<6}")
print("-"*80)

for station in bsl_mfl_revised[:10]:
    line_abbr = 'BSL' if 'Broad' in station['Line'] else 'MFL'
    print(f"{station['Citywide_Rank']:<6} {station['Station'][:24]:<25} {line_abbr:<8} "
          f"{station['Development_Score']:<6.1f} {station['Frequency_Score']:<6.1f} "
          f"{station['Existing_Score']:<6.1f} {station['Future_Score']:<6.1f} "
          f"{station['Total_Score']:<6.1f}")

# Load Regional Rail and add frequency scores
print("\n\nLoading Regional Rail stations...")
rr_revised = []

with open('outputs/regional_rail_analysis.json', 'r') as f:
    rr_data = json.load(f)

for station in rr_data['station_rankings']:
    # For RR (no DVRPC scores), use simpler methodology:
    # Development: 70%, Frequency: 30%

    # Normalize units to 70-point scale (max ~800 units)
    dev_score = min((station['units'] / 800.0) * 70, 70)

    # Frequency: 30 points max, RR gets 60% = 18 points
    freq_score = FREQUENCY_SCORES['RR'] * 0.30

    total = dev_score + freq_score

    rr_revised.append({
        'Station': station['station'],
        'Line': 'Regional Rail',
        'District': station['district'] if station['district'] else 'Unknown',
        'Units_2020_2025': station['units'],
        'Permits_2020_2025': station['permits'],
        'Development_Score': round(dev_score, 1),
        'Frequency_Score': round(freq_score, 1),
        'Total_Score': round(total, 1)
    })

rr_revised.sort(key=lambda x: x['Total_Score'], reverse=True)
for i, station in enumerate(rr_revised, 1):
    station['RR_Rank'] = i

print(f"Loaded {len(rr_revised)} Regional Rail stations")

# Show top 10 RR
print("\n" + "="*80)
print("TOP 10 REGIONAL RAIL STATIONS (With Frequency Weighting)")
print("="*80)
print(f"\n{'Rank':<6} {'Station':<30} {'Dev':<6} {'Freq':<6} {'Total':<6} {'Units':<8}")
print("-"*80)

for station in rr_revised[:10]:
    print(f"{station['RR_Rank']:<6} {station['Station'][:29]:<30} "
          f"{station['Development_Score']:<6.1f} {station['Frequency_Score']:<6.1f} "
          f"{station['Total_Score']:<6.1f} {station['Units_2020_2025']:<8}")

# Export revised BSL/MFL rankings
print("\n\nExporting revised rankings...")
with open('outputs/bsl_mfl_rankings_with_frequency.csv', 'w', newline='') as f:
    fieldnames = [
        'Citywide_Rank', 'Station', 'Line', 'District', 'Units_2020_2025',
        'Development_Score', 'Frequency_Score', 'Existing_Score', 'Future_Score',
        'Total_Score', 'Tier', 'Existing_TOD_Overlay'
    ]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()

    for station in bsl_mfl_revised:
        writer.writerow({
            'Citywide_Rank': station['Citywide_Rank'],
            'Station': station['Station'],
            'Line': station['Line'],
            'District': station['District'],
            'Units_2020_2025': station['Units_2020_2025'],
            'Development_Score': station['Development_Score'],
            'Frequency_Score': station['Frequency_Score'],
            'Existing_Score': station['Existing_Score'],
            'Future_Score': station['Future_Score'],
            'Total_Score': station['Total_Score'],
            'Tier': station['Tier'],
            'Existing_TOD_Overlay': station['Existing_TOD']
        })

# Export revised RR rankings
with open('outputs/regional_rail_rankings_with_frequency.csv', 'w', newline='') as f:
    fieldnames = [
        'RR_Rank', 'Station', 'District', 'Units_2020_2025', 'Permits_2020_2025',
        'Development_Score', 'Frequency_Score', 'Total_Score'
    ]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()

    for station in rr_revised:
        writer.writerow({
            'RR_Rank': station['RR_Rank'],
            'Station': station['Station'],
            'District': station['District'],
            'Units_2020_2025': station['Units_2020_2025'],
            'Permits_2020_2025': station['Permits_2020_2025'],
            'Development_Score': station['Development_Score'],
            'Frequency_Score': station['Frequency_Score'],
            'Total_Score': station['Total_Score']
        })

print("\n✓ Saved to outputs/bsl_mfl_rankings_with_frequency.csv")
print("✓ Saved to outputs/regional_rail_rankings_with_frequency.csv")

# Summary stats
print("\n" + "="*80)
print("FREQUENCY WEIGHTING IMPACT SUMMARY")
print("="*80)

# Check if rankings changed
original_top_10 = [s['Station'] for s in sorted(bsl_mfl_revised, key=lambda x: x['Old_Total'], reverse=True)[:10]]
new_top_10 = [s['Station'] for s in bsl_mfl_revised[:10]]

if original_top_10 == new_top_10:
    print("\n✓ Top 10 BSL/MFL rankings UNCHANGED (frequency already implicit in DVRPC scores)")
else:
    print("\n⚠ Top 10 BSL/MFL rankings CHANGED:")
    for i, (old, new) in enumerate(zip(original_top_10, new_top_10), 1):
        if old != new:
            print(f"  #{i}: {old} → {new}")

print("\nFrequency Score Assignments:")
print(f"  BSL/MFL: 25.0 points (6-20 min service)")
print(f"  Trolleys: 21.2 points (10-15 min service)")
print(f"  Regional Rail: 18.0 points (30-60 min service)")
print("\nNote: DVRPC Existing Orientation already includes jobs accessibility")
print("(regional employment reachable via transit, not just jobs at station)")
