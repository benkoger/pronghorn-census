from pydantic import BaseModel, field_validator 
from typing import Optional, List, Union 
from uuid import UUID

class PredictionQuery(BaseModel):
	prediction_id: List[UUID]

	@field_validator('prediction_id')
	@classmethod 
	def ensure_list(cls, value):
		if isinstance(value, list):
			return value
		if value is None or value == '':
			return []
		return [value]
