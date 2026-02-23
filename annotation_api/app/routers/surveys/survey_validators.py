from pydantic import BaseModel
from typing import Optional, Union, List
from datetime import datetime
from uuid import UUID

class CreateSurvey(BaseModel):
    project_id: Union[int, UUID]
    herd_unit_ids: List[Union[int, UUID]]
    survey_date: datetime
    name: str
    additional_info: Optional[str]

class UpdateSurvey(BaseModel):
    survey_date: Optional[datetime] = None
    name: Optional[str] = None
    additional_info: Optional[str] = None 