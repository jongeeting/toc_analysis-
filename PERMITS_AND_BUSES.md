# Adding Building Permits and High-Frequency Bus Data

## Why This Matters

**DVRPC's Development Score is Outdated**:
- DVRPC report from 2017 used permits from ~2007-2017
- Their `Dev_Data` field shows multifamily units built (e.g., Girard: 1,543 units, Manayunk: 284 units)
- That data is now **8-18 years old**
- Philadelphia's development boom happened 2018-2024 - completely missed by DVRPC

**High-Frequency Buses = TOC-Worthy Transit**:
- SEPTA Bus Revolution (2025): 29 frequent routes (≤15 min headways, 7 days/week)
- 1.1 million more people within 10min walk of frequent service
- Frequent buses function like light rail for TOC purposes

---

## Data Sources

### 1. Philadelphia Building Permits

**Source**: [OpenDataPhilly L&I Building & Zoning Permits](https://opendataphilly.org/datasets/licenses-and-inspections-building-and-zoning-permits/)

**Coverage**: 882,000 permits from 2007 to present (updated daily)

**Download URL (GeoJSON)**:
```
https://phl.carto.com/api/v2/sql?format=GeoJSON&q=SELECT * FROM permits WHERE permitissuedate>='2020-01-01'
```

**Key Fields**:
- `permitissuedate`: Date permit issued
- `occupancytype`: Includes "R-2 Residential (>2 Dwellings)" for multifamily
- `typeofwork`: RESIDENTIAL, COMMERCIAL, etc.
- `the_geom`: Location geometry
- `address`: Street address

**Recent Activity (2020-2025)**:
- 285,518 total permits since Jan 2020
- Districts 5, 1, 2 account for ~40% of permits

**Note**: API queries can be complex. Alternative approach:
1. Download from OpenDataPhilly portal directly (slower but reliable)
2. Or use Philadelphia's official data portal: https://www.phila.gov/property/data/

### 2. SEPTA High-Frequency Bus Routes

**Source**: [SEPTA Bus Revolution](https://wwww.septa.org/initiatives/bus/)

**New Network (Launching 2025)**:
- 106 total bus routes
- **29 frequent routes** (≤15 min headways, 7 days/week)
- 30% increase in frequent route coverage
- Launches June 1, 2025 through Fall 2025

**Frequency Definition**:
- **Frequent**: ≤15 minutes, 15 hours/day, 7 days/week
- **Standard**: Less frequent service

**Map Coding**:
- Red = Frequent routes
- Black = Standard routes

**Access**:
- Maps: https://wwww.septa.org/maps/
- Bus Revolution site: https://septabusrevolution.com/
- Route data: Already in SEPTA OpenDataPhilly dataset (filter by frequency)

**Existing High-Frequency Routes** (Pre-Revolution):
Major corridors that already had frequent service:
- Route 23 (Germantown Ave / 11th-12th St)
- Route 47 (7th St)
- Route 48 (Whitaker Ave / Torresdale Ave)
- Route 61 (Ridge Ave)
- Route 21 (Hunting Park / Welch Rd)

*Note*: Full list available in SEPTA's frequency maps

---

## Analysis Approach

### Option 1: Permit Clustering Near Stations

**Goal**: Count recent multifamily permits within 0.25 miles of each BSL/MFL/trolley station

**Steps**:
1. Download permits from 2020-2025 with R-2 occupancy type
2. Buffer each transit station by 0.25 miles (1,320 feet)
3. Count permits within each buffer
4. Calculate permit density score

**Formula**:
```
Permit Score (0-40 points) = min(40, permits_count / 10 * 40)

Where:
- 0 permits = 0 points
- 10+ permits = 40 points (max)
- Linear scale between
```

**Comparison to DVRPC**:
```
Station          | DVRPC Dev_Data | Recent Permits | Change
                 | (2007-2017)    | (2020-2025)    |
-----------------+----------------+----------------+--------
Girard (MFL)     |  1,543 units   |    ??? units   |  ???
46th Street      |      0 units   |    ??? units   |  ???
Ellsworth-Fed    |      0 units   |    ??? units   |  ???
52nd Street      |      0 units   |    ??? units   |  ???
```

This would likely show **significant divergence** from DVRPC's 2017 scores.

### Option 2: High-Frequency Bus Bonus

**Goal**: Add connectivity points for stations near high-frequency bus routes

**Steps**:
1. Identify 29 frequent bus routes from Bus Revolution
2. Find bus stops for these routes within 0.1 miles of each station
3. Award bonus points

**Formula**:
```
Bus Frequency Bonus (0-20 points) = min(20, frequent_bus_routes_count * 5)

Where:
- 0 frequent routes = 0 points
- 4+ frequent routes = 20 points (max)
- +5 points per route
```

**Rationale**:
- Stations with frequent bus connections provide multi-modal access
- Similar to multi-line subway stations (BSL+MFL)
- High-frequency buses = reliable transit for TOC residents

### Option 3: Combined Enhanced Score

**New Formula** (replacing or augmenting DVRPC):
```
Enhanced Score =
  (DVRPC Existing Orientation × 10)        // 0-40 pts - still valid
  + (Recent Permit Activity)                // 0-40 pts - current data
  + (Multi-Line Connectivity Bonus)         // 0-10 pts - subway transfers
  + (High-Frequency Bus Bonus)              // 0-10 pts - bus connections

Total: 0-100 point scale
```

**Weights**:
- 40% = Existing TOD fundamentals (DVRPC Existing Orientation)
- 40% = Current development activity (2020-2025 permits)
- 10% = Subway multi-line connectivity
- 10% = Bus frequency connectivity

---

## Implementation Script Template

```python
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import json

# Load transit stations
stations = gpd.read_file('data/processed/bsl_mfl_stations_analysis.geojson')

# Load building permits (2020-2025, R-2 multifamily)
# TODO: Download from OpenDataPhilly or use Carto API
permits = gpd.read_file('data/raw/philly_permits_multifamily_2020_2025.geojson')

# Filter to recent permits
permits['permit_date'] = pd.to_datetime(permits['permitissuedate'])
recent_permits = permits[permits['permit_date'] >= '2020-01-01']

# Buffer stations (0.25 mile = 402 meters)
stations_buffered = stations.copy()
stations_buffered['geometry'] = stations.to_crs('EPSG:3857').buffer(402).to_crs(stations.crs)

# Spatial join: count permits in each buffer
permits_by_station = gpd.sjoin(recent_permits, stations_buffered, predicate='within')
permit_counts = permits_by_station.groupby('Station_Na').size()

# Calculate permit score (0-40 points)
stations['permit_count_2020_2025'] = stations['Station_Na'].map(permit_counts).fillna(0)
stations['permit_score'] = stations['permit_count_2020_2025'].apply(
    lambda x: min(40, (x / 10) * 40)
)

# Compare to DVRPC
stations['dvrpc_dev_data'] = ... # From DVRPC properties
stations['permit_delta'] = stations['permit_count_2020_2025'] - stations['dvrpc_dev_data']

# High-frequency bus bonus
# TODO: Load SEPTA frequent bus routes, buffer, count intersections
# stations['frequent_bus_bonus'] = ...

# Final enhanced score
stations['enhanced_score_v2'] = (
    stations['ExistingOr'] * 10 +         # DVRPC existing (0-40)
    stations['permit_score'] +             # Recent permits (0-40)
    stations['connectivity_bonus'] +       # Multi-line subway (0-10)
    stations.get('frequent_bus_bonus', 0)  # Frequent buses (0-10)
)

# Save results
stations[['Station_Na', 'DISTRICT', 'permit_count_2020_2025',
          'permit_score', 'enhanced_score_v2']].to_csv(
    'outputs/stations_with_permits_analysis.csv', index=False
)
```

---

## Expected Outcomes

### Stations That Will Rise in Rankings

Based on visible development 2020-2025, these likely have **high permit activity**:

1. **Northern Liberties / Fishtown** (MFL stations)
   - Spring Garden, Girard, Berks area
   - Massive residential development boom

2. **University City** (Trolley corridors + BSL)
   - 40th St Portal area
   - Baltimore Ave corridor (T2)

3. **Center City** (All lines)
   - 15th St / City Hall trolley hub
   - Market East corridor

4. **South Broad** (BSL)
   - Tasker-Morris, Ellsworth-Federal
   - Washington Ave corridor development

### Stations That May Fall in Rankings

DVRPC scored these high, but recent permit activity may be lower:

1. **Far Northeast** (MFL)
   - Arrott, Frankford Transportation Center
   - Less new multifamily development

2. **North Broad** (BSL)
   - Olney, Logan - some development but not boom levels

3. **Suburban Regional Rail**
   - Not part of BSL/MFL/trolley focus anyway

---

## Next Steps

1. **Download Permits**: Use OpenDataPhilly portal or API
2. **Identify Frequent Buses**: Get 29 route list from SEPTA Bus Revolution
3. **Run Clustering**: Buffer stations, count permits
4. **Generate Comparison**: DVRPC 2017 vs. Current 2020-2025
5. **Update Political Analysis**: Show which stations have hot development NOW

---

## Resources

- **OpenDataPhilly Permits**: https://opendataphilly.org/datasets/licenses-and-inspections-building-and-zoning-permits/
- **SEPTA Bus Revolution**: https://wwww.septa.org/initiatives/bus/
- **SEPTA Frequency Maps**: https://iseptaphilly.com/blog/frequencymap
- **Bus Revolution Approval**: https://whyy.org/articles/septa-bus-revolution-approval/

---

## Political Messaging

**Why Current Permits Matter More Than DVRPC**:

> "DVRPC's 2017 analysis used development data from 2007-2017. But Philadelphia's apartment boom happened AFTER that - from 2018 to 2024. We analyzed the most recent building permits to see where multifamily housing is actually being built TODAY, not a decade ago."

**Why High-Frequency Buses Belong in TOC**:

> "SEPTA's new Bus Revolution network includes 29 frequent routes with 15-minute service, 7 days a week. That's subway-level reliability. Stations with access to frequent bus routes give residents multi-modal connectivity - the same benefit as BSL+MFL transfer stations like Girard."

**The Updated Ranking**:

> "When we factor in CURRENT development activity (2020-2025) and multi-modal bus connections, the station rankings shift. Neighborhoods like Northern Liberties, University City, and South Broad - which are seeing explosive growth RIGHT NOW - rise to the top. This is where TOC policy will have the greatest near-term impact."
