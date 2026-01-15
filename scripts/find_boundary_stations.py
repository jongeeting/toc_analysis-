#!/usr/bin/env python3
"""
Identify transit stations on or very near council district boundaries.
These require joint decisions by neighboring council members.
"""

import json
import math

def haversine(lon1, lat1, lon2, lat2):
    """Calculate distance between two points in meters"""
    R = 6371000
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

def point_in_polygon(lon, lat, polygon_coords):
    """Check if point is inside polygon using ray casting"""
    if polygon_coords[0][0] == polygon_coords[0][-1]:
        polygon_coords = polygon_coords[0][:-1]
    else:
        polygon_coords = polygon_coords[0]

    n = len(polygon_coords)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon_coords[i]
        xj, yj = polygon_coords[j]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside

def distance_to_polygon_boundary(lon, lat, polygon_coords):
    """Calculate minimum distance from point to polygon boundary"""
    if polygon_coords[0][0] == polygon_coords[0][-1]:
        polygon_coords = polygon_coords[0]
    else:
        polygon_coords = polygon_coords[0]

    min_dist = float('inf')

    # Check distance to each edge
    for i in range(len(polygon_coords) - 1):
        x1, y1 = polygon_coords[i]
        x2, y2 = polygon_coords[i + 1]

        # Calculate distance from point to line segment
        dist = haversine(lon, lat, x1, y1)
        dist2 = haversine(lon, lat, x2, y2)
        min_dist = min(min_dist, dist, dist2)

    return min_dist

def get_districts_within_distance(lon, lat, districts, buffer_meters=100):
    """Find all districts within buffer distance of a point"""
    nearby_districts = []

    for district in districts:
        district_num = district['properties']['DISTRICT']
        coords = district['geometry']['coordinates']

        # Check if point is inside district
        if point_in_polygon(lon, lat, coords):
            nearby_districts.append({
                'district': district_num,
                'status': 'INSIDE',
                'distance': 0
            })
        else:
            # Check distance to boundary
            dist = distance_to_polygon_boundary(lon, lat, coords)
            if dist <= buffer_meters:
                nearby_districts.append({
                    'district': district_num,
                    'status': 'NEAR_BOUNDARY',
                    'distance': round(dist, 1)
                })

    return nearby_districts

# Load council districts
print("Loading council districts...")
with open('data/raw/city_council_districts.geojson', 'r') as f:
    districts_geojson = json.load(f)
    districts = districts_geojson['features']

# Load all transit stations
all_stations = []

# BSL/MFL
print("Loading BSL/MFL stations...")
with open('data/processed/dvrpc_bsl_mfl_trolley.geojson', 'r') as f:
    bsl_mfl_data = json.load(f)
    for feature in bsl_mfl_data['features']:
        props = feature['properties']
        coords = feature['geometry']['coordinates']
        all_stations.append({
            'name': props['Station_Na'],
            'line': props['LINE'],
            'mode': 'BSL/MFL',
            'lon': coords[0],
            'lat': coords[1],
            'assigned_district': props.get('DISTRICT', 'N/A')
        })

# Regional Rail
print("Loading Regional Rail stations...")
with open('data/processed/septa_regional_rail_philadelphia.geojson', 'r') as f:
    rr_stations = json.load(f)
    for station in rr_stations:
        all_stations.append({
            'name': station['location_name'],
            'line': 'Regional Rail',
            'mode': 'Regional Rail',
            'lon': float(station['location_lon']),
            'lat': float(station['location_lat']),
            'assigned_district': None
        })

print(f"\nAnalyzing {len(all_stations)} stations for boundary proximity...\n")

# Check boundary proximity - use 100 meters as threshold
boundary_threshold = 100  # meters
boundary_stations = []

for station in all_stations:
    nearby = get_districts_within_distance(
        station['lon'],
        station['lat'],
        districts,
        boundary_threshold
    )

    # Station is on boundary if it's near multiple districts
    if len(nearby) > 1:
        boundary_stations.append({
            'station': station['name'],
            'line': station['line'],
            'mode': station['mode'],
            'districts': nearby,
            'assigned_district': station['assigned_district']
        })

# Sort by number of districts, then by station name
boundary_stations.sort(key=lambda x: (-len(x['districts']), x['station']))

print("="*80)
print("STATIONS ON OR NEAR COUNCIL DISTRICT BOUNDARIES")
print("(Within 100 meters of boundary)")
print("="*80)
print()

if boundary_stations:
    for item in boundary_stations:
        districts_str = " / ".join([
            f"District {d['district']}" +
            (f" ({d['status']}, {d['distance']}m)" if d['status'] == 'NEAR_BOUNDARY' else f" ({d['status']})")
            for d in item['districts']
        ])

        print(f"Station: {item['station']} ({item['line']})")
        print(f"  Boundary Districts: {districts_str}")
        print(f"  Assigned District: {item['assigned_district']}")
        print(f"  ** JOINT DECISION REQUIRED **")
        print()
else:
    print("No stations found on district boundaries within threshold.")

# Group by district pairs for summary
print("\n" + "="*80)
print("SUMMARY BY DISTRICT BOUNDARY")
print("="*80)
print()

from collections import defaultdict
boundary_pairs = defaultdict(list)

for item in boundary_stations:
    if len(item['districts']) == 2:
        d1 = item['districts'][0]['district']
        d2 = item['districts'][1]['district']
        pair_key = tuple(sorted([d1, d2]))
        boundary_pairs[pair_key].append(item)

for pair, stations in sorted(boundary_pairs.items()):
    print(f"District {pair[0]} / District {pair[1]} Boundary:")
    for item in stations:
        print(f"  - {item['station']} ({item['line']})")
    print()

# Save results
output = {
    'threshold_meters': boundary_threshold,
    'boundary_stations': boundary_stations,
    'total_boundary_stations': len(boundary_stations),
    'summary_by_pair': {
        f"{p[0]}-{p[1]}": [s['station'] for s in stations]
        for p, stations in boundary_pairs.items()
    }
}

with open('outputs/boundary_stations.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f"\nResults saved to outputs/boundary_stations.json")
print(f"Total boundary stations: {len(boundary_stations)}")
