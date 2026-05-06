"""
Functions for deriving DSM, DTM, and CHM rasters from normalized LiDAR point clouds.
"""

import numpy as np
import rasterio
from src.data_utils import load_laz
from pathlib import Path


def rasterize_to_dsm(normalized_laz_path, resolution, output_path):
    """
    Create a Digital Surface Model (DSM) GeoTIFF from a normalized point cloud.

    Rasterizes the maximum HeightAboveGround value within each pixel cell.
    The DSM represents the elevation of the highest return per cell — top of
    canopy in vegetated areas, rooftop in built areas.

    The target resolution must be consistent with the point density of the
    input tile. At 1m resolution, a minimum of ~2 pts/m² is required for
    reliable cell coverage (QL2 or better). Verify point density via
    inspect_point_cloud() before selecting a resolution.

    Parameters
    ----------
    normalized_laz_path : str or Path
        Path to the height-normalized .laz file produced by the PDAL pipeline
        (filters.hag_nn output). Points carry a HeightAboveGround dimension.
    resolution : float
        Target raster resolution in meters (e.g., 1.0 for 1m output).
    output_path : str or Path
        Path to write the output DSM GeoTIFF.

    Returns
    -------
    None
        Writes DSM GeoTIFF to output_path.
    """
    
    normalized_las = load_laz(normalized_laz_path)

    ncols = np.floor((normalized_las.x - normalized_las.x.min()) / resolution).astype(int)
    nrows = np.floor((normalized_las.y.max() - normalized_las.y) / resolution).astype(int)

    scatter_max = np.full((nrows.max() + 1, ncols.max() + 1), -np.inf)  

    np.maximum.at(scatter_max, (nrows, ncols), normalized_las.HeightAboveGround)
    
    scatter_max[scatter_max == -np.inf] = np.nan
    
    with rasterio.open(
        output_path,
        'w',
        driver='GTiff',
        height=scatter_max.shape[0],
        width=scatter_max.shape[1],
        count=1,
        dtype=scatter_max.dtype,
        crs='EPSG:32611', 
        transform=rasterio.transform.from_origin(
            normalized_las.x.min(), 
            normalized_las.y.max(), 
            resolution, 
            resolution
        )
    ) as dst:
        dst.write(scatter_max, 1)

    



def rasterize_to_dtm(normalized_laz_path, resolution, output_path):
    """
    Create a Digital Terrain Model (DTM) GeoTIFF from ground-classified returns.

    Filters the point cloud to ASPRS classification code 2 (ground) and
    rasterizes using the minimum or interpolated elevation per cell to
    represent the bare-earth surface. The DTM must use the same resolution
    and spatial extent as the DSM before CHM subtraction.

    Parameters
    ----------
    normalized_laz_path : str or Path
        Path to the ground-classified and height-normalized .laz file.
        Ground classification must have been applied (e.g., filters.csf)
        prior to calling this function.
    resolution : float
        Target raster resolution in meters. Must match the value passed to
        rasterize_to_dsm() to enable pixel-aligned CHM computation.
    output_path : str or Path
        Path to write the output DTM GeoTIFF.

    Returns
    -------
    None
        Writes DTM GeoTIFF to output_path.
    """
    normalized_las = load_laz(normalized_laz_path)
    
    # Filter to ground points (classification code 2)
    normalized_las = normalized_las[normalized_las.classification == 2]

    # Rasterize using minimum elevation per cell to represent the terrain surface
    ncols = np.floor((normalized_las.x - normalized_las.x.min()) / resolution).astype(int)
    nrows = np.floor((normalized_las.y.max() - normalized_las.y) / resolution).astype(int)

    # Initialize an array to hold the minimum elevation values for each cell
    scatter_min = np.full((nrows.max() + 1, ncols.max() + 1), np.inf)  

    # Use np.minimum.at to compute the minimum height above ground for each cell
    np.minimum.at(scatter_min, (nrows, ncols), normalized_las.HeightAboveGround)
    
    # Replace np.inf with NaN to indicate cells with no ground points 
    scatter_min[scatter_min == np.inf] = np.nan
    
    # Validate that the resulting DTM raster has the same dimensions and georeferencing as the DSM raster
    output_path_dsm = Path(str(output_path).replace("dtm", "dsm"))  # Assuming DSM is saved with a similar naming convention
    with rasterio.open(output_path_dsm) as dsm_src:
        dsm_data = dsm_src.read(1)
    # This is a simplified validation; in practice, you might want to check more detailed metadata
    assert scatter_min.shape == dsm_data.shape, "Shape mismatch between DTM and DSM"

    # Write the DTM raster to a GeoTIFF file
    with rasterio.open(
        output_path,
        'w',
        driver='GTiff',
        height=scatter_min.shape[0],
        width=scatter_min.shape[1],
        count=1,
        dtype=scatter_min.dtype,
        crs='EPSG:32611', 
        transform=rasterio.transform.from_origin(
            normalized_las.x.min(), 
            normalized_las.y.max(), 
            resolution, 
            resolution
        )
    ) as dst:
        dst.write(scatter_min, 1)


def compute_chm(dsm_path, dtm_path, output_path):
    """
    Compute a Canopy Height Model (CHM) by subtracting DTM from DSM.

    CHM = DSM − DTM. Each pixel value represents estimated vegetation height
    above the ground surface. The DSM and DTM must share identical CRS, pixel
    extent, and resolution before subtraction; misalignment will produce
    erroneous CHM values.

    Parameters
    ----------
    dsm_path : str or Path
        Path to the DSM GeoTIFF produced by rasterize_to_dsm().
    dtm_path : str or Path
        Path to the DTM GeoTIFF produced by rasterize_to_dtm().
    output_path : str or Path
        Path to write the output CHM GeoTIFF.

    Returns
    -------
    None
        Writes CHM GeoTIFF to output_path. Negative values (DSM below DTM
        due to interpolation artifacts) should be clamped to zero.
    """

    with rasterio.open(dsm_path) as dsm_src:
        dsm = dsm_src.read(1)
        dsm_meta = dsm_src.meta

    with rasterio.open(dtm_path) as dtm_src:
        dtm = dtm_src.read(1)
        dtm_meta = dtm_src.meta


    # Validate that DSM and DTM metadata are compatible for CHM computation
    assert dsm_meta['crs'] == dtm_meta['crs'], "CRS mismatch between DSM and DTM"
    # The transform includes pixel size and origin; it must be identical for both rasters to ensure proper alignment
    assert dtm_meta['transform'] == dsm_meta['transform'], "Transform mismatch between DSM and DTM"
    # The width and height must also match to ensure pixel-wise subtraction is valid
    assert chm_meta['width'] == dsm_meta['width'] == dtm_meta['width'], "Width mismatch between DSM and DTM"
    assert chm_meta['height'] == dsm_meta['height'] == dtm_meta['height'], "Height mismatch between DSM and DTM"

    # Compute CHM by subtracting DTM from DSM
    chm = dsm - dtm
    
    # CHM metadata should match the DSM/DTM metadata (same CRS, transform, resolution)
    # 'numpy.ndarray' object has no attribute 'meta'
    chm_meta = dsm_meta.copy()
    
    # Clamp negative values to zero
    chm[chm < 0] = 0

    # Write the CHM raster to a GeoTIFF file
    with rasterio.open(
        output_path,
        'w',
        driver='GTiff',
        height=chm.shape[0],
        width=chm.shape[1],
        count=1,
        dtype=chm.dtype,
        crs=chm_meta['crs'],
        transform=chm_meta['transform']
    ) as dst:
        dst.write(chm, 1)