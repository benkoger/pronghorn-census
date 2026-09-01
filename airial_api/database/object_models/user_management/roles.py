# Class definition for Role objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Self
from uuid import UUID

from authzed.api.v1 import RelationshipUpdate
from psycopg import Cursor
from pydantic import BaseModel, ConfigDict, field_validator

from ..base import DBbase

# ---------------------------------------------------------------------------------------------------------------------------


class RoleQuery(BaseModel):
    role_id: Optional[List[UUID]] = None

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @field_validator("role_id", mode="before")
    @classmethod
    def ensure_list(cls, value):
        if isinstance(value, list):
            return value
        if value is None or value == "":
            return []
        return [value]


class CreateRoleReq(BaseModel):
    """Not implemented; Were working on it :)"""

    ...


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class Role(DBbase):
    role_id: int
    name: str
    created: datetime
    modified: datetime
    uuid: UUID

    __tablename__: str = "roles"
    __schema__: str = "usermanagement"
    __pk_name__: str = "role_id"

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class Response(BaseModel):
        model_config = ConfigDict(from_attributes=True)
        role_id: int
        name: str
        created: datetime
        modified: datetime
        uuid: UUID

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def _create(
        cls, cursor: Cursor[Self], req: CreateRoleReq
    ) -> Optional[tuple[Self, list[RelationshipUpdate]]]: ...

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self):
        return Role.Response.model_validate(self).model_dump(mode="json")
