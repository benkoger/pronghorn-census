# Class definition for Model objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from ..base import DBbase

# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class Model(DBbase):
    """Dataclass for representing Models from the database"""

    model_id: int
    schema_id: int
    name: str
    created: datetime
    modified: datetime
    uuid: UUID

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class Response(BaseModel):
        model_config = ConfigDict(from_attributes=True)
        model_id: int
        schema_id: int
        name: str
        created: datetime
        modified: datetime
        uuid: UUID

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self):
        return Model.Response.model_validate(self).model_dump(mode="json")

# ---------------------------------------------------------------------------------------------------------------------------


class CreateModelReq(BaseModel):
    name: str
    project_id: UUID
    schema_id: UUID


# ---------------------------------------------------------------------------------------------------------------------------


class UpdateModelReq(BaseModel):
    name: str
    project_id: UUID
    schema_id: UUID
