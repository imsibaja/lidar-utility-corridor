# LiDAR Utility Corridor — Vegetation Height Exceedance Mapping

![Python](https://img.shields.io/badge/python-3.11-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![Last Updated](https://img.shields.io/badge/last%20updated-April%202026-lightgrey)

---

## Project Summary

This project builds a Python pipeline for detecting vegetation that exceeds clearance height thresholds within utility transmission line corridors, using USGS 3DEP LiDAR point cloud data as the primary input. A Canopy Height Model (CHM) is derived from the point cloud via PDAL ground classification and height normalization, rasterized to a 1m GeoTIFF, and clipped to a buffered corridor geometry. The final output is a corridor exceedance map identifying trees above a defined height threshold, suitable for utility vegetation management review. The intended audience is utility-sector hiring reviewers and remote sensing professionals evaluating applied geospatial workflows.

---

## Background and Motivation

### What LiDAR is and why it matters for utility vegetation management

LiDAR (Light Detection and Ranging) is an active remote sensing technology that emits laser pulses and measures the return time to estimate the 3D position of surfaces. Airborne LiDAR produces dense point clouds representing the terrain, vegetation, and structures below the aircraft. For utility vegetation management, LiDAR provides a direct measurement of canopy height that passive optical sensors cannot match — it penetrates partial canopy cover, distinguishes ground from vegetation, and operates independently of solar illumination.

Transmission line outages caused by vegetation contact are among the most common and preventable causes of grid failures. NERC FAC-003-4 (Transmission Vegetation Management) establishes minimum clearance distances between conductors and vegetation. LiDAR enables systematic, spatially explicit identification of trees approaching or exceeding those clearance distances across hundreds of miles of corridor.

### What a Canopy Height Model is and how it is derived

A Canopy Height Model (CHM) is a raster layer where each pixel value represents the estimated height of vegetation above the ground surface. It is derived by subtracting the Digital Terrain Model (DTM) from the Digital Surface Model (DSM):

```
CHM = DSM − DTM
```

The DSM captures the elevation of the highest return per pixel — the top of the canopy in vegetated areas. The DTM captures only ground-classified returns, representing the bare-earth surface. The difference isolates the vertical extent of above-ground objects. For this to be accurate, ground classification must be performed first (typically using PDAL's CSF or PMF filter) before the DTM is derived.

### Why utility companies care about tree height thresholds

Trees growing into or near transmission line rights-of-way create flashover risk, conductor contact hazards, and regulatory compliance obligations. Utility vegetation management programs use height thresholds — defined relative to conductor height and line voltage — to trigger inspection, trimming, or removal. An accurate CHM within a buffered corridor allows systematic prioritization: instead of walking every mile of line, crews can be directed to specific segments with confirmed exceedances.

### A note on learning context

This project represents my first systematic engagement with LiDAR point cloud processing. Methods are documented explicitly so the workflow is reproducible and legible to reviewers. Where parameter choices are uncertain or not yet validated, that uncertainty is noted directly in the code and this document rather than obscured.

---

## Study Area

**TBD** — The target area is a California utility corridor with USGS 3DEP QL1 or QL2 LiDAR coverage.

Candidate regions under consideration:
- Ventura County (SCE transmission corridors, mixed chaparral/oak)
- Santa Barbara County foothills (high fire-weather exposure, complex terrain)
- San Bernardino foothills (high tree density, documented outage history)

To select a specific tile, use the [OpenTopography](https://opentopography.org) map interface or the [USGS National Map Availability Viewer](https://apps.nationalmap.gov/viewer/) to confirm QL1/QL2 coverage for the area of interest before downloading. A 1km² tile is recommended to keep file sizes manageable during initial development.

---

## Data Sources

| Dataset | Source | Access | Format | Notes |
|---|---|---|---|---|
| USGS 3DEP LiDAR Point Cloud | OpenTopography (opentopography.org) | Free, no account required | .laz | QL1 or QL2 required; select 1km² tile to manage file size |
| CA Transmission Lines | CA Energy Commission GIS | Free, public | Shapefile | Used to define corridor centerline |
| NLCD 2021 or CALVEG | USGS / USFS | Free, public | GeoTIFF | Optional vegetation context layer; NLCD 2021 also used for accuracy assessment |

### Data Acquisition

#### USGS 3DEP LiDAR Quality Levels

USGS 3DEP LiDAR is distributed at three quality levels. **QL3 is insufficient for 1m CHM derivation** and must not be used:

- **QL1** (Quality Level 1): ≤0.35 pts/m² ground density, typically 8+ pts/m² total density. Suitable for high-resolution CHM at 0.5–1m.
- **QL2** (Quality Level 2): ≤0.71 pts/m² ground density, typically 2+ pts/m² total density. Adequate for 1m CHM with careful parameter selection.
- **QL3**: Insufficient ground point density for reliable 1m CHM. Not suitable for this workflow.

The target tile and region of interest are TBD. Select a tile using the [USGS National Map Availability Viewer](https://apps.nationalmap.gov/viewer/) to confirm quality level before download.

#### Recommended Download Methods

Two options are available for obtaining 3DEP LiDAR tiles:

- **OpenTopography REST API** — preferred for programmatic access. Enables reproducible, scripted tile selection and download. See [opentopography.org](https://opentopography.org) for API documentation.
- **USGS National Map Downloader** ([tnmaccess.usgs.gov](https://tnmaccess.usgs.gov)) — web interface for manual tile selection and direct download. Useful for initial tile identification.

#### CRS and Vertical Datum

USGS 3DEP LiDAR is distributed in state plane or UTM projections with **NAVD88** as the vertical datum. Before processing:

1. **Verify the horizontal CRS** of the downloaded tile (check the .laz file header or accompanying metadata). Reproject to a consistent projected CRS before processing. For Southern California, UTM Zone 11N (EPSG:26911 / NAD83) is a common target.
2. **Confirm the vertical datum is NAVD88** before any elevation-dependent analysis. Mixing vertical datums will produce erroneous CHM values.

All spatial operations (buffering, clipping, rasterization) require a projected CRS with linear units of meters. A geographic CRS (degrees) will produce incorrect distances and must not be used.

---

## Methods Overview

The pipeline is executed in the following order, corresponding to the four notebooks in `notebooks/`:

1. **Download LiDAR tile** — Obtain a single QL1/QL2 `.laz` tile from OpenTopography for the study corridor. Confirm CRS and point density before proceeding.

2. **Inspect point cloud structure** — Use `laspy` to report total return count, ASPRS classification code distribution, bounding box extent, and estimated point density (pts/m²). Validate that density supports the target CHM resolution.

3. **Run PDAL pipeline** — Execute `pipeline/pdal_pipeline.json` via `src.pdal_runner`. This pipeline applies:
   - **Ground classification** using `filters.csf` (Cloth Simulation Filter) — assigns ASPRS class 2 to ground returns
   - **Height normalization** using `filters.hag_nn` — adds `HeightAboveGround` dimension to each point
   - Output: normalized `.laz` with ground classification and HAG dimension

4. **Rasterize to CHM** — Using the normalized point cloud:
   - Build DSM from max return height per pixel
   - Build DTM from ground-classified returns only
   - Subtract DTM from DSM to produce CHM GeoTIFF at target resolution (1m)

5. **Load corridor centerline and buffer** — Load the CA transmission line shapefile with `geopandas`. Buffer by the corridor clearance distance (default: ~15m / 50ft). The buffer distance should be grounded in **NERC FAC-003-4** (Transmission Vegetation Management) clearance requirements for the applicable voltage class. FAC-003-4 Table 1 defines minimum clearance distances by voltage class. The 50ft (~15m) default reflects typical 200–500kV right-of-way standards; users must verify the voltage class of the study corridor and consult FAC-003-4 before applying results operationally.

6. **Clip CHM to corridor buffer** — Mask the CHM raster to the corridor buffer polygon using `rioxarray`. Output: `outputs/rasters/chm_clipped.tif`.

7. **Apply height threshold** — Binary threshold the clipped CHM to identify pixels exceeding the clearance height (default: ~4.57m / 15ft). Vectorize exceedance zones into polygons with height attributes. Output: `outputs/vector/flagged_trees.gpkg`.

8. **Generate summary statistics** — Aggregate flagged tree count and mean height by corridor segment. Output: `outputs/tables/flagged_tree_summary.csv`.

---

## Repository Structure

```
lidar-utility-corridor/
├── .gitignore                          # Excludes .laz/.las files, raw/processed data, outputs
├── README.md                           # This file
├── environment.yml                     # Conda environment specification
│
├── pipeline/
│   └── pdal_pipeline.json              # PDAL ground classification + HAG normalization pipeline
│
├── src/                                # Python source modules (skeleton functions only)
│   ├── __init__.py
│   ├── data_utils.py                   # load_laz, inspect_point_cloud, validate_crs
│   ├── pdal_runner.py                  # run_pipeline, check_pdal_available
│   ├── chm.py                          # rasterize_to_dsm, rasterize_to_dtm, compute_chm
│   └── corridor.py                     # load_corridor_centerline, buffer_corridor,
│                                       # clip_chm_to_corridor, threshold_exceedance
│
├── validation/                         # Accuracy assessment module (required before project is complete)
│   ├── __init__.py
│   └── accuracy_assessment.py          # assess_chm_accuracy (nlcd_canopy, manual_samples, detection_error)
│
├── notebooks/
│   ├── 01_data_acquisition.ipynb       # Download tile, inspect structure, validate CRS
│   ├── 02_pdal_processing.ipynb        # Run PDAL pipeline: ground classification + HAG normalization
│   ├── 03_chm_derivation.ipynb         # Rasterize DSM/DTM, compute CHM GeoTIFF
│   └── 04_corridor_analysis.ipynb      # Buffer corridor, clip CHM, detect exceedances, export outputs
│
├── data/
│   ├── raw/                            # Downloaded .laz tiles and source shapefiles (gitignored)
│   │   └── .gitkeep
│   └── processed/                      # Intermediate PDAL outputs, DSM/DTM/CHM rasters (gitignored)
│       └── .gitkeep
│
├── outputs/
│   ├── rasters/                        # chm_clipped.tif — CHM clipped to corridor buffer
│   │   └── .gitkeep
│   ├── vector/                         # flagged_trees.gpkg — tree detections exceeding threshold
│   │   └── .gitkeep
│   └── tables/                         # flagged_tree_summary.csv — count and mean height by segment
│       └── .gitkeep
│
└── tests/
    └── test_placeholder.py             # Placeholder; no assertions yet
```

---

## Output Artifacts

The following files are the explicit final deliverables of this pipeline. All three must be produced before the project is considered complete.

| File | Description | Produced by |
|---|---|---|
| `outputs/rasters/chm_clipped.tif` | CHM raster clipped to the corridor buffer extent, in the projected CRS of the study area | `src.corridor.clip_chm_to_corridor()` — Notebook 04 |
| `outputs/vector/flagged_trees.gpkg` | GeoPackage of individual tree detections where CHM exceeds the height threshold, with `height_m` attribute preserved | `src.corridor.threshold_exceedance()` — Notebook 04 |
| `outputs/tables/flagged_tree_summary.csv` | Summary table of flagged tree count and mean canopy height aggregated by corridor segment | Aggregation step in Notebook 04 |

---

## Environment Setup

This project requires PDAL, which has complex C++ system dependencies. **PDAL must be installed via conda-forge, not pip.** pip installation will fail or produce a broken environment.

```bash
# Create the environment from the specification file
conda env create -f environment.yml

# Activate the environment
conda activate lidar-corridor

# Verify PDAL installation
pdal --version
```

> **PDAL installation note:** If PDAL fails to install or `pdal --version` returns an error, consult the [PDAL compilation documentation](https://pdal.io/en/stable/development/compilation/index.html). On macOS, installing via `conda install -c conda-forge pdal python-pdal` is the most reliable path. Do not attempt to install PDAL via pip.

To add the environment as a Jupyter kernel:

```bash
python -m ipykernel install --user --name lidar-corridor --display-name "Python 3 (lidar-corridor)"
```

---

## Running the Pipeline

The pipeline is designed to be executed as a notebook sequence. Code is not yet written; the following describes the intended execution order once implementation is complete.

1. **Acquire data** — Download a QL1/QL2 `.laz` tile from OpenTopography and place it in `data/raw/`. Download the CA transmission line centerline shapefile and place it in `data/raw/`.

2. **Run Notebook 01** (`01_data_acquisition.ipynb`) — Load the tile, print the inspection summary, and confirm CRS matches the expected EPSG. Resolve any CRS mismatch before continuing.

3. **Run Notebook 02** (`02_pdal_processing.ipynb`) — Verify PDAL is available, then execute the pipeline JSON. Confirm the output normalized `.laz` is written to `data/processed/`.

4. **Run Notebook 03** (`03_chm_derivation.ipynb`) — Rasterize the normalized point cloud to DSM and DTM, then compute the CHM. Inspect the CHM visually before proceeding.

5. **Run Notebook 04** (`04_corridor_analysis.ipynb`) — Load the centerline, buffer by corridor width, clip the CHM, apply the height threshold, and export all three output artifacts to `outputs/`.

6. **Run accuracy assessment** — Execute `validation/accuracy_assessment.py` using at least one of the three supported methods before reporting results. See the Validation section below.

---

## Key Concepts Reference

A glossary written for my own reference while learning this workflow.

**LAS/LAZ**
LAS is the ASPRS standard binary format for LiDAR point cloud data. LAZ is its losslessly compressed variant, which reduces file size by 80–90% with no data loss. PDAL and laspy both read LAZ natively without decompression.

**Return number**
Each LiDAR pulse can generate multiple returns as it reflects off different surfaces at different heights. The first return typically comes from the top of the canopy; later returns penetrate through gaps; the last return is usually from the ground. Return number is stored per point in the LAS format and is used to separate ground from vegetation.

**Ground classification (Class 2)**
ASPRS LAS specification classification code 2 designates ground returns. PDAL's `filters.csf` (Cloth Simulation Filter) and `filters.pmf` (Progressive Morphological Filter) are the two most common algorithms for assigning this classification automatically. The DTM is derived exclusively from class 2 points.

**DSM — Digital Surface Model**
A raster layer representing the elevation of the highest return per pixel. Includes the tops of trees, buildings, and other above-ground objects. In vegetated areas, the DSM represents canopy top elevation.

**DTM — Digital Terrain Model**
A raster layer derived from ground-classified returns only, representing the bare-earth surface elevation. It is the "underneath" layer: what the ground looks like without any above-ground cover.

**CHM — Canopy Height Model**
CHM = DSM − DTM. Each pixel represents the estimated height of vegetation or other objects above the ground surface. A CHM value of 12m means the canopy top is approximately 12 meters above the ground at that location.

**PDAL Pipeline**
A JSON-defined sequence of processing stages executed by PDAL. Each stage specifies a reader, filter, or writer type and its parameters. Pipelines are reproducible and portable — the same JSON produces the same output on any machine with PDAL installed. See `pipeline/pdal_pipeline.json` for this project's pipeline.

---

## Validation

**Accuracy assessment is required before this project can be considered analytically complete. It is not optional.**

A CHM workflow without accuracy assessment cannot make defensible claims about output quality. Before reporting CHM-derived height estimates or exceedance detections operationally, at least one of the three methods below must be executed using `validation.accuracy_assessment.assess_chm_accuracy()`.

### Supported methods

**`"nlcd_canopy"`**
Compares CHM-derived canopy cover fraction against the NLCD 2021 percent tree canopy cover layer at matched spatial resolution. Quantifies pixel-level agreement between the LiDAR-derived product and the nationally consistent canopy reference. Reports mean absolute error (MAE) and Pearson correlation coefficient.

**`"manual_samples"`**
Compares CHM pixel heights at GPS-surveyed reference locations against field-measured canopy heights at the same points. This method is the most direct validation approach but requires field data collection. Reports RMSE, MAE, and signed bias.

**`"detection_error"`**
Quantifies commission error (false detections: trees flagged by the model that do not correspond to a real tree in the reference set) and omission error (real trees in the reference set not captured by the detection layer). Requires a manually delineated reference tree crown dataset. Reports precision, recall, and F1 score.

---

## Limitations and Known Gaps

Honest documentation of what is not yet validated. These will be updated as the workflow matures.

- [ ] Ground classification filter parameters not yet validated against reference data
- [ ] CHM resolution choice (target: 1m) not yet benchmarked against actual point density of the selected tile
- [ ] Corridor centerline not yet verified against as-built transmission line locations
- [ ] Height threshold value (default: 15ft / ~4.57m) is illustrative; real utility standards vary by voltage class and are defined in FAC-003-4
- [ ] No accuracy assessment has been performed yet — CHM quality claims are provisional until `validation/accuracy_assessment.py` is executed

---

## Future Work

Potential extensions after the core pipeline is validated:

- **Multi-temporal change detection** — compare CHMs from two acquisition dates to identify vegetation growth trends along the corridor between inspection cycles
- **Sentinel-2 NDVI fusion** — overlay NDVI-derived vegetation density on the CHM exceedance map to contextualize structural height with spectral greenness
- **Canopy cover percentage metric** — compute fraction of corridor area with canopy cover above a threshold in addition to individual tree height
- **CLI packaging** — package `src/` as a reusable command-line tool with a click or argparse interface for reproducible execution without notebooks

---

## Planned Extensions

### SAR-LiDAR Fusion for Canopy Structure Under Cloud Cover

A planned extension is to fuse CHM outputs with Sentinel-1 C-band SAR backscatter to enable canopy structure estimation in periods of cloud cover or smoke obscuration — conditions directly relevant to wildfire response and post-storm utility infrastructure inspection, when optical sensors are unavailable but rapid vegetation assessment is most needed.

The cross-sensor validation use case — using the LiDAR-derived CHM as ground truth for training and validating SAR-based vegetation height models — would close the SAR portfolio gap and connect directly to utility-sector remote sensing workflows where all-weather operational capability is a practical requirement.

No additional code structure or skeleton files are planned for this item at this time.

---

## License

MIT License — see LICENSE file (to be added).

---

## Author

**Ivan Morris Sibaja**
MEDS 2025, Bren School of Environmental Science & Management, UC Santa Barbara

[[GitHub]](https://github.com/imsibaja) · [[LinkedIn]](https://linkedin.com/in/imsibaja)
