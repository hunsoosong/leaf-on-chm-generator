import json
import os
from typing import Any, List, Tuple

import cv2
import laspy
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import numpy.typing as npt
import pdal
import rasterio
import scipy
from affine import Affine
from rasterio.crs import CRS
from rasterio.transform import from_origin
from scipy import interpolate, ndimage
from scipy.ndimage import median_filter, minimum_filter
from scipy.signal import convolve2d as conv2
from skimage.morphology import remove_small_objects, dilation, square
from skimage.util import view_as_windows


# -------------------------------
# Global parameters (adjustable)
# -------------------------------
slope_threshold = 45  # slope threshold (degrees)
target_resolution = 0.5  # 0.5m resolution
DSM_exist = False  # if DSM exist True, or False
RuleA = True  # if RuleA apply True (ground generation)
SAVE = True  # if Save, true


# ------------------------------------------
# 1. Raw LAZ file generation (PDAL pipeline)
# ------------------------------------------
def generate_raw_laz(
    ept_url: str, bbox_coords: List[float], target_epsg: int, session_dir: str
) -> str:
    """
    Generate a raw LAZ file from the ept_url within the given boundary after EPSG transformation.

    Parameters:
        ept_url (str): EPT data URL.
        bbox_coords (list): Boundary coordinates [xmin, ymin, xmax, ymax].
        target_epsg (str or int): Target EPSG code.
        session_dir (str): Directory to save the output.

    Returns:
        (str): File path of the generated LAZ file.
    """
    input_dir = os.path.join(session_dir, "input")
    os.makedirs(input_dir, exist_ok=True)
    out_laz_filename = os.path.join(input_dir, "lidar_halfmeter.laz")

    pipeline_json = {
        "pipeline": [
            {
                "filename": ept_url,
                "bounds": f"([{bbox_coords[0]}, {bbox_coords[2]}], [{bbox_coords[1]}, {bbox_coords[3]}])",
                "type": "readers.ept",
                "tag": "read",
            },
            {
                "out_srs": f"EPSG:{target_epsg}",
                "type": "filters.reprojection",
                "tag": "reproject",
            },
            {
                "filename": out_laz_filename,
                "inputs": ["reproject"],
                "type": "writers.las",
                "tag": "write",
            },
        ]
    }

    print("Running PDAL Pipeline for raw LAZ generation...")
    pipeline = pdal.Pipeline(json.dumps(pipeline_json))
    pipeline.execute()
    print(f"Pipeline Complete. Output saved to {out_laz_filename}.")
    return out_laz_filename


# ------------------------------------------------
# 2. DSM/DTM Generation (0.5m resolution, including pre-processing/interpolation)
# ------------------------------------------------
def generate_dsm_dtm(
    laz_path: str, target_resolution: float, target_epsg: int, session_dir: str
) -> Any:
    """
    Generate DSM (based on last return) and DTM (after removing buildings/objects and interpolation)
    from a LAZ file. (Generation from LAZ is performed only if DSM_exist is False.)

    Parameters:
        laz_path (str): Input LAZ file path.
        target_resolution (float): Target resolution (in meters).
        target_epsg (int or str): Target EPSG code.
        session_dir (str): Root directory for saving results.

    Returns:
        out_dsm, out_dtm (str): File paths for DSM and DTM.
        crs, transform: Raster georeferencing information.
        DSM, dtm: Calculated DSM and DTM arrays.
        DSM_LAST: Original DSM (last return) array (used for water body classification).
    """
    if DSM_exist:
        out_dsm = os.path.join(session_dir, "DSM_Purdue.tif")
        with rasterio.open(out_dsm) as DSM_file:
            transform = DSM_file.transform
            crs = DSM_file.crs
            DSM = DSM_file.read(1)
        EPSG_CODE = crs.to_epsg()
        print(f"The EPSG code of the DSM file is: {EPSG_CODE}")
        print("DSM exists, skip steps A-C")
        dtm = None
        DSM_LAST = None
    else:
        print("Create high-res DSM by taking last-return")
        unit = "meter"  # Assuming LAS file units are in meters
        EPSG_CODE = target_epsg
        resolution = target_resolution

        # Step A: Read the LAS file and extract points
        las = laspy.read(laz_path)
        lidar_points = np.vstack((las.x, las.y, las.z)).transpose()
        num_points = len(lidar_points)

        x_min, y_min = las.header.mins[0], las.header.mins[1]
        x_max, y_max = las.header.maxs[0], las.header.maxs[1]
        ncol_out = round((x_max - x_min) / resolution)
        nrow_out = round((y_max - y_min) / resolution)

        # Initialize DSM_LAST (set missing values to -999)
        DSM_LAST = np.ones((nrow_out, ncol_out), dtype=np.float32) * (-999)
        print("Step A: Loading done")

        # Step B: Assign each point to the corresponding grid (based on last return)
        for i in range(num_points):
            col = int((lidar_points[i, 0] - x_min) / resolution)
            row = int((y_max - lidar_points[i, 1]) / resolution)
            if 0 <= col < ncol_out and 0 <= row < nrow_out:
                if (
                    DSM_LAST[row, col] < lidar_points[i, 2]
                    and DSM_LAST[row, col] == -999
                ):
                    DSM_LAST[row, col] = lidar_points[i, 2]
                elif DSM_LAST[row, col] > lidar_points[i, 2]:
                    DSM_LAST[row, col] = lidar_points[i, 2]
        print("Step B: DSM (last return) population done")

        # Step C: Interpolate DSM_LAST (convert missing values: -999 → nan)
        DSM_LAST = DSM_LAST.astype("float32")
        DSM_LAST[DSM_LAST == -999] = np.nan
        DSM = interpolation(DSM_LAST, interpolation_method="nearest")
        DSM = DSM.astype("float32")

        print("DSM shape:", DSM.shape)
        if DSM.size == 0:
            raise ValueError(
                "DSM array is empty. Check input LAZ or boundary coordinates."
            )

        crs = rasterio.crs.CRS.from_epsg(EPSG_CODE)
        transform = from_origin(x_min, y_max, resolution, resolution)
        print("Step C: DSM interpolation done")

        # DSM visualization (for debugging)
        lower_bound = np.percentile(DSM, 1)
        upper_bound = np.percentile(DSM, 99)
        plt.figure(figsize=(8, 8), dpi=100)
        plt.imshow(DSM, clim=(lower_bound, upper_bound))
        plt.colorbar()
        plt.title("DSM")
        plt.show()

        # DSM pre-processing: Apply filters
        dsm = minimum_filter(DSM, 3)
        dsm = median_filter(dsm, 5)
        dsm = median_filter(dsm, 5)
        print("Step 0: DSM pre-processing done")

        # Calculate slope using Sobel filter
        sobel_image = sobel_filter(dsm)
        slope_map = np.arctan(sobel_image / (4 * target_resolution)) * (180 / np.pi)
        breakline_map = slope_map >= slope_threshold
        plt.figure(figsize=(8, 8), dpi=100)
        plt.imshow(slope_map)
        plt.title("Slope Map")
        plt.colorbar()
        plt.show()
        print("Step 1: Breakline-map delineation done")

        plt.figure(figsize=(8, 8), dpi=100)
        plt.imshow(breakline_map)
        plt.title("Breakline Map")
        plt.colorbar()
        plt.show()

        # Invert breakline map and set boundaries
        temp = np.uint8(1 - breakline_map)
        temp[:, 0] = 0
        temp[0, :] = 0
        temp[-1, :] = 0
        temp[:, -1] = 0

        # Connected component labeling
        number_of_labels, label_map, stats, centroids = (
            cv2.connectedComponentsWithStats(temp, connectivity=4)
        )
        stats_T = np.transpose(stats)
        area_stat = stats_T[4]

        # Apply RuleA (or RuleB) to extract ground
        if RuleA:
            print("RuleA")
            ground_label = np.argmax(area_stat[1:]) + 1  # Exclude background (label 0)
            ground = (label_map == ground_label).astype(np.uint8)
            obj = 1 - ground
        else:
            print("RuleB")
            bldg_is_rarely_bigger_than_this = 200000 / (target_resolution**2)
            labels_meeting_criteria = np.where(
                area_stat >= bldg_is_rarely_bigger_than_this
            )[0][1:]
            if len(labels_meeting_criteria) == 0:
                ground = np.ones(np.shape(label_map))
            else:
                ground = np.isin(label_map, labels_meeting_criteria)
            obj = 1 - ground

        plt.figure(figsize=(8, 8), dpi=100)
        plt.imshow(obj)
        plt.title("Objects")
        plt.colorbar()
        plt.show()
        print("Step 2: Object identification done")

        # Create DTM by removing objects from DSM
        temp = dsm.copy()
        temp[obj == 1] = np.nan
        dtm = interpolation(temp, interpolation_method="linear")
        if np.sum(np.isnan(dtm)) > 0:
            dtm = interpolation(dtm, interpolation_method="nearest")
        mask = (dtm > DSM) | (np.abs(dtm - DSM) < 0.1)
        dtm[mask] = DSM[mask]
        lower_bound = np.percentile(dtm, 1)
        upper_bound = np.percentile(dtm, 99)
        plt.figure(figsize=(8, 8), dpi=100)
        plt.imshow(dtm, cmap="terrain", clim=(lower_bound, upper_bound))
        plt.colorbar()
        plt.title("DTM")
        plt.show()
        print("Step 3: DTM generation done")

        # DSM/DTM 저장
        out_dsm = os.path.join(session_dir, "DSM_Purdue.tif")
        out_dtm = os.path.join(session_dir, "DTM_Purdue.tif")
        if SAVE:
            with rasterio.open(
                out_dsm,
                "w",
                driver="GTiff",
                height=DSM.shape[0],
                width=DSM.shape[1],
                count=1,
                dtype=DSM.dtype,
                crs=crs,
                transform=transform,
            ) as dst:
                dst.write(DSM, 1)
            with rasterio.open(
                out_dtm,
                "w",
                driver="GTiff",
                height=dtm.shape[0],
                width=dtm.shape[1],
                count=1,
                dtype=dtm.dtype,
                crs=crs,
                transform=transform,
            ) as dst:
                dst.write(dtm, 1)

    return out_dsm, out_dtm, crs, transform, DSM, dtm, DSM_LAST


# -----------------------------------------
# Helper functions for interpolation etc.
# -----------------------------------------
def sobel_filter(img):
    Gx = np.array([[1.0, 0.0, -1.0], [2.0, 0.0, -2.0], [1.0, 0.0, -1.0]])
    Gy = np.array([[1.0, 2.0, 1.0], [0.0, 0.0, 0.0], [-1.0, -2.0, -1.0]])
    gx = conv2(img, Gx, boundary="symm", mode="same")
    gy = conv2(img, Gy, boundary="symm", mode="same")
    return np.sqrt(gx**2 + gy**2)


def scipy_interpolation(img, METHOD):
    x = np.arange(0, img.shape[1])
    y = np.arange(0, img.shape[0])
    img_masked = np.ma.masked_invalid(img)
    xx, yy = np.meshgrid(x, y)
    x1 = xx[~img_masked.mask]
    y1 = yy[~img_masked.mask]
    newarr = img_masked[~img_masked.mask]
    interpolated_img = interpolate.griddata(
        (x1, y1), newarr.ravel(), (xx, yy), method=METHOD
    )
    return interpolated_img


def choose_scale(img_shape):
    if img_shape[0] % 4 == 0 and img_shape[1] % 4 == 0:
        return 4
    elif img_shape[0] % 3 == 0 and img_shape[1] % 3 == 0:
        return 3
    elif img_shape[0] % 2 == 0 and img_shape[1] % 2 == 0:
        return 2
    else:
        return 1


def interpolation(img, interpolation_method="linear"):
    SCALE = choose_scale(img.shape)
    dtm_temp = scipy_interpolation(img[::SCALE, ::SCALE], METHOD=interpolation_method)
    dtm_temp = scipy.ndimage.zoom(dtm_temp, SCALE, order=0)
    new_values_for_nan = np.multiply(np.isnan(img), dtm_temp)
    img_with_nan_replaced = np.copy(img)
    img_with_nan_replaced[np.isnan(img)] = 0
    interpolated_img = img_with_nan_replaced + new_values_for_nan
    return interpolated_img


# -------------------------------------------------
# 3. Building Map Extraction and Saving (2D/3D)
# -------------------------------------------------
def extract_building_maps(
    DSM, dtm, DSM_LAST, crs, transform, target_resolution, session_dir, SAVE=True
):
    """
    Extract building candidate areas using DSM, DTM, and NDHM (DSM - DTM), then generate 2D and 3D building maps
    after morphological and planarity filtering and boundary refinement.

    Parameters:
        DSM, dtm (ndarray): Calculated DSM and DTM arrays.
        DSM_LAST (ndarray): Original DSM (last return) array computed from the LAZ file (used for water classification).
        crs, transform: Raster georeferencing information.
        target_resolution (float): Resolution in meters.
        session_dir (str): Root directory for saving results.
        SAVE (bool): If True, the resulting maps are saved to files.

    Returns:
        out_building_2d, out_building_3d (str): File paths for the generated 2D and 3D building maps.
    """
    # Set parameters
    HT = 1.5  # Height threshold for building candidates
    K1 = 7  # Kernel size for morphological operations (erosion/dilation)
    K2 = 5  # Window size for surface roughness calculation
    RT = 4  # Planarity (roughness) threshold
    DT = 0.1  # Planarity ratio threshold
    K3 = 5  # Dilation kernel size for boundary refining

    # Calculate NDHM (DSM - DTM)
    NDHM = DSM - dtm

    # Building candidate areas: regions where NDHM is greater than HT
    building_candidates = NDHM > HT

    # NDHM visualization
    lower_bound = np.percentile(NDHM, 1)
    upper_bound = np.percentile(NDHM, 99)
    plt.figure(figsize=(8, 8), dpi=100)
    plt.imshow(NDHM, cmap="viridis", clim=(lower_bound, upper_bound))
    plt.colorbar()
    plt.title("NDHM (DSM - DTM)")
    plt.show()

    # --- Operation 1: Water Body Masking ---
    water_mask = classify_water(DSM_LAST, target_resolution=target_resolution)
    building_candidates = building_candidates & ~water_mask
    plt.figure(figsize=(8, 8), dpi=100)
    plt.imshow(water_mask, cmap="Blues")
    plt.colorbar()
    plt.title("Water Body Mask")
    plt.show()

    # --- Operation 2: Morphological Filtering (Opening) ---
    building_candidates = ndimage.binary_erosion(
        building_candidates, structure=np.ones((K1, K1))
    )
    building_candidates = ndimage.binary_dilation(
        building_candidates, structure=np.ones((K1, K1))
    )
    plt.figure(figsize=(8, 8), dpi=100)
    plt.imshow(building_candidates, cmap="viridis")
    plt.colorbar()
    plt.title("Building Candidates (after morphological opening)")
    plt.show()

    # --- Operation 3: Planarity Filtering ---
    roughness_map = calculate_surface_roughness(NDHM, ksz=K2)
    planar_mask = roughness_map < RT
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
        building_candidates.astype(np.uint8)
    )
    sum_planar_pixels = np.bincount(labels.ravel(), weights=planar_mask.ravel())
    total_pixels = stats[:, cv2.CC_STAT_AREA]
    with np.errstate(divide="ignore", invalid="ignore"):
        planarity_ratios = np.where(
            total_pixels != 0, sum_planar_pixels / total_pixels, 0
        )
    valid_labels = np.where(planarity_ratios >= DT)[0]
    filtered_building_mask = np.isin(labels, valid_labels)
    building_candidates = building_candidates * filtered_building_mask
    plt.figure(figsize=(8, 8), dpi=100)
    plt.imshow(building_candidates, cmap="viridis")
    plt.colorbar()
    plt.title("Building Candidates (after planarity filtering)")
    plt.show()

    # --- Operation 4: Boundary Refining ---
    building_2d_map = cv2.dilate(
        building_candidates.astype(np.uint8), np.ones((K3, K3))
    )
    building_3d_map = np.zeros_like(NDHM)
    NDHM_filtered = median_filter(NDHM, size=5)
    building_3d_map[building_2d_map == 1] = NDHM_filtered[building_2d_map == 1]

    # Custom colormap for 2D building map
    colors = [(1, 1, 0.95), (0.9, 0.6, 0.6)]
    cm = mcolors.LinearSegmentedColormap.from_list("custom", colors, N=2)
    plt.figure(figsize=(10, 10), dpi=120)
    plt.imshow(building_2d_map, cmap=cm)
    plt.colorbar()
    plt.title("2D Building Map")
    plt.show()

    if np.any(building_3d_map > 0):
        lower_bound_3d = np.percentile(building_3d_map[building_3d_map > 0], 1)
    else:
        lower_bound_3d = 0
    upper_bound_3d = np.percentile(building_3d_map, 99)
    plt.figure(figsize=(10, 10), dpi=120)
    plt.imshow(building_3d_map, cmap="viridis", clim=(lower_bound_3d, upper_bound_3d))
    plt.colorbar()
    plt.title("3D Building Map")
    plt.show()

    # Save the building maps
    out_building_2d = os.path.join(session_dir, "2DBuilding_Purdue.tif")
    out_building_3d = os.path.join(session_dir, "3DBuilding_Purdue.tif")
    if SAVE:
        with rasterio.open(
            out_building_2d,
            "w",
            driver="GTiff",
            height=building_2d_map.shape[0],
            width=building_2d_map.shape[1],
            count=1,
            dtype=building_2d_map.dtype,
            crs=crs,
            transform=transform,
        ) as dst:
            dst.write(building_2d_map, 1)
        with rasterio.open(
            out_building_3d,
            "w",
            driver="GTiff",
            height=building_3d_map.shape[0],
            width=building_3d_map.shape[1],
            count=1,
            dtype=building_3d_map.dtype,
            crs=crs,
            transform=transform,
        ) as dst:
            dst.write(building_3d_map, 1)

    print("Building extraction complete!")
    return out_building_2d, out_building_3d


# -----------------------------------------
# Additional helper functions for building extraction
# -----------------------------------------
def calculate_density_map(dsm, window_size=9):
    """
    Calculate the valid data density in local areas using the distribution of missing values in DSM.
    """
    valid_mask = ~np.isnan(dsm)
    kernel = np.ones((window_size, window_size))
    local_sums = conv2(valid_mask.astype(float), kernel, mode="same")
    return local_sums / (window_size**2)


def classify_water(
    dsm, target_resolution=0.5, threshold=2, min_area=1000, buffer_distance=5
):
    """
    Extract water bodies from DSM data.

    Parameters:
        dsm (ndarray): DSM data array.
        target_resolution (float): Resolution in meters.
        threshold (float): Threshold multiplier for standard deviation.
        min_area (int): Minimum area (in square meters) to consider.
        buffer_distance (float): Buffer distance (in meters) for dilation.

    Returns:
        (ndarray): Binary water body mask.
    """
    densities = calculate_density_map(dsm)
    avg_density = np.mean(densities)
    std_density = np.std(densities)
    # Consider regions with density lower than (mean - threshold*std) as water bodies
    potential_water_body = densities < (avg_density - threshold * std_density)
    # Remove regions smaller than the minimum area
    min_pixels = int(min_area / (target_resolution**2))
    potential_water_body = remove_small_objects(
        potential_water_body, min_size=min_pixels
    )
    # Apply buffer (dilation)
    buffer_pixels = int(buffer_distance / target_resolution)
    selem = square(int(buffer_pixels / target_resolution + 1))
    potential_water_body = dilation(potential_water_body, footprint=selem)
    return potential_water_body


def sliding_uniq_count(a, BSZ):
    """
    For array 'a', compute the number of unique values within a sliding window of size BSZ.
    """
    a_slid4D = view_as_windows(a, BSZ)
    a_slid2D = np.sort(a_slid4D.reshape(-1, np.prod(BSZ)), axis=1)
    unique_counts = (a_slid2D[:, 1:] != a_slid2D[:, :-1]).sum(axis=1) + 1
    out_shp = np.asarray(a.shape) - np.asarray(BSZ) + 1
    return unique_counts.reshape(out_shp)


def calculate_surface_roughness(ndhm, ksz=5):
    """
    Calculate surface roughness using the number of unique values in a local area of the NDHM.

    Parameters:
        ndhm (ndarray): NDHM data array.
        ksz (int): Kernel size for the sliding window.

    Returns:
        (ndarray): Surface roughness map.
    """
    r = int(np.floor(ksz / 2))
    padded_ndhm = np.pad(ndhm, ((r, r), (r, r)), mode="constant")
    padded_ndhm = np.uint8(padded_ndhm)
    roughness_map = sliding_uniq_count(padded_ndhm, [ksz, ksz])
    return roughness_map


# -----------------------------------------
# End of building_raster.py
# -----------------------------------------
