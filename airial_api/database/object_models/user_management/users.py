# Class definition for User objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Union
from uuid import UUID

from flask_login import UserMixin
from msgpack import packb
from pydantic import BaseModel, ConfigDict

from ..base import DBbase, Keyring

# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class User(UserMixin, DBbase):
    user_id: int
    username: str
    email: str
    external_auth_id: str
    external_auth_provider: str
    status: str
    created: datetime
    modified: datetime
    last_login: datetime
    locale: str
    uuid: UUID
    default_org_id: int
    password_hash: str
    roles: Optional[List[str]] = None
    id: str = field(init=False)

    __tablename__: str = "users"
    __schema__: str = "usermanagement"
    __pk_name__: str = "user_id"

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class Response(BaseModel):
        model_config = ConfigDict(from_attributes=True)

        user_id: int
        username: str
        email: str
        status: str
        created: datetime
        modified: datetime
        last_login: datetime
        locale: str
        default_org_id: int
        uuid: UUID

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __post_init__(self):
        self.id = str(self.uuid)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def getId(self) -> str:
        return self.id

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def hasRole(self, role_name: str) -> bool:
        return role_name in self.roles if self.roles else False

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def _create(cls, *args, **kwargs):
        """Stubbed to satisfy DBbase ABC contract."""
        raise NotImplementedError("Use base._insert(User, ...) for record creation.")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self) -> dict:
        return User.Response.model_validate(self).model_dump(mode="json")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def to_cache(self):
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
    username: str
    email: str
    password: str
    external_auth_id: Optional[str] = None
    external_auth_provider: Optional[str] = None
    status: Optional[str] = "invited"
    locale: Optional[str] = "en/us"
    organization_id: Optional[UUID] = None
    role_ids: Optional[List[UUID]] = None


# ---------------------------------------------------------------------------------------------------------------------------


class UpdateUserReq(BaseModel):
    username: Optional[str] = None
    last_login: Optional[datetime] = None


# ---------------------------------------------------------------------------------------------------------------------------


class LegacyAuthReq(BaseModel):
    email: str
    password: str


# ---------------------------------------------------------------------------------------------------------------------------


class RoleNameQuery(BaseModel):
    role_name: str


# ---------------------------------------------------------------------------------------------------------------------------


class UserQuery(BaseModel):
    organization_id: UUID


# ---------------------------------------------------------------------------------------------------------------------------


class SetActiveOrgReq(BaseModel):
    org_id: Union[int, UUID]
