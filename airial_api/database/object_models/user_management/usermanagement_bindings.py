# Multi table bindings for the usermanagement schema
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------
"""User management relational bindings models."""

from dataclasses import dataclass
from typing import ClassVar

import psycopg.sql as sql

from ..base import Relationbase

# ---------------------------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class OrganizationUser(Relationbase):
    """Relational binding between organizations, users, and roles."""

    user_id: int
    organization_id: int
    role_id: int

    __table__: ClassVar[sql.Identifier] = sql.Identifier("usermanagement", "organizations_users")
    __key__ = ("user_id", "organization_id", "role_id")


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class OrganizationProject(Relationbase):
    """Relational binding between organizations and projects."""

    project_id: int
    organization_id: int

    __table__: ClassVar[sql.Identifier] = sql.Identifier("usermanagement", "organizations_projects")
    __key__ = ("project_id", "organization_id")
