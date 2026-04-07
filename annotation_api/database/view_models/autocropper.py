from pydantic import BaseModel, field_validator
from typing import List, Union
from uuid import UUID 

class AutoCropperBatchQuery(BaseModel):
	survey_id: UUID
	herd_unit_id: UUID
	model_id: UUID
	label: List[int]	
	batch_size: int
	min_confidence: float
