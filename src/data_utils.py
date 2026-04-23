"""
Utilities for loading, inspecting, and validating USGS 3DEP LiDAR point clouds.
"""

import laspy
import numpy as np


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
    return laspy.read(filepath)


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
    # Print point count and classification distribution
    print(f"Total points: {len(las_data)}")
    
    # Print distibution of classification codes
    class_dist = dict(zip(*np.unique(las_data.classification, return_counts=True)))
    print("Classification distribution:")
    for cls, count in class_dist.items():
        print(f"  Class {cls}: {count} points")
        
    # Print bounding box info
    print("Bounding box:")
    print(f"xmin: {las_data.x.min()}, xmax: {las_data.x.max()}")
    print(f"ymin: {las_data.y.min()}, ymax: {las_data.y.max()}")
    print(f"zmin: {las_data.z.min()}, zmax: {las_data.z.max()}")
    
    las_xrange = (las_data.x.max() - las_data.x.min())
    las_yrange = (las_data.y.max() - las_data.y.min())
    
    # Print estimated point density
    print(f"Estimated point density (pts/m²): {len(las_data) / (las_xrange * las_yrange)}")



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
    
    epsg = las_data.header.parse_crs().to_epsg()
    if epsg != expected_epsg:   
        raise ValueError(f"CRS mismatch: expected EPSG:{expected_epsg}, got EPSG:{epsg}")

    return True