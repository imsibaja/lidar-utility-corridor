"""
Functions for deriving DSM, DTM, and CHM rasters from normalized LiDAR point clouds.
"""


def rasterize_to_dsm(normalized_laz, resolution, output_path):
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
    normalized_laz : str or Path
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
    raise NotImplementedError


def rasterize_to_dtm(normalized_laz, resolution, output_path):
    """
    Create a Digital Terrain Model (DTM) GeoTIFF from ground-classified returns.

    Filters the point cloud to ASPRS classification code 2 (ground) and
    rasterizes using the minimum or interpolated elevation per cell to
    represent the bare-earth surface. The DTM must use the same resolution
    and spatial extent as the DSM before CHM subtraction.

    Parameters
    ----------
    normalized_laz : str or Path
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
    raise NotImplementedError


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
    raise NotImplementedError
