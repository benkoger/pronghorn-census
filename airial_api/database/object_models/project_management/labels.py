# Class definition for Label objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------#


from dataclasses import dataclass
from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from ..base import DBbase

# ---------------------------------------------------------------------------------------------------------------------------#


@dataclass
class Label(DBbase):
    """Dataclass for representing labels from the databse"""

    label_id: int
    schema_id: int
    label: int
    name: str
    image_link: str
    created: datetime
    modified: datetime
    color: str
    uuid: UUID

    __tablename__: str = "labels"
    __schema__: str = "projectmanagement"
    __pk_name__: str = "label_id"

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

    class Response(BaseModel):
        model_config = ConfigDict(from_attributes=True)

        label_id: int
        schema_id: int
        label: int
        name: str
        image_link: str
        created: datetime
        modified: datetime
        color: str
        uuid: UUID

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

    def serialize(self):
        return Label.Response.model_validate(self).model_dump(mode="json")


# ---------------------------------------------------------------------------------------------------------------------------


class LabelQuery(BaseModel):
    label_id: List[UUID]

    @field_validator("label_id", mode="before")
    @classmethod
    def ensure_list(cls, value):
        if isinstance(value, list):
            return value
        return [value]


# ---------------------------------------------------------------------------------------------------------------------------


class CreateLabelReq(BaseModel):
    name: str
    schema_id: UUID
    label: int
    image_link: str
    color: str
