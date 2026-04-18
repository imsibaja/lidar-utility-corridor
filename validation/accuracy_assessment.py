"""
Accuracy assessment for CHM outputs. This module is required before the
project can be considered analytically complete. See assess_chm_accuracy().
"""


def assess_chm_accuracy(chm_path, reference_data, method):
    """
    Compare CHM-derived canopy height estimates against a reference dataset
    to quantify prediction error.

    This step is required before the project can be considered analytically
    complete. It is not optional. A CHM workflow without accuracy assessment
    cannot make defensible claims about output quality, and results should
    not be presented operationally until at least one method below has been
    executed and error metrics have been reviewed.

    Parameters
    ----------
    chm_path : str or Path
        Path to the CHM GeoTIFF to be evaluated (typically
        outputs/rasters/chm_clipped.tif or the full-extent CHM).
    reference_data : str, Path, or geopandas.GeoDataFrame
        Reference dataset used for comparison. The expected format depends
        on the chosen method:
        - "nlcd_canopy": path to the NLCD 2021 Percent Tree Canopy GeoTIFF,
          resampled or aligned to the CHM grid.
        - "manual_samples": path to a point shapefile or GeoPackage with a
          field-measured canopy height attribute at each sample location.
        - "detection_error": path to a GeoPackage of manually delineated
          tree crown polygons used as the reference detection set.
    method : str
        Accuracy assessment method. Must be one of:

        "nlcd_canopy"
            Compare CHM-derived canopy cover fraction against the NLCD 2021
            percent tree canopy cover layer at matched spatial resolution.
            Reports mean absolute error (MAE) and Pearson correlation
            coefficient between the two rasters.

        "manual_samples"
            Compare CHM pixel heights at surveyed reference points against
            field-measured canopy heights at the same locations. Reports
            root mean squared error (RMSE), mean absolute error (MAE), and
            signed bias (mean CHM height minus mean field height).

        "detection_error"
            Quantify commission error (false detections above threshold with
            no corresponding reference tree) and omission error (reference
            trees not captured by the detection layer) for individual tree
            detections above a specified height threshold. Compared against
            a manually delineated reference tree crown dataset. Reports
            precision, recall, and F1 score.

    Returns
    -------
    dict
        Summary dictionary of accuracy metrics appropriate to the chosen
        method. Key sets by method:

        "nlcd_canopy":
            {"mae": float, "pearson_r": float, "n_pixels": int}

        "manual_samples":
            {"rmse": float, "mae": float, "bias": float, "n_samples": int}

        "detection_error":
            {"precision": float, "recall": float, "f1": float,
             "n_reference": int, "n_detected": int}

    Raises
    ------
    ValueError
        If method is not one of "nlcd_canopy", "manual_samples", or
        "detection_error".
    NotImplementedError
        This function is not yet implemented.
    """
    raise NotImplementedError
