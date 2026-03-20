from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import List, Optional, Union
from uuid import UUID

class GetRoles(BaseModel):
	role_id: List[Union[int, UUID]]

	@field_validator('role_id', mode='before')
	@classmethod
	def ensure_list(cls, value):
		if isinstance(value, list):
			return value
		if value is None or value == "":
			return []
		return [value]