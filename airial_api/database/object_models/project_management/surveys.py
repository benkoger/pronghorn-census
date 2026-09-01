# Class definition for Survey objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------#

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from ..base import DBbase

# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class Survey(DBbase):
    """Dataclass for representing Surveys from the database"""

    survey_id: int
    survey_date: datetime
    name: str
    additional_info: str
    created: datetime
    modified: datetime
    uuid: UUID

    __tablename__: str = "surveys"
    __schema__: str = "projectmanagement"
    __pk_name__: str = "survey_id"

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class Response(BaseModel):
        model_config = ConfigDict(from_attributes=True)

        survey_id: int
        survey_date: datetime
        name: str
        additional_info: str
        created: datetime
        modified: datetime
        uuid: UUID

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self) -> dict:
        return Survey.Response.model_validate(self).model_dump(mode="json")


# ---------------------------------------------------------------------------------------------------------------------------


class CreateSurveyReq(BaseModel):
    project_id: UUID
    herd_unit_id: UUID
    survey_date: datetime
    name: str
    additional_info: Optional[str]


# ---------------------------------------------------------------------------------------------------------------------------


class UpdateSurveyReq(BaseModel):
    survey_date: Optional[datetime] = None
    name: Optional[str] = None
    additional_info: Optional[str] = None


class SurveyImageQuery(BaseModel):
    page: int = 1
    per_page: int = 50
