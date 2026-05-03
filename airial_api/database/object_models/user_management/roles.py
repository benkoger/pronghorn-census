# Class definition for Role objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------#s

from dataclasses import dataclass
from datetime import datetime
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator

from ..base import DBbase

# ---------------------------------------------------------------------------------------------------------------------------#


@dataclass
class Role(DBbase):
    role_id: int
    name: str
    created: datetime
    modified: datetime
    uuid: UUID

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

    def to_dict(self):
        return {
            "role_id": self.role_id,
            "name": self.name,
            "created": self.fmt_date(self.created),
            "modified": self.fmt_date(self.modified),
            "uuid": str(self.uuid),
        }


# ---------------------------------------------------------------------------------------------------------------------------#


class RoleQuery(BaseModel):
    role_id: Optional[List[UUID]] = None

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

    @field_validator("role_id", mode="before")
    @classmethod
    def ensure_list(cls, value):
        if isinstance(value, list):
            return value
        if value is None or value == "":
            return []
        return [value]


class CreateRoleRequest(BaseModel):
    name: str
