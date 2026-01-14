# Philadelphia TOC Political Analysis - Summary

## Data Collected (as of January 2026)

### Transit Station Data

#### 1. BSL/MFL Stations (30 total)
**Source**: DVRPC TOD Evaluation Tool
**File**: `data/processed/dvrpc_bsl_mfl_trolley.geojson`

- **Broad Street Line**: 14 stations
- **Market-Frankford Line**: 16 stations
- **Includes**: DVRPC TOD Readiness Scores (1-4 scale, 12 factors)

**Top 5 Stations by DVRPC TOD Score**:
1. 46th Street (BSL) - 7.46 (ExO: 3.86, FP: 3.60)
2. Ellsworth-Federal (BSL) - 7.06 (ExO: 3.86, FP: 3.20)
3. Girard (MFL) - 6.86 (ExO: 3.86, FP: 3.00)
4. 52nd Street (BSL) - 6.80 (ExO: 4.00, FP: 2.80)
5. Snyder (BSL) - 6.66 (ExO: 3.86, FP: 2.80)

**DVRPC Scoring Categories**:
- **Existing Orientation** (7 factors): Transit connectivity, job access, travel time, intensity, car ownership, non-car commuters, walkability
- **Future Potential** (5 factors): Development activity, commercial market, residential market, available land, planning context

#### 2. Trolley Stops (551 total)
**Source**: SEPTA OpenDataPhilly
**File**: `data/processed/philadelphia_trolley_stops.geojson`

Subway-surface trolley routes (rebranded as SEPTA Metro "T" in Feb 2024):
- **T1 (Route 10 - Lancaster Ave)**: 75 stops
- **T2 (Route 34 - Baltimore Ave)**: 70 stops
- **T3 (Route 13 - Chester Ave)**: 96 stops
- **T4 (Route 11 - Woodland Ave)**: 95 stops
- **T5 (Route 36 - Elmwood Ave)**: 91 stops
- **G1 (Route 15 - Girard Ave)**: 124 stops

#### 3. City Council Districts
**Source**: OpenDataPhilly
**File**: `data/raw/city_council_districts.geojson`

- 10 City Council districts covering Philadelphia

#### 4. Ridership Data
**Source**: SEPTA OpenDataPhilly
**File**: `data/raw/septa_ridership_rail.csv`

- Regional Rail ridership by station (2017-2024, excludes 2020-2021 COVID years)
- Note: BSL/MFL/trolley ridership data needs separate acquisition

## Analysis Framework

### Multi-Line Connectivity Scoring
**Key Insight**: Stations serving multiple transit lines provide greatest access and development potential.

**Transfer Stations to Prioritize**:
- BSL/MFL intersections (e.g., City Hall area, potential transfers)
- Trolley/BSL/MFL transfer points
- Multi-trolley intersections (West Philadelphia corridors)

**Connectivity Bonus**: +10 points per additional line (max +20)

### Enhanced TOD Score Formula
```
Enhanced Score = (DVRPC Combined Score × 10) + Connectivity Bonus
```

**Components**:
- **DVRPC Score** (0-80 points): Existing orientation + Future potential
- **Connectivity Bonus** (0-20 points): Additional lines served
- **Total**: 0-100 point scale

### Political Strategy Factors

**For City Council Engagement**:
1. **Stations per District**: Which councilmembers represent transit-rich areas?
2. **High-Impact Stations**: Where would TOC affect most daily riders?
3. **Multi-Line Hubs**: Emphasize stations where TOC unlocks multi-destination access
4. **Development Readiness**: DVRPC scores show market conditions
5. **Equity Considerations**: Districts with limited/no rapid transit

## Key Findings & Recommendations

### BSL/MFL as Core (Not Regional Rail)
Per user clarification:
- ✅ **Include**: BSL, MFL, trolleys (subway-surface + Route 15)
- ❌ **Likely exclude**: Regional Rail (may not be in final TOC legislation)
- **Rationale**: Urban frequent-service transit vs. commuter rail

### DVRPC Report Context
- DVRPC **excluded Center City stations** from detailed analysis
- **Not because they're poor fits** - assumed obvious inclusions
- Need to add Center City stations explicitly to recommendations

### Multi-Line Connectivity Priority
Stations serving multiple lines should be **first-tier priorities**:
- Greater access to jobs and destinations
- Higher development impact
- Better SEPTA fiscal health (Niskanen Center argument)

### Market Conditions
DVRPC Future Potential scores show:
- **High**: West Philly corridors (46th St, Girard, Ellsworth-Federal)
- **Moderate**: North Broad corridor, MFL eastern segments
- **Development Activity**: Recent multifamily construction concentrated in high-score areas

## Running the Analysis

### Option 1: Full Python Analysis (Requires Dependencies)
```bash
# Install requirements
pip install -r requirements.txt

# Run comprehensive analysis
python scripts/comprehensive_tod_analysis.py
```

**Outputs**:
- Stations by City Council district
- Multi-line transfer station identification
- Enhanced TOD scores (DVRPC + connectivity)
- Interactive maps
- Political briefing CSVs

### Option 2: Jupyter Notebook (Interactive)
```bash
jupyter notebook notebooks/toc_political_analysis.ipynb
```

### Option 3: Quick Summary (No Installation)
```bash
python scripts/quick_summary.py
```

## Data Sources & References

1. **DVRPC TOD Evaluation**: https://dvrpc.github.io/TOD/
2. **"Building on Our Strengths" Report**: https://www.dvrpc.org/products/16036
3. **OpenDataPhilly - SEPTA Stations**: https://opendataphilly.org/datasets/septa-routes-stops-locations/
4. **OpenDataPhilly - Council Districts**: https://opendataphilly.org/datasets/city-council-districts/
5. **OpenDataPhilly - Ridership**: https://opendataphilly.org/datasets/septa-ridership-statistics/
6. **Niskanen Center - SEPTA Fiscal Analysis**: https://www.niskanencenter.org/philadelphia-regional-rail-population-density-and-septas-fiscal-crisis/

## Next Steps

1. ✅ **Extract trolley stops** - COMPLETE
2. ✅ **Download DVRPC TOD scores** - COMPLETE
3. ⏳ **Run multi-line connectivity analysis** - Requires Python environment
4. ⏳ **Spatial join with City Council districts** - Requires Python environment
5. ⏳ **Generate political briefing materials** - Requires analysis completion
6. 🔲 **Acquire BSL/MFL/trolley ridership data** (separate from Regional Rail)
7. 🔲 **Add Center City stations explicitly** (noted as DVRPC exclusions)
8. 🔲 **Cross-reference with recent development permits** (market validation)

## File Structure

```
toc_analysis-/
├── data/
│   ├── raw/
│   │   ├── septa_all_transit_stops.geojson     # All SEPTA stops (6,753)
│   │   ├── septa_regional_rail_stations.geojson # Regional Rail only (49)
│   │   ├── city_council_districts.geojson       # 10 districts
│   │   ├── septa_ridership_rail.csv             # Ridership data
│   │   ├── dvrpc_tod_scores.js                  # DVRPC TOD data (162 stations)
│   │   └── dvrpc_rail_lines.js                  # DVRPC rail line geometries
│   └── processed/
│       ├── dvrpc_bsl_mfl_trolley.geojson        # 30 BSL/MFL stations + scores
│       └── philadelphia_trolley_stops.geojson    # 551 trolley stops
├── notebooks/
│   └── toc_political_analysis.ipynb             # Main analysis notebook
├── scripts/
│   ├── parse_dvrpc_data.py                      # Extract DVRPC BSL/MFL data
│   ├── comprehensive_tod_analysis.py            # Full analysis (multi-line + districts)
│   └── quick_summary.py                         # Command-line summary
├── outputs/                                      # Generated maps, charts, CSVs
├── requirements.txt                              # Python dependencies
└── README.md                                     # Project documentation
```

## Contact & Questions

For questions about methodology or data sources, refer to:
- **DVRPC**: Andrew Svekla (asvekla@dvrpc.org, 215-238-2810)
- **SEPTA Open Data**: planning@septa.org
