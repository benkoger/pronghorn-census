from pydantic import BaseModel, field_validator
from typing import List, Optional, Union
from uuid import UUID 

class LabelQuery(BaseModel):
	label_id: Optional[List[Union[int, UUID]]] = None
		
	@field_validator('label_id', mode='before')
	@classmethod
	def ensure_list(cls, value):
		if isinstance(value, list):
			return value
		return [value]

