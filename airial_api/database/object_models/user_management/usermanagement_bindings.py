# Multi table bindings for the usermanagement schema
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------

from dataclasses import dataclass
from ..base import Relationbase


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class OrganizationUser(Relationbase):
    user_id: int
    organization_id: int
    role_id: int

    __tablename__ = "organizations_users"
    __schema__ = "usermanagement"
    __key__ = ("user_id", "organization_id", "role_id")


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class OrganizationProject(Relationbase):
    project_id: int
    organization_id: int

    __tablename__ = "organizations_projects"
    __schema__ = "usermanagement"
    __key__ = ("project_id", "organization_id")
