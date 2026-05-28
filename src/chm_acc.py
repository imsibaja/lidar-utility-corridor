"""
Function for assessing the accuracy of a canopy height model (CHM) derived from lidar data, using field measurements of tree heights as ground truth. The function will calculate various error metrics such as mean absolute error (MAE), root mean squared error (RMSE), and R-squared (R²) to evaluate the performance of the CHM in estimating tree heights.
"""

from geopandas import gpd
import pandas as pd
import numpy as np
import rasterio

def assess_chm_accuracy(chm_path, fire_perimeter_path, output_path):

    """
    Assess CHM accuracy by comparing canopy heights inside and outside a fire perimeter.

    Loads the CHM and creates masks for areas inside and outside the fire perimeter.
    Computes mean and median CHM for each zone, with the expectation that inside
    perimeter mean CHM should be significantly lower than outside. Records mean CHM
    inside, mean CHM outside, difference, and percentage of inside pixels at or below
    0.5m (bare ground). Writes summary statistics to CSV.

    Parameters
    ----------
    chm_path : str or Path
        Path to the CHM GeoTIFF produced by compute_chm().
    fire_perimeter_path : str or Path
        Path to the fire perimeter vector file (e.g., GeoJSON or Shapefile) used to create masks.
    output_path : str or Path
        Path to write the output accuracy csv.

    Returns
    -------
    accuracy_df: pandas.DataFrame
        DataFrame containing mean CHM inside, mean CHM outside,
        mean difference, and percent bare ground inside the fire perimeter.
    """

    with rasterio.open(chm_path) as chm:
        chm_data = chm.read(1)
        chm_meta = chm.meta
        nodata = chm.nodata

    valid_mask = np.isfinite(chm_data)

    fire_perimeter_gdf = gpd.read_file(fire_perimeter_path).to_crs(chm_meta['crs'])
    fire_mask = rasterio.features.geometry_mask(
        fire_perimeter_gdf.geometry,
        out_shape=chm_data.shape,
        transform=chm_meta['transform'],
        invert=True
        )

    chm_inside = chm_data[fire_mask & valid_mask]
    chm_outside = chm_data[~fire_mask & valid_mask]

    mean_inside = np.mean(chm_inside)
    mean_outside = np.mean(chm_outside)
    mean_diff = mean_outside - mean_inside

    median_inside = np.median(chm_inside)
    median_outside = np.median(chm_outside)
    median_diff = median_outside - median_inside

    percent_bare_ground = np.sum(chm_inside <= 0.5) / len(chm_inside) * 100
    
    accuracy_summary = {
        "mean_chm_inside": mean_inside,
        "mean_chm_outside": mean_outside,
        "mean_difference": mean_diff,
        "median_chm_inside": median_inside,
        "median_chm_outside": median_outside,
        "median_difference": median_diff,
        "percent_bare_ground_inside": percent_bare_ground
    }   
    
    accuracy_df = pd.DataFrame([accuracy_summary])
    accuracy_df.to_csv(output_path, index=False)
    
    return accuracy_df
    
    