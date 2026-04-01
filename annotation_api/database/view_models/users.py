from typing import List, Optional, Union
from uuid import UUID

from pydantic import BaseModel

class CreateUser(BaseModel):
	username: str
	email: str
	password: str
	external_auth_id: str
	external_auth_provider: str 
	status: str = 'invited'
	locale: str
	organization_id: Union[int, UUID]
	role_ids: List[Union[int, UUID]]
	current_user: UUID 	

class LegacyAuth(BaseModel):
	email: str
	password: str

class RoleQuery(BaseModel):
	role_name: str

