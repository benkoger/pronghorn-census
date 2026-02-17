from pydantic import BaseModel
from typing import Union, List, Optional
from uuid import UUID

class CreateModel(BaseModel):
    name: str
    project_id: Union[int, UUID]
    schema_id: Union[int, UUID]
    survey_ids: Optional[List[Union[int, UUID]]]