"""
Functions for loading corridor centerlines, buffering, clipping, and detecting
vegetation exceedances within transmission line right-of-way corridors.
"""

import numpy as np
import geopandas as gpd
import laspy
import rasterio
from rasterio.features import shapes
from shapely.geometry import box, shape
from scipy import ndimage
import warnings
import rioxarray as rioxa

def load_corridor_centerline(line_shape_url, laz_path):
    """
    Load a transmission line centerline shapefile or GeoPackage as a GeoDataFrame.

    Validates that all geometry types are LineString or MultiLineString.
    Other geometry types (Point, Polygon) will cause downstream buffering
    steps to fail or produce unexpected results and must be corrected upstream.

    Parameters
    ----------
    filepath : str or Path
        Path to a shapefile (.shp) or GeoPackage (.gpkg) containing
        transmission line centerline features.

    Returns
    -------
    geopandas.GeoDataFrame
        GeoDataFrame with LineString or MultiLineString geometries.

    Raises
    ------
    ValueError
        If the file contains geometry types other than LineString or
        MultiLineString.
    """
    
    # 1. Read LAZ to get bounds and build spatial filter for the API query
    las = laspy.read(laz_path)
    xmin, ymin, xmax, ymax = las.x.min(), las.y.min(), las.x.max(), las.y.max()

    # Pass bbox as spatial filter so the API returns only intersecting lines,
    # avoiding the 2000-record default cap on statewide queries
    base_url = line_shape_url.split("?")[0]
    spatial_url = (
        f"{base_url}/query?outFields=*&where=1%3D1&f=geojson"
        f"&geometry={xmin},{ymin},{xmax},{ymax}"
        f"&geometryType=esriGeometryEnvelope"
        f"&spatialRel=esriSpatialRelIntersects"
        f"&inSR={las.header.parse_crs().to_epsg()}&&outSR={las.header.parse_crs().to_epsg()}"
    )
    transmission_lines = gpd.read_file(spatial_url)

    valid_types = {"LineString", "MultiLineString"}
    if not transmission_lines.geom_type.isin(valid_types).all():
        invalid_types = transmission_lines.geom_type[~transmission_lines.geom_type.isin(valid_types)].unique()
        raise ValueError(f"Invalid geometry types found: {invalid_types}. All geometries must be LineString or MultiLineString.")

    transmission_lines = transmission_lines.to_crs("EPSG:32611")

    bbox = box(xmin, ymin, xmax, ymax)
    bbox_gdf = gpd.GeoDataFrame(geometry=[bbox], crs="EPSG:32611")

    clipped_transmission_lines = transmission_lines.clip(bbox_gdf)

    return clipped_transmission_lines


def buffer_corridor(gdf, buffer_distance_m = 15):
    """
    Apply a metric buffer around transmission line centerlines.

    The input GeoDataFrame must be in a projected CRS with linear units of
    meters before buffering. A geographic CRS (degrees) will produce
    incorrect distances and must be reprojected first.

    The buffer_distance_m parameter should be grounded in NERC FAC-003-4
    (Transmission Vegetation Management) clearance requirements for the
    relevant voltage class, not chosen arbitrarily. The illustrative default
    of ~15m (50ft) reflects typical 200–500kV right-of-way standards. Users
    must verify the applicable voltage class and consult FAC-003-4 Table 1
    before applying results operationally.

    Parameters
    ----------
    gdf : geopandas.GeoDataFrame
        Corridor centerline GeoDataFrame in a projected CRS (units: meters).
    buffer_distance_m : float
        Buffer distance in meters. Derive from FAC-003-4 clearance standards
        for the applicable voltage class; do not choose arbitrarily.

    Returns
    -------
    geopandas.GeoDataFrame
        GeoDataFrame of buffer polygons with the same CRS as the input.
    """
    
    if gdf.crs is None:
        gdf = gdf.to_crs("EPSG:32611")
        warnings.warn("Input GeoDataFrame had no CRS. Assigned EPSG:32611 for buffering. Verify that this CRS is appropriate for your region and use case.")
    if gdf.crs.is_geographic:
        gdf = gdf.to_crs("EPSG:32611")
        warnings.warn("Input GeoDataFrame was in a geographic CRS. Reprojected to EPSG:32611 for buffering. Verify that this CRS is appropriate for your region and use case.")

    return gdf.buffer(buffer_distance_m)


def clip_chm_to_corridor(chm_path, corridor_gdf, output_path):
    """
    Clip a CHM raster to the spatial extent of the corridor buffer polygon.

    Uses rioxarray to mask the CHM raster to the corridor buffer geometry.
    The CHM and corridor_gdf must be in the same CRS before clipping; a CRS
    mismatch will produce an empty or misaligned output.

    Final output artifact: outputs/rasters/chm_clipped.tif — CHM raster
    clipped to the corridor buffer extent. Produced by this function.

    Parameters
    ----------
    chm_path : str or Path
        Path to the full CHM GeoTIFF produced by compute_chm().
    corridor_gdf : geopandas.GeoDataFrame
        Corridor buffer GeoDataFrame produced by buffer_corridor().
    output_path : str or Path
        Path to write the clipped CHM GeoTIFF
        (e.g., outputs/rasters/chm_clipped.tif).

    Returns
    -------
    None
        Writes clipped CHM GeoTIFF to output_path.
    """
    
    chm_raster = rioxa.open_rasterio(chm_path)
    
    if chm_raster.rio.crs is None:
        chm_raster = chm_raster.rio.write_crs("EPSG:32611")
        warnings.warn("CHM raster had no CRS. Assigned EPSG:32611 for clipping. Verify that this CRS is appropriate for your region and use case.")
    if chm_raster.rio.crs.is_geographic:
        chm_raster = chm_raster.rio.reproject("EPSG:32611")
        warnings.warn("CHM raster was in a geographic CRS. Reprojected to EPSG:32611 for clipping. Verify that this CRS is appropriate for your region and use case.")  
    
    corridor_gdf = corridor_gdf.to_crs(chm_raster.rio.crs)
    corridor_geometry = corridor_gdf.unary_union
    
    chm_raster_clipped = chm_raster.rio.clip([corridor_geometry], all_touched=True, drop=False)

    chm_raster_clipped.rio.to_raster(output_path)
    
    return None

def threshold_exceedance(chm_clipped_path, height_threshold_m):
    """
    Identify pixels in the clipped CHM that exceed a vegetation height threshold.

    Applies a binary mask to the CHM raster and vectorizes contiguous
    exceedance zones into polygon features. The height threshold value should
    reflect utility vegetation management standards for the relevant voltage
    class under FAC-003-4, not be chosen arbitrarily.

    Final output artifacts produced downstream from this function's output:
    - outputs/vector/flagged_trees.gpkg — GeoPackage of individual tree
      detections exceeding the height threshold, with height attribute.
    - outputs/tables/flagged_tree_summary.csv — summary of flagged tree
      count and mean height by corridor segment.

    Parameters
    ----------
    chm_clipped_path : str or Path
        Path to the corridor-clipped CHM GeoTIFF produced by
        clip_chm_to_corridor().
    height_threshold_m : float
        Height threshold in meters above which vegetation is flagged
        (e.g., 4.57 for 15ft). Verify against applicable utility standards.

    Returns
    -------
    geopandas.GeoDataFrame
        GeoDataFrame of polygon features where CHM exceeds the threshold,
        with a 'height_m' attribute containing the CHM value at each feature.
    """
    # Context manager guarantees the file handle closes even if an error is raised mid-read.
    with rasterio.open(chm_clipped_path) as src:
        # Pull Band 1, the CHM values
        chm_arr = src.read(1).astype(np.float32)

        # Map array indicies as real coordinates
        transform = src.transform

        # Preserve the raster's CRS 
        crs = src.crs

    # Mask where CHM exceeds height threshold
    mask_arr = chm_arr > height_threshold_m

    # Label zones of contiguous True pixels in the mask. 
    labeled, n = ndimage.label(mask_arr)

    # Return empty GDF if no exceedances found
    if n == 0:
        message = f"No exceedances found above {height_threshold_m}m. Returning empty GeoDataFrame:"
        warnings.warn(message)
        return gpd.GeoDataFrame({"geometry": [], "height_m": []}, crs=crs)

    # Compute the mean CHM value for each labeled zone.
    mean_heights = ndimage.mean(chm_arr, labeled, range(1, n + 1))

    # Build a label -> mean_height dict. 0 is background, enumeration begins at 1. 
    height_lookup = dict(enumerate(mean_heights, start=1))

    seen = set()
    records = []
    for geom_dict, val in shapes(
        
        labeled.astype(np.int16),
        # Mask exceedance zones
        mask=mask_arr.astype(np.uint8),
        # Transform pixel coordinates to real-world coordinates
        transform=transform,
    ):
        # LV or label value
        lv = int(val)

        # skip loop if already seen this label value or if it's 0 (background)
        if lv == 0 or lv in seen:
            continue
        seen.add(lv)

        # append a dict with geometry and mean height for this exceedance zone to the records list
        records.append({"geometry": shape(geom_dict), "height_m": height_lookup[lv]})
        
    return gpd.GeoDataFrame(records, crs=crs)

