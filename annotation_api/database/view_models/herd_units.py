from pydantic import BaseModel
from typing import Union, List
from uuid import UUID

class CreateHerdUnit(BaseModel):
    name: str
    project_id: Union[int, UUID]