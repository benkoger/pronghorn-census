from pydantic import BaseModel
from typing import Optional, List

class CreateImage(BaseModel):
    name: str
    herd_unit_id: int
    survey_id: int
    img_key: str
    image_length_px: int
    image_width_px: int
    area: Optional[int] = None
    viewshed_polygon: Optional[List[List[float]]] = None
    has_detection: bool = False   
    dem_name: Optional[str] = None
    bbox_wsen: Optional[List[int]] = None

class UpdateImage(BaseModel):
    name: Optional[str] = None
    herd_unit_id: Optional[int] = None
    survey_id: Optional[int] = None
    img_key: Optional[str] = None
    image_length_px: Optional[int] = None
    image_width_px: Optional[int] = None
    area: Optional[int] = None
    viewshed_polygon: Optional[List[List[float]]] = None
    has_detection: bool = False   
    dem_name: Optional[str] = None
    bbox_wsen: Optional[List[int]] = None