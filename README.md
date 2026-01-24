# Sapena et al. (2020) Replication

Open-source Python 3 replication of the spatio-temporal urban growth analysis methodology from Sapena et al. (2020).

**Reference:**
Sapena, M., Ruiz, L.A., & Taubenböck, H. (2020). Analyzing Links between Spatio-Temporal Metrics of Built-Up Areas and Socio-Economic Indicators on a Semi-Global Scale. *ISPRS International Journal of Geo-Information*, 9(7), 436. https://doi.org/10.3390/ijgi9070436

---

## Validation

This replication achieves **>99.99% correlation** with the original results across all metrics. See [VALIDATION_REPORT.md](VALIDATION_REPORT.md) for detailed validation results.

---

## Key Differences from Original

| Original (Sapena) | This Replication |
|-------------------|------------------|
| Python 2.7 | Python 3.9+ |
| ArcPy / ArcGIS | geopandas, rasterio, shapely |
| Windows only | Cross-platform (macOS, Linux, Windows) |
| IndiFrag toolkit | Open-source implementations |

---

## Repository Structure

```
.
├── README.md                    # This file
├── VALIDATION_REPORT.md         # Validation results (>99.99% accuracy)
│
├── scripts/                     # Python 3 replication scripts
│   ├── requirements.txt         # Python dependencies
│   ├── README.md                # Detailed script documentation
│   ├── utils.py                 # Shared utility functions
│   ├── step1_spatial_metrics_2000.py
│   ├── step2_spatial_metrics_2014.py
│   ├── step3_road_network.py
│   ├── step4_land_cover.py
│   ├── step5_multitemporal_metrics.py
│   └── validate_outputs.py      # Compare outputs vs original
│
├── data/                        # Reference data (included in repo)
│   ├── boundaries/              # FUA boundary shapefiles
│   ├── utm_zones/               # UTM zone reference
│   └── preprocessed/            # Sapena's original results (for validation)
│
├── original/                    # Sapena's original code (reference)
│   ├── Code_statistic_analysis/ # Original Python 2.7 scripts
│   ├── Codes_spatio_temporal_analysis/
│   └── README.docx
│
└── paper/                       # Publication materials
    ├── Sapena_et_al_2020.pdf    # Full paper
    └── ijgi-09-00436-s001.pdf   # Supplementary information
```

---

## Quick Start

### 1. Install dependencies

```bash
cd scripts
pip install -r requirements.txt
```

### 2. Download external data

Create a `data_external/` folder and download the following datasets:

**GHSL (Global Human Settlement Layer)** - Required for Steps 1 & 2
- Download: https://data.jrc.ec.europa.eu/dataset/jrc-ghsl-10007
- File: `GHS_BUILT_LDSMT_GLOBE_R2018A_3857_30_V2_0.zip`
- Extract to: `data_external/GHS_BUILT_LDSMT_GLOBE_R2018A_3857_30_V2_0/`

**GRIP (Global Roads)** - Required for Step 3
- Download: https://www.globio.info/download-grip-dataset
- Extract to: `data_external/GRIP/`

**ESA CCI Land Cover** - Required for Step 4
- Download: ftp://anon-ftp.ceda.ac.uk/neodc/esacci/land_cover/
- File: `ESACCI-LC-L4-LCCS-Map-300m-P1Y-1992_2015-v2.0.7.tif`
- Place in: `data_external/CCI_LC/`

### 3. Run the analysis

Execute scripts in order:

```bash
cd scripts

# Step 1: Spatial metrics for year 2000
python3 -u step1_spatial_metrics_2000.py --country US

# Step 2: Spatial metrics for year 2014 (requires Step 1)
python3 -u step2_spatial_metrics_2014.py --country US

# Step 3: Road network density
python3 -u step3_road_network.py --country US

# Step 4: Land cover change metrics
python3 -u step4_land_cover.py --country US

# Step 5: Multi-temporal urban growth (requires Steps 1-3)
python3 -u step5_multitemporal_metrics.py --country US

# Validate outputs against Sapena's results
python3 validate_outputs.py
```

Use `-u` for unbuffered output to see real-time progress.

---

## Metrics Computed

### Spatial Metrics (T1=2000, T2=2014)

| Metric | Description |
|--------|-------------|
| UA | Urban Area (km²) |
| DU | Urban Density (%) |
| C | Compactness (0-1) |
| DI | Dispersion Index |
| AWSD | Area-Weighted Standard Distance (km) |
| L_UC | Largest Urban Core (% of FUA) |
| SL_UC | Second Largest Urban Core (%) |
| C_UC | Urban Core Compactness |
| ER_UC | Elongation Ratio |

### Multi-Temporal Metrics

| Metric | Description |
|--------|-------------|
| UCR | Urban Change Rate (% change 2000-2014) |
| AWMEI | Area-Weighted Mean Expansion Index |
| AWMAI | Area-Weighted Mean Accessibility Index |
| LEI | Landscape Expansion Index (0=outlying, >0.5=infilling) |

### Land Cover Change

| Metric | Land Cover Class |
|--------|-----------------|
| CP_LC1 | Agriculture |
| CP_LC2 | Forest/High vegetation |
| CP_LC3 | Shrub/Grass/Low vegetation |
| CP_LC4 | Urban |

### Infrastructure

| Metric | Description |
|--------|-------------|
| D_road | Road network density (km/km²) |

---

## Command-Line Options

All scripts support filtering:

```bash
--country, -c    Filter by country code (e.g., US, AUS, EUR)
--fua, -f        Process specific FUA codes (e.g., USA01,USA02)
--limit, -l      Limit number of FUAs for testing
```

---

## License

This replication is provided for academic and research purposes.

**Original data sources:**
- GHSL: European Commission, Joint Research Centre (JRC)
- GRIP: PBL Netherlands Environmental Assessment Agency
- CCI Land Cover: European Space Agency (ESA)
