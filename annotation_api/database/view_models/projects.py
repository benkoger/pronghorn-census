from pydantic import BaseModel, field_validator
from typing import List, Optional, Union 
from uuid import UUID 

class ProjectQuery(BaseModel):
	project_id: Optional[List[Union[int, UUID]]] = None
	organization_id: Optional[Union[int, UUID]] = None

	@field_validator('project_id', mode='before')
	@classmethod
	def ensure_list(cls, value):
		if isinstance(value, list):
			return value
		return [value]
