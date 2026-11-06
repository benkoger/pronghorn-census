"""Role database models and schemas."""

# ---------------------------------------------------------------------------------------------------------------------------

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Self
from uuid import UUID

import psycopg.sql as sql
from authzed.api.v1 import RelationshipUpdate
from psycopg import Cursor
from pydantic import BaseModel, ConfigDict

from ..base import DBbase

# ---------------------------------------------------------------------------------------------------------------------------


class CreateRoleReq(BaseModel):
    """Request schema for creating a role."""


@dataclass
class Role(DBbase):
    """Database representation of a role."""

    role_id: int
    name: str
    created: datetime
    modified: datetime
    uuid: UUID

    __table__: ClassVar[sql.Identifier] = sql.Identifier("usermanagement", "roles")
    __pk__: ClassVar[sql.Identifier] = sql.Identifier("role_id")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class Response(BaseModel):
        """Response schema for a role."""

        model_config = ConfigDict(from_attributes=True)
        role_id: int
        name: str
        created: datetime
        modified: datetime
        uuid: UUID

    Response: ClassVar[type[BaseModel]] = Response

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def _create(cls, cursor: Cursor[Self], req: CreateRoleReq) -> tuple[Self, list[RelationshipUpdate]] | None:
        """Create a new role record.

        Args:
            cursor: Active database cursor.
            req: Role creation request.

        Returns:
            Optional tuple containing created Role and SpiceDB relationship updates, or None.
        """
        ...

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self) -> dict:
        """Serialize role model to a dictionary.

        Returns:
            dict: Serialized role representation.
        """
        return Role.Response.model_validate(self).model_dump(mode="json")
