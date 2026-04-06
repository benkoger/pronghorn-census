from pydantic import BaseModel, field_validator
from typing import Optional, List, Union
from uuid import UUID

class CreateImage(BaseModel):
    name: str
    herd_unit_id: Union[int, str]
    survey_id: Union[int, str]
    img_key: str
    image_length_px: int
    image_width_px: int
    area: Optional[int] = None
    viewshed_polygon: Optional[List[List[float]]] = None
    has_detection: bool = False   
    dem_name: Optional[str] = None
    bbox_wsen: Optional[List[int]] = None

class CreatePresignedPut(BaseModel):
    image_id: Union[str, int]
    upload_id: str
    part_number: int
    chunk_size: int
    chunk_md5: str

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

class CreatePredictionCrop(BaseModel):
	image_id: UUID
	prediction_id: List[UUID]

	@field_validator('prediction_id')
	@classmethod
	def ensure_list(cls, value):
		if isinstance(value, list):
			return value
		if value is None or value == '':
			return []
		return [value]
