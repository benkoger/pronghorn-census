# Class definition for Organization objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------
"""Organization database models and schemas."""

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


class UpdateOrganizationReq(BaseModel):
    """Request schema for updating an organization."""

    name: str | None = None
    logo_url: str | None = None


# --------------------------------------------------------------------------------------------------------------------------


class createOrganizationReq(BaseModel):
    """Request schema for creating an organization."""

    name: str
    logo_url: str | None = None


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class Organization(DBbase):
    """Database representation of an organization."""

    organization_id: int
    name: str
    created: datetime
    modified: datetime
    uuid: UUID
    logo_url: str | None = None

    __table__: ClassVar[sql.Identifier] = sql.Identifier("usermanagement", "organizations")
    __pk__: ClassVar[sql.Identifier] = sql.Identifier("organization_id")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class Response(BaseModel):
        """Response schema for an organization."""

        model_config = ConfigDict(from_attributes=True)

        organization_id: int
        name: str
        created: datetime
        modified: datetime
        uuid: UUID
        logo_url: str | None = None

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def _create(cls, cursor: Cursor[Self], req: createOrganizationReq) -> tuple[Self, list[RelationshipUpdate]] | None: ...

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self):
        """Serialize organization model to a dictionary."""
        return Organization.Response.model_validate(self).model_dump(mode="json")
