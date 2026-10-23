# Class definition for Organization objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Optional, Self
from uuid import UUID

import psycopg.sql as sql

from authzed.api.v1 import RelationshipUpdate
from psycopg import Cursor
from pydantic import BaseModel, ConfigDict

from ..base import DBbase

# ---------------------------------------------------------------------------------------------------------------------------


class UpdateOrganizationReq(BaseModel):
    name: Optional[str] = None
    logo_url: Optional[str] = None


# --------------------------------------------------------------------------------------------------------------------------


class createOrganizationReq(BaseModel):
    name: str
    logo_url: Optional[str] = None


@dataclass
class Organization(DBbase):
    organization_id: int
    name: str
    created: datetime
    modified: datetime
    uuid: UUID
    logo_url: Optional[str] = None

    __table__: ClassVar[sql.Identifier] = sql.Identifier("usermanagement", "organizations")
    __pk__: ClassVar[sql.Identifier] = sql.Identifier("organization_id")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class Response(BaseModel):
        model_config = ConfigDict(from_attributes=True)

        organization_id: int
        name: str
        created: datetime
        modified: datetime
        uuid: UUID
        logo_url: Optional[str] = None

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def _create(
        cls, cursor: Cursor[Self], req: createOrganizationReq
    ) -> Optional[tuple[Self, list[RelationshipUpdate]]]: ...

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self):
        return Organization.Response.model_validate(self).model_dump(mode="json")
