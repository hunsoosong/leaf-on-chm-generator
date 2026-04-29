import json
import os
from typing import List, Tuple

import geopandas as gpd
import pdal
from shapely.geometry import box

from app.ml.building_raster import (
    generate_raw_laz,
    generate_dsm_dtm,
    extract_building_maps,
)
from app.ml.lidar.model import (
    load_trained_pix2pix_model,
    generate_and_save_pix2pix_images,
)
from app.ml.lidar.my_functions import (
    generate_ndhm,
    save_patches,
    merge_patches,
    update_coordinate_system,
    resample_to_reference,
    remove_buildings_from_final2,
)


# ====================
# 1. 데이터 준비 및 DTM/DSM 생성
# ====================
def process_dtm_dsm(
    boundary_coordinates: List[float],
    session_dir: str,
    ept_id: str,
    ept_url: str,
    ept_epsg: int,
) -> Tuple[str, str]:
    """
    DTM 및 DSM 생성

    Parameters:
        boundary_coordinates (list): AOI 경계 좌표
        session_dir (str): 결과 저장 경로
        ept_id (str): 데이터셋 ID
        ept_url (str): 데이터셋 URL
        ept_epsg (str): EPSG 코드
    """
    # ====================
    # 좌표 변환
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
    # DTM 생성 (Jupyter Notebook 방식)
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
    # DSM 생성 (기존 방식 유지)
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


# ====================
# 2. NDHM generation and Pix2Pix model execution
# ====================
def process_ndhm_and_model(
    dtm: str, dsm: str, session_dir: str, model_path: str
) -> Tuple[str, str]:
    """
    NDHM generation and Pix2Pix model application
    """
    ndhm_output = os.path.join(session_dir, "output_ndhm.tif")
    patch_folder = os.path.join(session_dir, "patches")
    output_model = os.path.join(session_dir, "gen_patches")
    merged_output = os.path.join(session_dir, "merged_gen_chm.tif")
    updated_output = os.path.join(session_dir, "updated_gen_patches")

    # NDHM generate
    generate_ndhm(dsm, dtm, ndhm_output)
    save_patches(ndhm_output, patch_folder, patch_size=256)

    # Pix2Pix model application
    model = load_trained_pix2pix_model(model_path)
    generate_and_save_pix2pix_images(model, patch_folder, output_model)
    update_coordinate_system(patch_folder, output_model, updated_output)
    merge_patches(updated_output, merged_output)

    return ndhm_output, merged_output


# ====================
# 3. main execution
# ====================
def your_main_model_function(
    boundary_coordinates: List[float],
    session_dir: str,
    ept_id: str,
    ept_url: str,
    ept_epsg: int,
    model_path: str,
) -> Tuple[str, str, str, str, str]:
    # 1m resolution DTM/DSM, NDHM, CHM generation
    dtm, dsm = process_dtm_dsm(
        boundary_coordinates, session_dir, ept_id, ept_url, ept_epsg
    )
    ndhm_output, final_output = process_ndhm_and_model(
        dtm, dsm, session_dir, model_path
    )

    # Bounding Box to Shapely Polygon
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
    print("Reprojected Bounding Box for Building Raster:", bbox_coords)

    # raw laz generation using ept_url (no preprocessing)
    raw_laz = generate_raw_laz(
        ept_url, bbox_coords, target_epsg=ept_epsg, session_dir=session_dir
    )

    # 0.5m resolution DSM/DTM, 2d/3d building raster generation
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

    # resampling building_2d building_3d raster (to match final output resolution (1m))
    resampled_building_2d = os.path.join(session_dir, "resampled_building_2d.tif")
    resampled_building_3d = os.path.join(session_dir, "resampled_building_3d.tif")

    resample_to_reference(
        building_2d, final_output, resampled_building_2d, resample_method="nearest"
    )
    resample_to_reference(
        building_3d, final_output, resampled_building_3d, resample_method="nearest"
    )

    # refined building removal: removing building from final_output using 3D building raster
    final_output_nobuild = os.path.join(session_dir, "final_output_nobuild.tif")
    remove_buildings_from_final2(
        final_output,
        resampled_building_2d,
        resampled_building_3d,
        final_output_nobuild,
        tolerance=3.0,
    )

    print(f"✅ NDHM: {ndhm_output}")
    print(f"✅ Final Leaf-on CHM: {final_output}")
    print(f"✅ Resampled 2D Building Map: {resampled_building_2d}")
    print(f"✅ Resampled 3D Building Map: {resampled_building_3d}")
    print(f"✅ Final Output with Refined Building Removal: {final_output_nobuild}")

    return (
        ndhm_output,
        final_output,
        resampled_building_2d,
        resampled_building_3d,
        final_output_nobuild,
    )
