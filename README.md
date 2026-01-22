# Sapena et al. (2020) Replication

Open-source Python 3 replication of the spatio-temporal urban growth analysis from Sapena et al. (2020).

Sapena et al. (2020) conducted the original analysis using Python 2.x with ArcMap and the IndiFrag toolkit. The original codes and data are available at https://doi.org/10.6084/m9.figshare.12554531.v1.

## Key Differences from Original

| Original (Sapena) | This Replication |
|-------------------|------------------|
| Python 2.7 | Python 3.9+ |
| ArcPy / ArcGIS | geopandas, rasterio, shapely |
| Windows only | Cross-platform (macOS, Linux, Windows) |
| IndiFrag toolkit | Custom implementations |

## Project Structure

```
eja-home/
├── original/                 # Sapena's original files (reference)
│   ├── Codes_spatio_temporal_analysis/
│   ├── Code_statistic_analysis/
│   └── paper.pdf
│
├── replication/              # Open-source Python 3 replication
│   ├── scripts/              # Python scripts
│   │   ├── utils.py
│   │   ├── step1_spatial_metrics_2000.py
│   │   ├── step2_spatial_metrics_2014.py
│   │   ├── step3_road_network.py
│   │   ├── step4_land_cover.py
│   │   ├── step5_multitemporal_metrics.py
│   │   ├── validate_outputs.py
│   │   └── requirements.txt
│   └── outputs/
│
├── data/                     # Data files
│   ├── boundaries/           # FUA boundary shapefiles
│   ├── utm_zones/            # UTM zone shapefiles
│   └── preprocessed/         # Sapena's expected results (CSVs)
│
└── data_external/            # Large files (not in git)
    ├── GHS_BUILT_LDSMT_GLOBE_R2018A_3857_30_V2_0/
    ├── GRIP/
    └── CCI_LC/
```

## Setup

### 1. Install Python dependencies

```bash
cd eja-home/replication/scripts
pip3 install -r requirements.txt
```

### 2. Download external data

**GHSL (Global Human Settlement Layer)** - Required for Steps 1 & 2
- Download: https://data.jrc.ec.europa.eu/dataset/jrc-ghsl-10007
- Extract to: `data_external/GHS_BUILT_LDSMT_GLOBE_R2018A_3857_30_V2_0/`

**GRIP (Road Network)** - Required for Step 3
- Download: https://www.globio.info/download-grip-dataset
- Extract to: `data_external/GRIP/`

**CCI Land Cover** - Required for Step 4
- Download: ftp://anon-ftp.ceda.ac.uk/neodc/esacci/
- Place in: `data_external/CCI_LC/`

## Running the Analysis

Execute scripts in order:

```bash
cd eja-home/replication/scripts

python3 step1_spatial_metrics_2000.py
python3 step2_spatial_metrics_2014.py
python3 step3_road_network.py
python3 step4_land_cover.py
python3 step5_multitemporal_metrics.py

# Validate outputs against Sapena's results
python3 validate_outputs.py
```

## Metrics Computed

**Spatial Metrics (T1=2000, T2=2014):**
- UA: Urban Area
- DU: Urban Density
- C: Compactness
- DI: Dispersion Index
- AWSD: Area-Weighted Standard Distance
- Urban Core metrics: L_UC, SL_UC, C_UC, ER_UC

**Multi-Temporal Metrics:**
- UCR: Urban Change Rate
- AWMEI: Area-Weighted Mean Expansion Index
- AWMAI: Area-Weighted Mean Accessibility Index
- LEI: Landscape Expansion Index (growth type classification)

**Additional:**
- D_road: Road network density (km/km²)
- CP_LC1-4: Land cover change percentages

## Reference

Sapena, Marta, Luis Ruiz, and Hannes Taubenböck. "Analyzing Links between Spatio-Temporal Metrics of Built-Up Areas and Socio-Economic Indicators on a Semi-Global Scale." ISPRS International Journal of Geo-Information 9, no. 7 (July 11, 2020): 436. https://doi.org/10.3390/ijgi9070436.
