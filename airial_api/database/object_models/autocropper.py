from pydantic import BaseModel, field_validator
from typing import List
from uuid import UUID 

class AutoCropperBatchQuery(BaseModel):
	survey_id: UUID
	herd_unit_id: UUID
	model_id: UUID
	label: List[int]	
	batch_size: int
	min_confidence: float

class AutoCropReq(BaseModel):
	image_id: UUID
	prediction_id: List[UUID]
	label_id: List[UUID]

	@field_validator('prediction_id', 'label_id')
	@classmethod 
	def ensure_list(cls, value):
		if isinstance(value, list):
			return value
		if value is None or value == '':
			return []
		return [value]

