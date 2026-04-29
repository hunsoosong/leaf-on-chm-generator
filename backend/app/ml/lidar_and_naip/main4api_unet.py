import json
import os
from typing import List, Tuple

import geopandas as gpd
import pdal
import rasterio
import rasterio.mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
from shapely.geometry import box

from app.ml.building_raster import (
    generate_raw_laz,
    generate_dsm_dtm,
    extract_building_maps,
)
from app.ml.lidar_and_naip.my_functions import (
    generate_ndhm,
    save_combined_patches,
    merge_patches,
    resample_to_reference,
    remove_buildings_from_final2,
)
from app.ml.lidar_and_naip.model import (
    load_trained_model,
    load_test_images,
    generate_and_save_images,
)


# ====================
# 1. Data preparation, DTM/DSM generation
# ====================
def process_dtm_dsm(
    boundary_coordinates: List[float],
    session_dir: str,
    ept_id: str,
    ept_url: str,
    ept_epsg: int,
) -> Tuple[str, str]:
    """
    DTM / DSM generation

    Parameters:
        boundary_coordinates (list): AOI boundary coordinates
        session_dir (str): output save directory
        ept_id (str): dateset ID
        ept_url (str): dateset URL
        ept_epsg (str): EPSG code
    """
    # ====================
    # coordinate trasformation
    # ====================
    # bbox_geom = box(*[coord for pair in boundary_coordinates[0] for coord in pair])
    bbox_geom = box(
        boundary_coordinates[0],
        boundary_coordinates[1],
        boundary_coordinates[2],
        boundary_coordinates[3],
    )
    poly = gpd.GeoDataFrame(geometry=[bbox_geom], crs="EPSG:4326")
    poly = poly.to_crs(ept_epsg)
    bbox_coords = poly.total_bounds.tolist()
    print("Reprojected Bounding Box:", bbox_coords)

    # ====================
    # DTM generation
    # ====================
    # out_dtm_laz = os.path.join(session_dir, "clip_dtm.laz")
    out_dtm_tif = os.path.join(session_dir, "clip_dtm.tif")

    dtm_pipeline = {
        "pipeline": [
            {
                "bounds": f"([{bbox_coords[0]}, {bbox_coords[2]}], [{bbox_coords[1]}, {bbox_coords[3]}])",
                "filename": ept_url,
                "type": "readers.ept",
                "tag": "readdata",
            },
            # {
            #     "limits": "Classification![7:7]",
            #     "type": "filters.range",
            #     "tag": "nonoise",
            # },
            # {
            #     "assignment": "Classification[:]=0",
            #     "type": "filters.assign",
            #     "tag": "wipeclasses",
            # },
            {
                "out_srs": f"EPSG:{ept_epsg}",
                "type": "filters.reprojection",
                "tag": "reprojectUTM",
            },
            # {"type": "filters.smrf", "tag": "groundify"},
            {
                "limits": "Classification[2:2]",
                "type": "filters.range",
                "tag": "classify",
            },
            # {
            #     "filename": out_dtm_laz,
            #     "inputs": ["classify"],
            #     "type": "writers.las",
            #     "tag": "writerslas",
            # },
            {
                "filename": out_dtm_tif,
                "gdalopts": "tiled=yes,compress=deflate",
                "inputs": ["classify"],
                "nodata": -9999,
                "output_type": "idw",
                "resolution": 1,
                "type": "writers.gdal",
                "window_size": 30,
                "override_srs": f"EPSG:{ept_epsg}",
            },
        ]
    }

    print("Running DTM Pipeline...")
    os.makedirs(session_dir, exist_ok=True)
    pdal.Pipeline(json.dumps(dtm_pipeline)).execute()
    print(f"✅ DTM Generated: {out_dtm_tif}")

    # ====================
    # DSM generation
    # ====================
    out_dsm_laz = os.path.join(session_dir, "clip_dsm.laz")
    out_dsm_tif = os.path.join(session_dir, "clip_dsm.tif")

    dsm_pipeline = {
        "pipeline": [
            {
                "bounds": f"([{bbox_coords[0]}, {bbox_coords[2]}], [{bbox_coords[1]}, {bbox_coords[3]}])",
                "filename": ept_url,
                "type": "readers.ept",
                "tag": "readdata",
            },
            {
                "assignment": "Classification[:]=0",
                "type": "filters.assign",
                "tag": "wipeclasses",
            },
            {
                "out_srs": f"EPSG:{ept_epsg}",
                "type": "filters.reprojection",
                "tag": "reprojectUTM",
            },
            {
                "filename": out_dsm_laz,
                "inputs": ["reprojectUTM"],
                "type": "writers.las",
                "tag": "savelaz",
            },
            {
                "filename": out_dsm_tif,
                "gdalopts": "tiled=yes,compress=deflate",
                "inputs": ["savelaz"],
                "nodata": -9999,
                "output_type": "max",
                "resolution": 1,
                "type": "writers.gdal",
                "window_size": 6,
                "override_srs": f"EPSG:{ept_epsg}",
            },
        ]
    }

    print("Running DSM Pipeline...")
    pdal.Pipeline(json.dumps(dsm_pipeline)).execute()
    print(f"✅ DSM Generated: {out_dsm_tif}")

    return out_dtm_tif, out_dsm_tif


def crop_naip(
    naip_url: str, boundary_coordinates: List[float], session_dir: str
) -> str:
    """
    Crop NAIP data using AOI boundary coordinates

    Parameters:
        naip_url (str): NAIP data URL
        boundary_coordinates (list): AOI boundary coordinates
        session_dir (str): result save directory

    Returns:
        cropped_naip_tif (str): cropped naip file directory
    """
    cropped_naip_tif = os.path.join(session_dir, "cropped_naip.tif")

    # Bounding Box to Shapely Polygon
    # bbox_geom = box(*[coord for pair in boundary_coordinates[0] for coord in pair])
    bbox_geom = box(
        boundary_coordinates[0],
        boundary_coordinates[1],
        boundary_coordinates[2],
        boundary_coordinates[3],
    )
    poly = gpd.GeoDataFrame(geometry=[bbox_geom], crs="EPSG:4326")

    with rasterio.open(naip_url) as src:
        poly = poly.to_crs(src.crs)  # coordinate transformation
        out_image, out_transform = rasterio.mask.mask(src, poly.geometry, crop=True)
        out_meta = src.meta.copy()
        out_meta.update(
            {
                "driver": "GTiff",
                "height": out_image.shape[1],
                "width": out_image.shape[2],
                "transform": out_transform,
            }
        )

    with rasterio.open(cropped_naip_tif, "w", **out_meta) as dest:
        dest.write(out_image)

    print(f"✅ cropped NAIP save completed: {cropped_naip_tif}")
    return cropped_naip_tif


def align_naip_to_dtm(cropped_naip_tif: str, dtm_tif: str, session_dir: str) -> str:
    """
    align cropped naip into dtm shape

    Parameters:
        cropped_naip_tif (str): cropped naip directory
        dtm_tif (str): DTM file directory
        session_dir (str): output save directory

    Returns:
        aligned_naip_tif (str): aligned naip directory
    """
    aligned_naip_tif = os.path.join(session_dir, "aligned_naip.tif")

    # DTM 크기 및 좌표계 가져오기
    with rasterio.open(dtm_tif) as dtm:
        dtm_width, dtm_height = dtm.width, dtm.height
        dtm_transform = dtm.transform
        dtm_crs = dtm.crs

    with rasterio.open(cropped_naip_tif) as src:
        transform, width, height = calculate_default_transform(
            src.crs, dtm_crs, dtm_width, dtm_height, *src.bounds
        )

        new_meta = src.meta.copy()
        new_meta.update(
            {
                "crs": dtm_crs,
                "transform": dtm_transform,
                "width": dtm_width,
                "height": dtm_height,
            }
        )

        with rasterio.open(aligned_naip_tif, "w", **new_meta) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=dtm_transform,
                    dst_crs=dtm_crs,
                    resampling=Resampling.nearest,  # 보간법: nearest (선택 가능)
                )

    print(f"✅ NAIP align completed: {aligned_naip_tif}")
    return aligned_naip_tif


def process_naip(
    boundary_coordinates: List[float],
    session_dir: str,
    naip_id: str,
    naip_url: str,
    naip_epsg: int,
    dtm_tif: str,
) -> str:
    """
    NAIP crop + aligning

    Parameters:
        boundary_coordinates (list): AOI boundary coordinate
        session_dir (str): output save directory
        naip_id (str): NAIP dataset ID
        naip_url (str): NAIP dataset URL
        naip_epsg (str): NAIP EPSG code
        dtm_tif (str): DTM file directory

    Returns:
        aligned_naip_tif (str): final NAIP file directory
    """
    print("🔹 NAIP data crop and aligning...")

    # Step 1: NAIP 크롭
    cropped_naip = crop_naip(naip_url, boundary_coordinates, session_dir)

    # Step 2: NAIP 크기 및 좌표계 정렬 (DTM 기준)
    aligned_naip = align_naip_to_dtm(cropped_naip, dtm_tif, session_dir)

    print(f"✅ final NAIP completed: {aligned_naip}")
    return aligned_naip


def process_ndhm_and_model(
    dtm_tif: str, dsm_tif: str, naip_tif: str, session_dir: str, model_path: str
) -> Tuple[str, str, str]:
    """
    NDHM generation, U-Net model run

    Parameters:
        dtm_tif (str): DTM file directory
        dsm_tif (str): DSM file directory
        naip_tif (str): aligned NAIP file directory
        session_dir (str): API session directory
        model_path (str): trained U-Net model directory (.h5)

    Returns:
        output_ndhm (str): generated NDHM file directory
        aligned_naip (str): (DTM aligned) NAIP file directory
        merged_output (str): final merged generated CHM file directory
    """
    print("🔹 NDHM generation, model run...")

    # path
    output_ndhm = os.path.join(session_dir, "output_ndhm.tif")
    patch_folder = os.path.join(session_dir, "patches")
    chm_patch_folder = os.path.join(patch_folder, "chm_patches")  # CHM patch folder
    naip_patch_folder = os.path.join(patch_folder, "naip_patches")  # NAIP patch folder
    combined_patch_folder = os.path.join(
        patch_folder, "combined_patches"
    )  # CHM + NAIP combined patch folder
    output_model = os.path.join(
        session_dir, "gen_patches"
    )  # generated CHM patch folder
    merged_output = os.path.join(
        session_dir, "merged_gen_chm.tif"
    )  # merged generated CHM directory

    # ✅ Step 0: output folder check
    os.makedirs(os.path.dirname(output_ndhm), exist_ok=True)
    os.makedirs(chm_patch_folder, exist_ok=True)
    os.makedirs(naip_patch_folder, exist_ok=True)
    os.makedirs(combined_patch_folder, exist_ok=True)
    os.makedirs(output_model, exist_ok=True)
    os.makedirs(os.path.dirname(merged_output), exist_ok=True)

    # ✅ Step 1: NDHM generate
    print("📌 Step 1: Generating NDHM...")
    generate_ndhm(dsm_tif, dtm_tif, output_ndhm)

    # ✅ Step 2: CHM + NAIP patch generation
    print("📌 Step 2: Creating Combined CHM+NAIP Patches...")
    save_combined_patches(output_ndhm, naip_tif, combined_patch_folder, patch_size=256)

    # ✅ Step 3: model run and generate
    print("📌 Step 3: Running U-Net Model for CHM Prediction...")
    model = load_trained_model(model_path)
    test_images, file_names = load_test_images(
        combined_patch_folder, combined_patch_folder
    )
    generate_and_save_images(
        model, test_images, file_names, combined_patch_folder, output_model
    )

    # ✅ Step 4: merge output
    print("📌 Step 4: Merging Predicted CHM Patches...")
    merge_patches(output_model, merged_output)

    print(f"✅ CHM predict completed: {merged_output}")
    return output_ndhm, naip_tif, merged_output


def your_main_model_function2(
    boundary_coordinates: List[float],
    session_dir: str,
    ept_id: str,
    ept_url: str,
    ept_epsg: int,
    naip_id: str,
    naip_url: str,
    naip_epsg: int,
    model_path: str,
) -> Tuple[str, str, str, str, str, str]:
    """
    API

    Parameters:
        boundary_coordinates (list): AOI boundary coordinates
        session_dir (str): session directory
        ept_id (str): DSM dataset ID
        ept_url (str): DSM dataset URL
        ept_epsg (str): DSM EPSG code
        naip_id (str): NAIP dataset ID
        naip_url (str): NAIP dataset URL
        naip_epsg (str): NAIP EPSG code
        model_path (str): trained U-Net model file path (.h5)

    Returns:
        aligned_naip (str): aligned NAIP file path (DTM aligned)
        output_ndhm (str): processed NDHM file path
        final_chm (str): final merged generated CHM file path
        resampled_building_2d (str): resampled 2D building map file path
        resampled_building_3d (str): resampled 3D building map file path
        final_output_nobuild (str): final CHM file with buildings removed
    """
    print("🔹 [STEP 1] DSM & DTM generation")
    dtm_tif, dsm_tif = process_dtm_dsm(
        boundary_coordinates, session_dir, ept_id, ept_url, ept_epsg
    )

    print("🔹 [STEP 2] NAIP preprocess (crop and align)")
    aligned_naip_tif = process_naip(
        boundary_coordinates, session_dir, naip_id, naip_url, naip_epsg, dtm_tif
    )

    print("🔹 [STEP 3] NDHM generation and model run")
    output_ndhm, aligned_naip, final_chm = process_ndhm_and_model(
        dtm_tif, dsm_tif, aligned_naip_tif, session_dir, model_path
    )

    # ====================
    # 4. Building Raster processing
    # ====================
    print("🔹 [STEP 4] Building Raster processing")
    # Calculate bounding box for building raster
    bbox_geom = box(
        boundary_coordinates[0],
        boundary_coordinates[1],
        boundary_coordinates[2],
        boundary_coordinates[3],
    )
    poly = gpd.GeoDataFrame(geometry=[bbox_geom], crs="EPSG:4326")
    poly = poly.to_crs(ept_epsg)
    bbox_coords = poly.total_bounds.tolist()
    print("Reprojected Bounding Box for Building Raster:", bbox_coords)

    # Generate raw LAZ file using ept_url
    raw_laz = generate_raw_laz(
        ept_url, bbox_coords, target_epsg=ept_epsg, session_dir=session_dir
    )

    # Generate DSM/DTM and building maps (resolution 0.5m)
    out_dsm_br, out_dtm_br, crs_br, transform_br, DSM_br, dtm_br, DSM_LAST = (
        generate_dsm_dtm(
            raw_laz,
            target_resolution=0.5,
            target_epsg=ept_epsg,
            session_dir=session_dir,
        )
    )
    building_2d, building_3d = extract_building_maps(
        DSM_br,
        dtm_br,
        DSM_LAST,
        crs_br,
        transform_br,
        target_resolution=0.5,
        session_dir=session_dir,
        SAVE=True,
    )

    # Resample building maps to match final CHM reference
    resampled_building_2d = os.path.join(session_dir, "resampled_building_2d.tif")
    resampled_building_3d = os.path.join(session_dir, "resampled_building_3d.tif")
    resample_to_reference(
        building_2d, final_chm, resampled_building_2d, resample_method="nearest"
    )
    resample_to_reference(
        building_3d, final_chm, resampled_building_3d, resample_method="nearest"
    )

    # Remove buildings from final CHM using building maps
    final_output_nobuild = os.path.join(session_dir, "final_output_nobuild.tif")
    remove_buildings_from_final2(
        final_chm,
        resampled_building_2d,
        resampled_building_3d,
        final_output_nobuild,
        tolerance=3.0,
    )

    print(f"✅ NDHM: {output_ndhm}")
    print(f"✅ Final CHM: {final_chm}")
    print(f"✅ Resampled 2D Building Map: {resampled_building_2d}")
    print(f"✅ Resampled 3D Building Map: {resampled_building_3d}")
    print(f"✅ Final Output with Building Removal: {final_output_nobuild}")

    return (
        final_chm,
        output_ndhm,
        resampled_building_2d,
        resampled_building_3d,
        final_output_nobuild,
        aligned_naip_tif,
    )
