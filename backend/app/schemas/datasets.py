from typing import List, Optional

from pydantic import AnyHttpUrl, BaseModel


class LidarDatasetItem(BaseModel):
    id: str
    bbox: List[float]
    epsg: int
    href: AnyHttpUrl


class NaipDatasetItem(BaseModel):
    id: str
    bbox: List[float]
    epsg: int
    gsd: float
    href: AnyHttpUrl


class DatasetsResponse(BaseModel):
    point_cloud: List[LidarDatasetItem]
    raster: List[NaipDatasetItem]


class ResultDataset(BaseModel):
    href: str
    rescale: str
    file_size: float


class ModelResponse(BaseModel):
    chm: ResultDataset
    ndhm: ResultDataset
    building2d: ResultDataset
    building3d: ResultDataset
    chmv2: ResultDataset
    naip: Optional[ResultDataset] = None
    session_id: str
