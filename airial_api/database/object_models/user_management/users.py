# Class definition for User objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------
"""User database models and schemas."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import ClassVar
from uuid import UUID

import psycopg.sql as sql
from flask_login import UserMixin
from msgpack import packb
from pydantic import BaseModel, ConfigDict

from ..base import DBbase

# ---------------------------------------------------------------------------------------------------------------------------


class UserStatus(StrEnum):
    """Enumeration of user statuses."""

    ACTIVE = "active"
    INVITED = "invited"
    DISABLED = "disabled"


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class User(UserMixin, DBbase):
    """Database representation of a user."""

    user_id: int
    username: str
    email: str
    external_auth_id: str
    external_auth_provider: str
    status: UserStatus
    created: datetime
    modified: datetime
    last_login: datetime
    uuid: UUID
    default_org_id: int
    password_hash: str
    roles: list[str] | None = None
    locale: str | None = None
    id: str = field(init=False)

    __table__: ClassVar[sql.Identifier] = sql.Identifier("usermanagement", "users")
    __pk__: ClassVar[sql.Identifier] = sql.Identifier("user_id")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class Response(BaseModel):
        """Response schema for a user."""

        model_config = ConfigDict(from_attributes=True)

        user_id: int
        username: str
        email: str
        status: UserStatus
        created: datetime
        modified: datetime
        last_login: datetime
        locale: str | None
        default_org_id: int
        uuid: UUID

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __post_init__(self):
        """Initialize string ID from UUID."""
        self.id = str(self.uuid)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def getId(self) -> str:
        """Return the user ID string."""
        return self.id

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def hasRole(self, role_name: str) -> bool:
        """Check if the user has a specific role."""
        return role_name in self.roles if self.roles else False

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def _create(cls, *args, **kwargs):
        """Stubbed to satisfy DBbase ABC contract."""
        raise NotImplementedError("Use base._insert(User, ...) for record creation.")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self) -> dict:
        """Serialize user model to a dictionary."""
        return User.Response.model_validate(self).model_dump(mode="json")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def to_cache(self):
        """Serialize user model to packed msgpack bytes for caching."""
        return packb(
            {
                **self.serialize(),
                "external_auth_id": self.external_auth_id,
                "external_auth_provider": self.external_auth_provider,
                "roles": self.roles,
                "default_org_id": self.default_org_id,
                "password_hash": self.password_hash,
            }
        )


# ---------------------------------------------------------------------------------------------------------------------------


class CreateUserReq(BaseModel):
    """Request schema for creating a user."""

    username: str
    email: str
    password: str
    external_auth_id: str | None = None
    external_auth_provider: str | None = None
    status: UserStatus | None = UserStatus.INVITED
    locale: str | None = "en/us"
    organization_id: UUID | None = None
    role_ids: list[UUID] | None = None


# ---------------------------------------------------------------------------------------------------------------------------


class UpdateUserReq(BaseModel):
    """Request schema for updating a user."""

    username: str | None = None
    last_login: datetime | None = None
    status: UserStatus | None = None
    external_auth_provider: str | None = None
    external_auth_id: str | None = None


# ---------------------------------------------------------------------------------------------------------------------------


class LegacyAuthReq(BaseModel):
    """Request schema for legacy email/password authentication."""

    email: str
    password: str


# ---------------------------------------------------------------------------------------------------------------------------


class RoleNameQuery(BaseModel):
    """Query parameters for role lookup."""

    role_name: str


# ---------------------------------------------------------------------------------------------------------------------------


class UserQuery(BaseModel):
    """Query parameters for user lookup by organization."""

    organization_id: UUID


# ---------------------------------------------------------------------------------------------------------------------------


class SetActiveOrgReq(BaseModel):
    """Request schema for setting the active organization."""

    org_id: int | UUID
