import base64
import os
import secrets
from typing import Dict

import geopandas as gpd
from geojson_pydantic import Feature, Polygon
from pyproj import CRS
from shapely.geometry import shape


def generate_secret_key() -> str:
    """Creates secret key based on a random byte string with 64 bytes.

    Returns:
        str: Base64 encoded secret key converted to a string.
    """
    # Create random byte string with 64 bytes
    secret_key_bytes = secrets.token_bytes(64)

    # Base64 encode secret_key and convert to str object
    secret_key_str = base64.b64encode(secret_key_bytes).decode("utf-8")

    return secret_key_str


def get_file_size_in_bytes(filepath: str) -> float:
    """Returns the size of the file at file_path in bytes.

    Args:
        filepath (str): The path to the file.

    Raises:
        FileNotFoundError: If the file does not exist.

    Returns:
        float: The size of the file in bytes.
    """

    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"The file '{filepath}' does not exist.")

    return os.path.getsize(filepath)


def is_aoi_too_large(aoi: Feature[Polygon, Dict]) -> bool:
    """Computes the area of a GeoJSON polygon in square meters by projecting it
    to an appropriate UTM zone. Returns whether the area exceeds a specified limit.

    Args:
        aoi (Feature[Polygon, Dict]): Area of interest in GeoJSON format.

    Returns:
        bool: True if exceeds area limit, othewise False.
    """
    # Get aoi area limit from environment variable if available
    AOI_AREA_LIMIT = os.environ.get("AOI_AREA_LIMIT", 1000000)

    # Convert GeoJSON to Shapely Polygon
    polygon_shape = shape(aoi.model_dump()["geometry"])

    # Create GeoDataFrame with EPSG:4326 coordinate system
    gdf = gpd.GeoDataFrame(geometry=[polygon_shape], crs="EPSG:4326")

    # Get the centroid longitude to determine UTM zone
    lon = gdf.geometry.centroid.x.iloc[0]

    # Determine the UTM zone EPSG code
    utm_zone = int((lon + 180) / 6) + 1
    is_northern = gdf.geometry.centroid.y.iloc[0] >= 0
    utm_epsg = 32600 + utm_zone if is_northern else 32700 + utm_zone

    # Reproject to UTM
    gdf_projected = gdf.to_crs(CRS.from_epsg(utm_epsg))

    # Calculate the area in square meters
    area_m2 = gdf_projected.geometry.area.iloc[0]

    return area_m2 > 1000000
