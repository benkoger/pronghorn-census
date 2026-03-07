from datetime import datetime
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
	roles: Optional[List[str]] = None
	project_ids: Optional[List[Union[int, UUID]]] = None
	organization_ids: Optional[List[Union[int, UUID]]] = None

class LegacyAuth(BaseModel):
	email: str
	password: str

class RoleQuery(BaseModel):
	role_name: str