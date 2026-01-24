# Replication Scripts

Open-source Python 3 implementation of Sapena et al. (2020) urban metrics methodology.

**Reference:** Sapena, M., Ruiz, L., & Taubenböck, H. (2020). Analyzing Links between Spatio-Temporal Metrics of Built-Up Areas and Socio-Economic Indicators on a Semi-Global Scale. *ISPRS International Journal of Geo-Information*, 9(7), 436. https://doi.org/10.3390/ijgi9070436

---

## Scripts Overview

| Script | Description | Input Data | Output |
|--------|-------------|------------|--------|
| `step1_spatial_metrics_2000.py` | Spatial metrics for T1 (2000) | GHSL | Shapefile + CSV |
| `step2_spatial_metrics_2014.py` | Spatial metrics for T2 (2014) | GHSL (requires Step 1) | Shapefile + CSV |
| `step3_road_network.py` | Road network density | OpenStreetMap | Shapefile + CSV |
| `step4_land_cover.py` | Land cover change metrics | ESA CCI-LC | Shapefile + CSV |
| `step5_multitemporal_metrics.py` | Multi-temporal urban growth | Steps 1, 2, 3 outputs | Shapefile + CSV |

---

## Common Command-Line Arguments

All scripts support the following filtering options:

```bash
--country, -c    Filter FUAs by country code prefix (e.g., US, AUS, EUR)
                 Can specify multiple comma-separated codes (e.g., US,CA)

--fua, -f        Process specific FUA code(s), comma-separated (e.g., USA01,USA02)
```

---

## Step 1: Spatial Metrics 2000 (T1)

Extracts spatial metrics from the Global Human Settlement Layer (GHSL) for year 2000.

**Metrics calculated:**
- `UA_T1` - Urban Area (km²)
- `C_T1` - Compactness
- `DI_T1` - Dispersion Index
- `AWSD_T1` - Area-Weighted Standard Distance
- `DU_T1` - Urban Density (%)
- `L_UC_T1` - Largest Urban Core (%)
- `C_UC_T1` - Urban Core Compactness
- `SL_UC_T1` - Second Largest Urban Core (%)
- `ER_UC_T1` - Elongation Ratio

**Usage:**
```bash
# All FUAs
python3 step1_spatial_metrics_2000.py

# US FUAs only
python3 step1_spatial_metrics_2000.py --country US

# Specific FUAs
python3 step1_spatial_metrics_2000.py --fua USA46,USA146,USA37
```

**Output:**
- `outputs/Boundaries_SM_2000.shp` - Shapefile with metrics
- `outputs/Boundaries_SM_2000.csv` - CSV with metrics (no geometry)

**Required data:**
- GHSL: `data/GHS_BUILT_LDSMT_GLOBE_R2018A_3857_30_V2_0/`

---

## Step 2: Spatial Metrics 2014 (T2)

Extracts spatial metrics from GHSL for year 2014. Requires Step 1 to be run first.

**Metrics calculated:**
- Same as Step 1 but with `_T2` suffix

**Usage:**
```bash
# All FUAs (requires Step 1 outputs)
python3 step2_spatial_metrics_2014.py

# US FUAs only
python3 step2_spatial_metrics_2014.py --country US

# Specific FUAs
python3 step2_spatial_metrics_2014.py --fua USA46,USA146,USA37
```

**Output:**
- `outputs/Boundaries_SM_2014.shp`
- `outputs/Boundaries_SM_2014.csv`

**Required:**
- Step 1 must be run first (uses clipped rasters from `outputs/Ras_3857/`)

---

## Step 3: Road Network Density

Calculates road network density from OpenStreetMap data.

**Metrics calculated:**
- `D_road` - Road density (km/km²)

**Usage:**
```bash
# All FUAs
python3 step3_road_network.py

# US FUAs only
python3 step3_road_network.py --country US
```

**Output:**
- `outputs/Boundaries_ROADs.shp`
- `outputs/Boundaries_ROADs.csv`

**Required data:**
- OSM road shapefiles in `data/external/OSM/`

---

## Step 4: Land Cover Metrics

Processes ESA CCI Land Cover data and calculates land cover change between 2000 and 2014.

**Metrics calculated:**
- `D_LC1_T1`, `D_LC1_T2`, `CP_LC1` - Agriculture
- `D_LC2_T1`, `D_LC2_T2`, `CP_LC2` - Forest/High vegetation
- `D_LC3_T1`, `D_LC3_T2`, `CP_LC3` - Shrub/Grass/Low vegetation
- `D_LC4_T1`, `D_LC4_T2`, `CP_LC4` - Urban
- `D_LC5_T1`, `D_LC5_T2`, `CP_LC5` - Bare/Sparse
- `D_LC6_T1`, `D_LC6_T2`, `CP_LC6` - Water
- `D_LC7_T1`, `D_LC7_T2`, `CP_LC7` - Snow/Ice

Where:
- `D_LCx_T1` = Density at T1 (2000)
- `D_LCx_T2` = Density at T2 (2014)
- `CP_LCx` = Change percentage

**Usage:**
```bash
# All FUAs
python3 step4_land_cover.py

# US FUAs only
python3 step4_land_cover.py --country US

# Specific FUAs
python3 step4_land_cover.py --fua USA46,USA146
```

**Output:**
- `outputs/Boundaries_CCI_LC.shp`
- `outputs/Boundaries_CCI_LC.csv`

**Required data (auto-detected):**
- Option 1: Multi-temporal file `data/external/CCI_LC/ESACCI-LC-L4-LCCS-Map-300m-P1Y-1992_2015-v2.0.7.tif`
- Option 2: Single-year files `ESACCI-LC-L4-LCCS-Map-300m-P1Y-2000-v2.0.7.tif` and `...-2014-...tif`

---

## Step 5: Multi-Temporal Metrics

Calculates urban growth metrics by comparing T1 (2000) and T2 (2014) built-up areas.

**Metrics calculated:**
- `UCR` - Urban Change Rate (%)
- `AWMEI` - Area-Weighted Mean Expansion Index
- `AWMAI` - Area-Weighted Mean Accessibility Index

**Growth type classification (based on Landscape Expansion Index):**
- LEI = 0: Outlying (no shared boundary with existing urban)
- LEI 0-0.5: Edge-Expansive
- LEI > 0.5: Infilling

**Usage:**
```bash
# All FUAs (requires Steps 1, 2, 3)
python3 step5_multitemporal_metrics.py

# US FUAs only
python3 step5_multitemporal_metrics.py --country US

# Specific FUAs
python3 step5_multitemporal_metrics.py --fua USA46,USA146
```

**Output:**
- `outputs/Boundaries_MT_2000_2014.shp`
- `outputs/Boundaries_MT_2000_2014.csv`
- `outputs/Vec_00_14/BUILT_{FUA}_00_14.shp` - Change maps for each FUA

**Required:**
- Step 1 outputs (`outputs/Vec_00/`)
- Step 2 outputs (`outputs/Vec_14/`)
- Step 3 outputs (`outputs/ROADs_PJ/`)

---

## Recommended Workflow

Run scripts in order, as later steps depend on earlier outputs:

```bash
cd /path/to/eja-home/replication/scripts

# Step 1: Spatial metrics T1 (2000)
python3 -u step1_spatial_metrics_2000.py --country US

# Step 2: Spatial metrics T2 (2014) - requires Step 1
python3 -u step2_spatial_metrics_2014.py --country US

# Step 3: Road network density
python3 -u step3_road_network.py --country US

# Step 4: Land cover metrics (independent of Steps 1-3)
python3 -u step4_land_cover.py --country US

# Step 5: Multi-temporal metrics - requires Steps 1, 2, 3
python3 -u step5_multitemporal_metrics.py --country US
```

**Tip:** Use `-u` flag for unbuffered output to see real-time progress.

---

## Output Directory Structure

```
outputs/
├── Boundaries_SM_2000.shp/.csv     # Step 1 results
├── Boundaries_SM_2014.shp/.csv     # Step 2 results
├── Boundaries_ROADs.shp/.csv       # Step 3 results
├── Boundaries_CCI_LC.shp/.csv      # Step 4 results
├── Boundaries_MT_2000_2014.shp/.csv # Step 5 results
├── Vec_00/                         # Step 1 vectorized built-up (UTM)
├── Vec_14/                         # Step 2 vectorized built-up (UTM)
├── Vec_00_14/                      # Step 5 change maps
├── Ras_00/                         # Step 1 reclassified rasters
├── Ras_14/                         # Step 2 reclassified rasters
├── Ras_3857/                       # Clipped GHSL rasters
├── FUAs/                           # FUA boundaries in UTM
├── ROADs_PJ/                       # Projected road networks
├── CCI_4326/                       # Clipped CCI rasters
└── Vec_CCI/                        # Vectorized land cover
```

---

## Validation

See `../VALIDATION_REPORT.md` for validation results comparing this implementation against Sapena et al. (2020) original results.

**Summary:** All metrics show >99% correlation with original values.
