# Class definition for User objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Union
from uuid import UUID

from flask_login import UserMixin
from msgpack import packb
from pydantic import BaseModel

from ..base import DBbase

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

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "status": self.status,
            "created": self.fmt_date(self.created),
            "modified": self.fmt_date(self.modified),
            "last_login": self.fmt_date(self.last_login),
            "default_org_id": self.default_org_id,
            "locale": self.locale,
            "uuid": str(self.uuid),
        }

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def to_cache(self):
        return packb(
            {
                **self.to_dict(),
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
