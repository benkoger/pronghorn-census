# Class definition for Project objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from ..base import DBbase

# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class Project(DBbase):
    """Dataclass for representing projects from the databse"""

    project_id: int
    name: str
    created: datetime
    modified: datetime
    uuid: UUID

    __tablename__: str = "projects"
    __schema__: str = "projectmanagement"
    __pk_name__: str = "project_id"

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class Response(BaseModel):
        model_config = ConfigDict(from_attributes=True)

        project_id: int
        name: str
        created: datetime
        modified: datetime
        uuid: UUID

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self):
        return Project.Response.model_validate(self).model_dump(mode="json") 


# ---------------------------------------------------------------------------------------------------------------------------


class ProjectQuery(BaseModel):
    project_id: Optional[List[Union[int, UUID]]] = None

    @field_validator("project_id", mode="before")
    @classmethod
    def ensure_list(cls, value):
        if isinstance(value, list):
            return value
        return [value]


# ---------------------------------------------------------------------------------------------------------------------------


class createProjectReq(BaseModel):
    name: str
    organization_id: UUID
