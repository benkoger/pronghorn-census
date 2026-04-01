from pydantic import BaseModel
from uuid import UUID

class CreateHerdUnit(BaseModel):
    name: str
    project_id: UUID
