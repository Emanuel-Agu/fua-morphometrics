# Reference & Validation Data

This directory holds reference spatial layers and published benchmark outputs
used to run and validate the replication pipeline against Sapena, Ruiz &
Taubenböck (2020).

## Contents

- `boundaries/` — Functional Urban Area (FUA) boundary shapefiles
  (`Boundaries_3857.shp`, `Boundaries_4326.shp`), prepared from EU–OECD FUA
  definitions in Sapena et al. (2020).
- `utm_zones/` — UTM zone reference shapefiles (`UTM_Zone_EPSG_3857.shp`,
  `UTM_Zone_EPSG_4326.shp`) used to match the original EPSG selection.
- `preprocessed/` — Published metric tables from Sapena et al. (2020) converted
  to CSV for validation (`spatial_metrics.csv`, `Spatiotemp_metrics.csv`,
  `Roads.csv`, `LandCover_CH.csv`, `Pugi.csv`, `LC_dens.csv`, `names_FUAs.csv`).

## Attribution & License

These files originate from the supplementary data package of Sapena, Ruiz &
Taubenböck (2020) and its underlying institutional sources (EU–OECD). They are
kept here solely for reproducibility and validation and are **not** covered by
this repository's MIT license.

The original Python 2.7 / ArcPy and R scripts are not redistributed in this
repository; download them directly from the original authors' Figshare deposit:

- **Original code & data archive:** [doi:10.6084/m9.figshare.12554531](https://doi.org/10.6084/m9.figshare.12554531)
- **Original article:** Sapena, M., Ruiz, L. A., & Taubenböck, H. (2020).
  Analyzing Links between Spatio-Temporal Metrics of Built-Up Areas and
  Socio-Economic Indicators on a Semi-Global Scale. *ISPRS International
  Journal of Geo-Information*, 9(7), 436.
  [doi:10.3390/ijgi9070436](https://doi.org/10.3390/ijgi9070436)
