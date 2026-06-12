"""Spatial RDD validation for CHM outputs using the Thomas Fire perimeter as treatment boundary."""

from pathlib import Path
import numpy as np
import pandas as pd
import rioxarray
import rasterio
import geopandas as gpd
import scipy.stats
from matplotlib import pyplot as plt


def _intercept_se(x, y):
    """
    Standard error of the OLS intercept for a simple linear regression.

    Used internally by spatial_rdd() to propagate uncertainty from each
    side of the RDD boundary into the final estimate's standard error.

    Parameters
    ----------
    x : array-like
        Predictor (signed distance values for one side of the boundary).
    y : array-like
        Response (CHM height values for the same pixels).

    Returns
    -------
    float
        Standard error of the intercept estimate.

    Notes
    -----
    Var(intercept) = s² * (1/n + x̄² / Σ(xᵢ - x̄)²)
    where s² = Σresiduals² / (n - 2).
    """
    # TODO — Implement using numpy and scipy.stats.linregress.
    #   1. Fit linregress(x, y) to get slope and intercept.
    #   2. Compute residuals = y - (slope * x + intercept).
    #   3. s2 = sum(residuals**2) / (n - 2)
    #   4. sxx = sum((x - x.mean())**2)
    #   5. var_intercept = s2 * (1/n + x.mean()**2 / sxx)
    #   6. Return sqrt(var_intercept).
    
    linreg = scipy.stats.linregress(x, y)
    slope, intercept = linreg.slope, linreg.intercept
    residuals = y - (slope * x + intercept)
    n = len(x)
    s2 = np.sum(residuals**2) / (n - 2)
    sxx = np.sum((x - x.mean())**2)
    var_intercept = s2 * (1/n + x.mean()**2 / sxx)
    
    return np.sqrt(var_intercept)
    


def _plot_discontinuity(binned, bandwidth_m, save_path):
    """
    Save a scatter plot of binned mean CHM vs. signed distance to the boundary.

    Parameters
    ----------
    binned : pandas.DataFrame
        DataFrame with columns 'bin' (bin midpoint in meters) and
        'height_m' (mean CHM per bin).
    bandwidth_m : float
        Bandwidth used, for shading the burned/unburned regions.
    save_path : str or Path
        Full path to save the figure (e.g., outputs/figures/spatial_rdd.png).
    """
    # TODO — Implement with matplotlib. ✅
    #   - Scatter plot: x = binned['bin'], y = binned['height_m'].
    #   - Vertical dashed line at x=0 (the fire boundary).
    #   - Shade x < 0 in light red ("burned"), x > 0 in light green ("unburned").
    #   - Label axes: x = "Signed distance to fire boundary (m) ← burned | unburned →"
    #                 y = "Mean CHM (m)"
    #   - Save with fig.savefig(save_path, dpi=150). Close the figure after saving.

    BG = "#0d0d0d"
    TEXT = "#ffffff"
    y_min, y_max = binned['height_m'].min(), binned['height_m'].max()

    fig, ax = plt.subplots(figsize=(8, 6), facecolor=BG)
    ax.set_facecolor(BG)

    ax.scatter(binned['bin'], binned['height_m'], color=TEXT, s=22, label='Binned mean CHM')
    ax.axvline(x=0, color='#aaaaaa', linestyle='--', linewidth=1.2, label='Fire boundary')
    ax.fill_betweenx([y_min, y_max], -bandwidth_m, 0, color='#ff4040', alpha=0.18, label='Burned')
    ax.fill_betweenx([y_min, y_max], 0, bandwidth_m, color='#40c060', alpha=0.18, label='Unburned')

    ax.set_xlabel("Signed distance to fire boundary (m) ← burned | unburned →", color=TEXT)
    ax.set_ylabel("Mean CHM (m)", color=TEXT)
    ax.set_title(f"Spatial RDD Discontinuity (Bandwidth = {bandwidth_m}m)", color=TEXT)
    ax.tick_params(colors=TEXT)
    for spine in ax.spines.values():
        spine.set_edgecolor("#2a2a2a")

    legend = ax.legend(facecolor="#1a1a1a", labelcolor=TEXT, edgecolor="#2a2a2a")
    fig.savefig(save_path, dpi=150, facecolor=BG)
    plt.close(fig)


def spatial_rdd(chm_path, fire_perimeter_path, bandwidth_m=200, output_path=None):
    """
    Estimate the causal effect of the Thomas Fire on canopy height using a
    Spatial Regression Discontinuity Design.

    The fire perimeter is treated as a sharp treatment boundary. Pixels inside
    received the treatment (fire); pixels outside did not. Fitting separate
    local linear regressions on each side of the boundary and extrapolating
    to distance=0 gives a causal estimate of the fire's effect on canopy
    height — independent of gradual spatial trends in terrain or vegetation.

    Identifying assumption: vegetation just inside and just outside the fire
    perimeter boundary was similar before the fire. The boundary was set by
    fire weather and fuel conditions, not pre-existing vegetation structure.

    Parameters
    ----------
    chm_path : str or Path
        Path to the full-extent CHM GeoTIFF (not the corridor-clipped version —
        we need pixels near the fire boundary, which may be outside the corridor).
    fire_perimeter_path : str or Path
        Path to the Thomas Fire perimeter GeoPackage in EPSG:32611.
    bandwidth_m : float
        Half-width of the analysis window in meters. Only pixels within this
        distance of the perimeter boundary are included. Default 200m.
        Run sensitivity checks at 100m and 300m to confirm estimate stability.
    output_path : str or Path, optional
        Directory for output figures and tables. Defaults to outputs/.

    Returns
    -------
    dict
        {
            "rdd_estimate": float,   # jump in CHM at boundary (meters); negative = fire reduced height
            "se": float,             # standard error of the estimate
            "ci_lower": float,       # 95% CI lower bound
            "ci_upper": float,       # 95% CI upper bound
            "n_pixels": int,         # pixels included in the analysis window
            "bandwidth_m": float,    # bandwidth used
        }

    Raises
    ------
    ValueError
        If fewer than 50 pixels fall within the bandwidth window.
    NotImplementedError
        This function is not yet implemented.
    """
    # TODO 6a — Load the CHM raster with rioxarray and extract pixel centroids.
    #   - Open chm_path with rioxarray, squeeze the band dimension.
    #   - Use rasterio.open() + rasterio.transform.xy() to convert row/col
    #     indices to projected (x, y) coordinates.
    #   - Flatten to 1D arrays: heights, xs, ys (exclude NaN pixels).
    #   - Build a GeoDataFrame (pixel_points) with a 'height_m' column and
    #     point geometries from xs, ys. Set CRS to match the CHM.
    
    with rioxarray.open_rasterio(chm_path) as chm: 
        chm = chm.squeeze()  # drop band dimension if it exists
        transform = chm.rio.transform()
        height_m = chm.values.flatten()
        rows, cols = np.indices(chm.shape)
        xs, ys = rasterio.transform.xy(transform, rows.flatten(), cols.flatten())
        pixel_points = gpd.GeoDataFrame(
            {'height_m': height_m},
            geometry=gpd.points_from_xy(xs, ys),
            crs=chm.rio.crs
        ).dropna(subset=['height_m'])  # exclude NaN pixels

    # TODO 6b — Compute signed distance from each pixel to the fire boundary.
    #   - Load the fire perimeter with geopandas and reproject to the CHM CRS.
    #   - Use .geometry.boundary.unary_union to get the perimeter edge (not interior).
    #   - Compute pixel_points.geometry.distance(boundary) → dist_to_boundary.
    #   - Sign: negative for pixels inside the perimeter, positive for outside.
    #     Hint: use fire.geometry.unary_union.contains(pixel_points.geometry)
    #     to build the inside mask, then np.where() to apply the sign.
    #   - Store as 'signed_dist' column in pixel_points.
    #   Note: distance() on a large raster can take several minutes. Consider
    #   computing on a downsampled grid and interpolating, or using a raster
    #   distance transform via scipy.ndimage.distance_transform_edt().
    
    fire = gpd.read_file(fire_perimeter_path).to_crs(chm.rio.crs)
    boundary = fire.geometry.boundary.unary_union
    dist_to_boundary = pixel_points.geometry.distance(boundary) 
    
    inside_mask = fire.geometry.unary_union.contains(pixel_points.geometry)
    pixel_points['signed_dist'] = np.where(inside_mask, -dist_to_boundary, dist_to_boundary)   
    
    
    def bandwidth_lr(bandwidth_m = bandwidth_m):
        # TODO 6c — Restrict to the bandwidth window.
        #   - Filter to rows where abs(signed_dist) <= bandwidth_m.
        #   - Raise ValueError if fewer than 50 pixels remain (too narrow to fit).
        #   - Report n_pixels to the user.
        
        pixel_points_restricted = pixel_points[np.abs(pixel_points['signed_dist']) <= bandwidth_m]
        n_pixels = len(pixel_points_restricted)
        if n_pixels < 50:
            raise ValueError(f"Only {n_pixels} pixels within {bandwidth_m}m bandwidth. Consider increasing bandwidth.")
        print(f"{n_pixels} pixels within {bandwidth_m}m bandwidth included in RDD analysis.")
        
        # TODO 6d — Bin and plot the raw discontinuity.
        #   - Bin pixels into ~10m increments of signed_dist.
        #   - Compute mean CHM per bin.
        #   - Call _plot_discontinuity() to save the figure.
        #   - Make note that a visible jump at x=0 is the visual evidence of a discontinuity.

        pixel_points_restricted['bin'] = (pixel_points_restricted['signed_dist'] // 10) * 10 + 5  # bin midpoints
        binned = pixel_points_restricted.groupby('bin')['height_m'].mean().reset_index()
        figures_path = Path(output_path) / "figures"
        figures_path.mkdir(parents=True, exist_ok=True)
        _plot_discontinuity(binned, bandwidth_m, figures_path / f"spatial_rdd_bandwidth_{bandwidth_m}m.png")
        print("Discontinuity plot saved. Look for a visible jump at x=0 as evidence of a fire effect on canopy height.")
                
        # TODO 6e — Fit local linear regression on each side of the boundary.
        #   - Split window into burned (signed_dist < 0) and unburned (>= 0).
        #   - Use scipy.stats.linregress on each half: CHM ~ signed_dist.
        #   - Extrapolate each line to signed_dist=0 (the intercept IS the prediction
        #     at x=0, since slope * 0 + intercept = intercept).
        #   - RDD estimate = predicted CHM (burned side) − predicted CHM (unburned side).
        #     A negative value means the fire reduced canopy height, as expected.
        #   - Compute SE via _intercept_se() on each side, then combine:
        #     SE_total = sqrt(SE_burned^2 + SE_unburned^2).
        #   - 95% CI: estimate ± 1.96 * SE_total.       
        burned = pixel_points_restricted[pixel_points_restricted['signed_dist'] < 0]
        unburned = pixel_points_restricted[pixel_points_restricted['signed_dist'] >= 0] 
        linreg_burned = scipy.stats.linregress(burned['signed_dist'], burned['height_m'])
        linreg_unburned = scipy.stats.linregress(unburned['signed_dist'], unburned['height_m'])
        burned_intercept = linreg_burned.intercept
        unburned_intercept = linreg_unburned.intercept
        rdd_estimate = burned_intercept - unburned_intercept  # negative means fire reduced height
        se_burned = _intercept_se(burned['signed_dist'], burned['height_m'])
        se_unburned = _intercept_se(unburned['signed_dist'], unburned['height_m'])
        se_total = np.sqrt(se_burned**2 + se_unburned**2)
        ci_lower = rdd_estimate - 1.96 * se_total
        ci_upper = rdd_estimate + 1.96 * se_total
        print(f"RDD estimate: {rdd_estimate:.2f} m (95% CI: {ci_lower:.2f} to {ci_upper:.2f})")
        
        return {"bandwidth_m": bandwidth_m, "rdd_estimate": rdd_estimate, "se": se_total, "ci_lower": ci_lower, "ci_upper": ci_upper, "n_pixels": n_pixels}

    # TODO 6f — Sensitivity check across alternative bandwidths.
    #   - Re-run steps 6c–6e at bandwidth_m = 100, 200, and 300.
    #   - Collect results into a DataFrame and save to
    #     outputs/tables/rdd_sensitivity.csv.
    #   - If the estimate changes by more than ~20% across bandwidths, flag it.

    tables_path = Path(output_path) / "tables"
    tables_path.mkdir(parents=True, exist_ok=True)

    if bandwidth_m not in [100, 200, 300]:
        bandwidths = [bandwidth_m, 100, 200, 300]
    else:
        bandwidths = [100, 200, 300]
    results = []

    for bw in bandwidths:
        result = bandwidth_lr(bandwidth_m=bw)
        results.append(result)

    results_df = pd.DataFrame(results)
    results_df.to_csv(tables_path / "rdd_sensitivity.csv", index=False)
    print("RDD sensitivity results saved. Check for stability across bandwidths — flag if estimates vary by more than ~20%.")

    primary = next(r for r in results if r["bandwidth_m"] == bandwidth_m)
    return primary

