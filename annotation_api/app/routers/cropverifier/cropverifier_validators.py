from pydantic import BaseModel, field_validator
from typing import Union, List, Optional, Dict
from uuid import UUID

class RAQuery(BaseModel):
	herd_unit_id: Optional[List[int]]
	survey_id: Optional[List[int]] 
	include_reviewed: Optional[bool] = False
	include_opened: Optional[bool] = False

	@field_validator('herd_unit_id', 'survey_id', mode='before')
	@classmethod
	def ensure_list(cls, value):
		if isinstance(value, list):
			return value
		if value is None or value == "":
			return []
		return [value]

class ApproveAnnotations(BaseModel):
	reviewed_area_id: Union[int, UUID]
	image_id: Union[int, UUID]
	annotations: List[Dict]
	deleted_annotations: List[Dict]
