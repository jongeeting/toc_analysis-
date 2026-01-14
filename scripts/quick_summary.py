#!/usr/bin/env python3
"""
Quick summary script for Philadelphia TOC political analysis.
Provides command-line summary of key statistics.
"""

import pandas as pd
import geopandas as gpd
from pathlib import Path

def main():
    print("\n" + "="*70)
    print(" PHILADELPHIA TRANSIT-ORIENTED COMMUNITIES POLITICAL ANALYSIS")
    print("="*70 + "\n")

    # Define paths
    DATA_RAW = Path(__file__).parent.parent / 'data' / 'raw'

    try:
        # Load data
        print("Loading data...")
        council_districts = gpd.read_file(DATA_RAW / 'city_council_districts.geojson')
        regional_rail = gpd.read_file(DATA_RAW / 'septa_regional_rail_stations.geojson')
        ridership = pd.read_csv(DATA_RAW / 'septa_ridership_rail.csv')

        # Ensure same CRS
        if council_districts.crs != regional_rail.crs:
            regional_rail = regional_rail.to_crs(council_districts.crs)

        # Spatial join
        stations_districts = gpd.sjoin(regional_rail, council_districts, how='left', predicate='within')

        # Count by district
        district_counts = stations_districts.groupby('DISTRICT').size().sort_index()

        print(f"\n✓ Loaded {len(regional_rail)} Regional Rail stations")
        print(f"✓ Loaded {len(council_districts)} City Council districts")
        print(f"✓ Loaded ridership data with {len(ridership)} records\n")

        print("-" * 70)
        print("STATIONS PER CITY COUNCIL DISTRICT")
        print("-" * 70)

        for district, count in district_counts.items():
            print(f"  District {district:2}: {count:2} stations")

        districts_with_stations = len(district_counts)
        districts_without = 10 - districts_with_stations

        print(f"\n  Districts with stations: {districts_with_stations}")
        print(f"  Districts without stations: {districts_without}")

        # Ridership summary
        year_cols = [col for col in ridership.columns if col.startswith('20')]
        if year_cols:
            recent = [col for col in year_cols if any(yr in col for yr in ['2022', '2023', '2024'])]
            if recent:
                ridership['avg_recent'] = ridership[recent].mean(axis=1)
                top_10 = ridership.nlargest(10, 'avg_recent')

                print("\n" + "-" * 70)
                print("TOP 10 HIGHEST RIDERSHIP STATIONS")
                print("-" * 70)

                station_col = [col for col in ridership.columns if 'station' in col.lower() or 'stop' in col.lower()]
                if station_col:
                    for idx, row in top_10.iterrows():
                        print(f"  {row[station_col[0]][:40]:40} {row['avg_recent']:>10,.0f} daily")

        print("\n" + "="*70)
        print("\nFor detailed analysis, run the Jupyter notebook:")
        print("  jupyter notebook notebooks/toc_political_analysis.ipynb")
        print("\nOutputs will be saved to: outputs/\n")

    except FileNotFoundError as e:
        print(f"\n❌ Error: Data file not found - {e}")
        print("   Please ensure data files are in data/raw/\n")
    except Exception as e:
        print(f"\n❌ Error: {e}\n")

if __name__ == "__main__":
    main()
