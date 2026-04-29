from typing import List

import rasterio

from app.celery.celery_app import celery_app
from app.db.crud import update_task
from app.ml.lidar.main4api import your_main_model_function as lidar_model
from app.ml.lidar_and_naip.main4api_unet import (
    your_main_model_function2 as lidar_and_naip_model,
)
from app.schemas.datasets import ModelResponse
from app.utils import get_file_size_in_bytes


@celery_app.task(name="lidar-only-task")
def run_lidar_only_model(
    bounding_box: List[float],
    session_id: str,
    session_dir: str,
    ept_id: str,
    ept_url: str,
    ept_epsg: int,
    model_path: str,
) -> None:
    # Update status in db
    update_task(session_id=session_id, status="running")

    try:
        # Run model
        ndhm_path, chm_path, building_2d_path, building_3d_path, final_output_path = (
            lidar_model(
                bounding_box, session_dir, ept_id, ept_url, ept_epsg, model_path
            )
        )
    except Exception as e:
        print(str(e))
        update_task(session_id=session_id, status="error")
        return None

    try:
        # Get rescale values for chm
        with rasterio.open(chm_path) as src:
            band1 = src.read(1)
            chm_min_value = band1.min()
            chm_max_value = band1.max()
    except Exception as e:
        print(str(e))
        update_task(session_id=session_id, status="error")
        return None

    # Create JSON payload
    payload = ModelResponse(
        chm={
            "href": chm_path,
            "rescale": f"rescale={chm_min_value},{chm_max_value}",
            "file_size": get_file_size_in_bytes(chm_path),
        },
        ndhm={
            "href": ndhm_path,
            "rescale": f"rescale={chm_min_value},{chm_max_value}",
            "file_size": get_file_size_in_bytes(ndhm_path),
        },
        building2d={
            "href": building_2d_path,
            "rescale": "rescale=0,1",
            "file_size": get_file_size_in_bytes(building_2d_path),
        },
        building3d={
            "href": building_3d_path,
            "rescale": f"rescale={chm_min_value},{chm_max_value}",
            "file_size": get_file_size_in_bytes(building_3d_path),
        },
        chmv2={
            "href": final_output_path,
            "rescale": f"rescale={chm_min_value},{chm_max_value}",
            "file_size": get_file_size_in_bytes(final_output_path),
        },
        naip=None,
        session_id=session_id,
    ).model_dump_json()

    # Update status and set results in db
    update_task(session_id=session_id, status="finished", payload=payload)


@celery_app.task(name="lidar-and-naip-task")
def run_lidar_and_naip_model(
    bounding_box: List[float],
    session_id: str,
    session_dir: str,
    ept_id: str,
    ept_url: str,
    ept_epsg: int,
    naip_id: str,
    naip_url: str,
    naip_epsg: int,
    model_path: str,
) -> None:
    # Update status in db
    update_task(session_id=session_id, status="running")

    try:
        # Run model
        (
            chm_path,
            ndhm_path,
            building_2d_path,
            building_3d_path,
            final_output_path,
            naip_path,
        ) = lidar_and_naip_model(
            bounding_box,
            session_dir,
            ept_id,
            ept_url,
            ept_epsg,
            naip_id,
            naip_url,
            naip_epsg,
            model_path,
        )
    except Exception as e:
        print(str(e))
        update_task(session_id=session_id, status="error")

    try:
        # Get rescale values for chm
        with rasterio.open(chm_path) as src:
            band1 = src.read(1)
            chm_min_value = band1.min()
            chm_max_value = band1.max()

        # Get rescale values for naip
        with rasterio.open(naip_path) as src:
            band1 = src.read(1)
            band2 = src.read(2)
            band3 = src.read(3)
            band1_min_value = band1.min()
            band1_max_value = band1.max()
            band2_min_value = band2.min()
            band2_max_value = band2.max()
            band3_min_value = band3.min()
            band3_max_value = band3.max()
    except Exception as e:
        print(str(e))
        update_task(session_id=session_id, status="error")

    # Create JSON payload
    payload = ModelResponse(
        chm={
            "href": chm_path,
            "rescale": f"rescale={chm_min_value},{chm_max_value}",
            "file_size": get_file_size_in_bytes(chm_path),
        },
        ndhm={
            "href": ndhm_path,
            "rescale": f"rescale={chm_min_value},{chm_max_value}",
            "file_size": get_file_size_in_bytes(ndhm_path),
        },
        building2d={
            "href": building_2d_path,
            "rescale": "rescale=0,1",
            "file_size": get_file_size_in_bytes(building_2d_path),
        },
        building3d={
            "href": building_3d_path,
            "rescale": f"rescale={chm_min_value},{chm_max_value}",
            "file_size": get_file_size_in_bytes(building_3d_path),
        },
        chmv2={
            "href": final_output_path,
            "rescale": f"rescale={chm_min_value},{chm_max_value}",
            "file_size": get_file_size_in_bytes(final_output_path),
        },
        naip={
            "href": naip_path,
            "rescale": f"bidx=1&bidx=2&bidx=3&rescale={band1_min_value},{band1_max_value}&rescale={band2_min_value},{band2_max_value}&rescale={band3_min_value},{band3_max_value}",
            "file_size": get_file_size_in_bytes(naip_path),
        },
        session_id=session_id,
    ).model_dump_json()

    # Update status and set results in db
    update_task(session_id=session_id, status="finished", payload=payload)
