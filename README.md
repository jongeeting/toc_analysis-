# Philadelphia Transit-Oriented Communities (TOC) Political Analysis

Analysis of Philadelphia transit stations and development potential for City Council engagement on TOC legislation.

## Project Goals

1. **Stations per District**: Count and map transit stations by City Council district for political targeting
2. **Ridership Analysis**: Identify high-ridership stations where TOC impact would be greatest
3. **Market Conditions**: Assess development likelihood based on market indicators

## Data Sources

- **SEPTA Transit Stations**: Station locations (Broad Street Line, Market-Frankford Line, Regional Rail)
- **SEPTA Ridership**: Average weekday boardings by station
- **City Council Districts**: Philadelphia City Council district boundaries
- **Market Data**: Zoning, property values, recent permits (where available)

## Directory Structure

```
.
├── data/
│   ├── raw/          # Original source data
│   └── processed/    # Cleaned and merged datasets
├── notebooks/        # Jupyter analysis notebooks
├── outputs/          # Maps, charts, summary tables
├── scripts/          # Python utility scripts
└── requirements.txt  # Python dependencies
```

## Setup

```bash
pip install -r requirements.txt
```

## Analysis Outputs

- Transit stations per City Council district (table + map)
- High ridership stations highlighted
- Development likelihood scores by station area
- Summary statistics for political briefings
