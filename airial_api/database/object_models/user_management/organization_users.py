# Organization <-> User binding
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------

from dataclasses import dataclass
from ..base import Relationbase


@dataclass(frozen=True)
class OrganizationUser(Relationbase):
    user_id: int
    organization_id: int
    role_id: int

    __tablename__ = "organizations_users"
    __schema__ = "usermanagement"
    __key__ = ("user_id", "organization_id", "role_id")
