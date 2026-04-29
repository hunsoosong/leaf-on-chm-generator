import os
import uuid
from typing import Any, Dict, Optional

import numpy as np
from fastapi import Body, FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from geojson_pydantic import Feature, Polygon
from pystac_client import Client
from starlette.middleware.sessions import SessionMiddleware

from app.db.crud import add_task, get_task
from app.celery.tasks import run_lidar_only_model, run_lidar_and_naip_model
from app.schemas.datasets import (
    DatasetsResponse,
    LidarDatasetItem,
    ModelResponse,
    NaipDatasetItem,
)
from app.schemas.tasks import Task
from app.utils import generate_secret_key, is_aoi_too_large

AOI_AREA_LIMIT = os.environ.get("AOI_AREA_LIMIT", 1000000)

app = FastAPI(title="Leaf-on Generator")


app.add_middleware(
    SessionMiddleware, secret_key=os.environ.get("SECRET_KEY", generate_secret_key())
)

app.mount("/static", StaticFiles(directory="/static"), name="static")


@app.get("/api/health", status_code=status.HTTP_200_OK)
def check_health() -> Any:
    return {"status": "healthy"}


@app.get("/api/check_status", response_model=Optional[Task])
def get_session_status(session_id: str) -> Any:
    task = get_task(session_id=session_id)
    return task


@app.post("/api/datasets", response_model=DatasetsResponse)
def find_datasets_in_aoi(aoi: Feature[Polygon, Dict]) -> Any:
    # Check for required geometry
    if not aoi.geometry or aoi.geometry.type.lower() != "polygon":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AOI must include polygon geometry",
        )

    # Get bounding box from polygon coordinates
    boundary_arr = np.array(aoi.geometry.coordinates[0])
    bounding_box = [
        boundary_arr[:, 0].min(),
        boundary_arr[:, 1].min(),
        boundary_arr[:, 0].max(),
        boundary_arr[:, 1].max(),
    ]

    # Connect to STAC API
    client = Client.open("https://stac-api.d2s.org")

    # Search 3DEP collection
    search_3dep = client.search(max_items=10, collections=["3dep"], bbox=bounding_box)

    # Search NAIP collection
    search_naip = client.search(max_items=10, collections=["naip"], bbox=bounding_box)

    # Create payload with dataset IDs and URLs
    payload = DatasetsResponse(
        point_cloud=[
            {
                "id": item.id,
                "bbox": item.bbox,
                "epsg": item.properties.get("proj:epsg") or -1,
                "href": item.assets["ept.json"].href,
            }
            for item in search_3dep.items()
        ],
        raster=[
            {
                "id": item.id,
                "bbox": item.bbox,
                "epsg": item.properties.get("proj:epsg") or -1,
                "gsd": item.properties.get("gsd") or -1,
                "href": item.assets["image"].href,
            }
            for item in search_naip.items()
        ],
    )

    return payload


@app.post("/api/model", response_model=ModelResponse)
def run_3dep_model(
    aoi: Feature[Polygon, Dict],
    lidar: LidarDatasetItem,
    model: str = Body(default="lidar"),
    naip: Optional[NaipDatasetItem] = None,
) -> Any:
    # Verify aoi is within 1,000,000 square meter area limit
    if is_aoi_too_large(aoi):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Area of interest cannot exceed {AOI_AREA_LIMIT} square meters.",
        )

    # Create session ID
    session_id = str(uuid.uuid4())

    # Add task to database
    add_task(session_id=session_id, status="pending")

    # Create folder in static directory for session
    session_dir = os.path.join("/static", session_id)
    if not os.path.isdir(session_dir):
        os.makedirs(session_dir)

    # Check for required geometry
    if not aoi.geometry or aoi.geometry.type.lower() != "polygon":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AOI must include polygon geometry",
        )

    # Get bounding box from polygon coordinates
    boundary_arr = np.array(aoi.geometry.coordinates[0])
    bounding_box = [
        boundary_arr[:, 0].min(),
        boundary_arr[:, 1].min(),
        boundary_arr[:, 0].max(),
        boundary_arr[:, 1].max(),
    ]
    # Get EPT ID, URL, and EPSG
    ept_id = lidar.id
    ept_url = str(lidar.href)
    ept_epsg = lidar.epsg

    # Get NAIP properties if Lidar + Spectral selected
    if model == "both" and naip:
        naip_id = naip.id
        naip_url = str(naip.href)
        naip_epsg = naip.epsg
        naip_gsd = naip.gsd

    # Run model here
    if model == "lidar":
        print("Running lidar_model...")
        model_path = os.path.join("/app", "app", "ml", "test_oct2_.h5")

        run_lidar_only_model.apply_async(
            args=(
                bounding_box,
                session_id,
                session_dir,
                ept_id,
                ept_url,
                ept_epsg,
                model_path,
            )
        )

    elif model == "both":
        print("Running lidar_and_naip_model...")
        model_path = os.path.join("/app", "app", "ml", "best_naip_unet_model.h5")

        run_lidar_and_naip_model.apply_async(
            args=(
                bounding_box,
                session_id,
                session_dir,
                ept_id,
                ept_url,
                ept_epsg,
                naip_id,
                naip_url,
                naip_epsg,
                model_path,
            )
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selected model must be 'lidar' or 'both'",
        )

    response = JSONResponse(content={"session_id": session_id})
    response.set_cookie(key="session_id", value=session_id, httponly=True)

    return response
