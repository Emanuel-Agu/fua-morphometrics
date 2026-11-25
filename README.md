# fua-morphometrics

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19635759.svg)](https://doi.org/10.5281/zenodo.19635759)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python ≥3.11](https://img.shields.io/badge/python-%E2%89%A53.11-blue.svg)](pyproject.toml)

Open-source Python 3 **replication and extension** of the spatio-temporal urban morphometrics pipeline from Sapena, Ruiz & Taubenböck (2020). Computes 14+ metrics of urban form, growth, and land-cover change for Functional Urban Areas (FUAs) across 32 countries. Reproduces the original analysis on GHSL-B R2018A and extends it to the current GHSL-B R2023A release.

**Upstream paper:**
Sapena, M., Ruiz, L. A., & Taubenböck, H. (2020). Analyzing Links between Spatio-Temporal Metrics of Built-Up Areas and Socio-Economic Indicators on a Semi-Global Scale. *ISPRS International Journal of Geo-Information*, 9(7), 436. [doi:10.3390/ijgi9070436](https://doi.org/10.3390/ijgi9070436)

---

## Credit: what comes from the original study and what is new here

`fua-morphometrics` is replication software. **The method and the analysis pipeline belong to Sapena, Ruiz & Taubenböck (2020)**: the choice of metrics, the Functional Urban Area sample, the data sources and the step 1–5 workflow are theirs. Their spatial metrics are computed with the IndiFrag toolbox (Sapena & Ruiz 2015, [doi:10.4995/raet.2015.3476](https://doi.org/10.4995/raet.2015.3476)).

- **New here:** the Python 3 code in `scripts/`, written by the author to reproduce that pipeline with open-source libraries (geopandas, rasterio, shapely) instead of Python 2.7 and ArcPy, and the extension to GHSL-B R2023A. It contains no code from the original scripts; a line-by-line comparison (November 2026) found no shared lines.
- **Not ours:** `original/` holds the original authors' code and `data/preprocessed/` their published results, included for reference and validation. They are not covered by this repository's MIT license.
- **Development.** The code was written by the author with the assistance of Anthropic's Claude (Claude Opus 4.5 and 4.7, through Claude Code), as recorded in the commit history; the author reviewed and validated all code.

---

## Validation

This replication achieves **>99.99% correlation** with the original results across all metrics. See [VALIDATION_REPORT.md](VALIDATION_REPORT.md) for detailed validation results.

---

## Key Differences from Original

| Original (Sapena) | This Replication |
|-------------------|------------------|
| Python 2.7 | Python 3.11+ |
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
└── original/                    # Sapena's original code (reference)
    ├── Code_statistic_analysis/ # Original Python 2.7 scripts
    ├── Codes_spatio_temporal_analysis/
    └── README.docx
```

The paper PDF and supplementary material are not redistributed here — follow the [upstream DOI](https://doi.org/10.3390/ijgi9070436) to retrieve them from the publisher (open access, CC-BY).

---

## Quick Start

### 1. Install dependencies

Using [`uv`](https://docs.astral.sh/uv/) (recommended):

```bash
git clone https://github.com/Emanuel-Agu/fua-morphometrics.git
cd fua-morphometrics
uv sync --dev
```

Run the test suite to verify the environment:

```bash
uv run pytest
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

Execute scripts in order from the repository root (outputs are written to `outputs/`):

```bash
# Step 1: Spatial metrics for year 2000
uv run python -u scripts/step1_spatial_metrics_2000.py --country US

# Step 2: Spatial metrics for year 2014 (requires Step 1)
uv run python -u scripts/step2_spatial_metrics_2014.py --country US

# Step 3: Road network density
uv run python -u scripts/step3_road_network.py --country US

# Step 4: Land cover change metrics
uv run python -u scripts/step4_land_cover.py --country US

# Step 5: Multi-temporal urban growth (requires Steps 1-3)
uv run python -u scripts/step5_multitemporal_metrics.py --country US

# Validate outputs against Sapena's results
uv run python scripts/validate_outputs.py
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

## Citing

If you use this software in academic work, please cite it (see [`CITATION.cff`](CITATION.cff)) along with the original upstream paper:

> Sapena, M., Ruiz, L. A., & Taubenböck, H. (2020). Analyzing Links between Spatio-Temporal Metrics of Built-Up Areas and Socio-Economic Indicators on a Semi-Global Scale. *ISPRS International Journal of Geo-Information*, 9(7), 436. [doi:10.3390/ijgi9070436](https://doi.org/10.3390/ijgi9070436)

## License

Code in this repository is released under the **MIT License** — see [`LICENSE`](LICENSE).

This is an independent open-source replication and is not affiliated with or endorsed by the original authors.

**Underlying data sources (cite separately if used):**
- GHSL: European Commission, Joint Research Centre (JRC)
- GRIP: PBL Netherlands Environmental Assessment Agency
- CCI Land Cover: European Space Agency (ESA)
