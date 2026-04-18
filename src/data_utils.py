"""
Utilities for loading, inspecting, and validating USGS 3DEP LiDAR point clouds.
"""


def load_laz(filepath):
    """
    Read a .laz or .las file and return a laspy LasData object.

    Parameters
    ----------
    filepath : str or Path
        Path to the input .laz or .las file.

    Returns
    -------
    laspy.LasData
        Parsed point cloud object with access to all dimensions (x, y, z,
        classification, return_number, intensity, etc.).
    """
    raise NotImplementedError


def inspect_point_cloud(las_data):
    """
    Print a human-readable summary of a LiDAR point cloud.

    Outputs to stdout:
    - Total point count
    - Distribution of ASPRS classification codes (e.g., class 1=unclassified,
      class 2=ground, class 5=high vegetation)
    - Bounding box: xmin, xmax, ymin, ymax, zmin, zmax
    - Estimated point density (pts/m²) derived from total point count divided
      by the horizontal footprint of the bounding box

    Parameters
    ----------
    las_data : laspy.LasData
        Point cloud object loaded via load_laz().

    Returns
    -------
    None
        Prints summary to stdout.
    """
    raise NotImplementedError


def validate_crs(las_data, expected_epsg):
    """
    Verify that the point cloud's horizontal CRS matches the expected EPSG code.

    USGS 3DEP tiles are distributed in state plane or UTM projections and must
    be confirmed before any spatial join, buffering, or rasterization step.
    If the CRS does not match, the data must be reprojected before processing.

    Parameters
    ----------
    las_data : laspy.LasData
        Point cloud object loaded via load_laz().
    expected_epsg : int
        EPSG code of the expected projected CRS
        (e.g., 26911 for UTM Zone 11N / NAD83).

    Returns
    -------
    bool
        True if the point cloud CRS matches expected_epsg.

    Raises
    ------
    ValueError
        If the point cloud CRS does not match expected_epsg.
    """
    raise NotImplementedError
