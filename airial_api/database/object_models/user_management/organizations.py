# Class definition for Organization objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------#

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from ..base import DBbase

# ---------------------------------------------------------------------------------------------------------------------------#


@dataclass
class Organization(DBbase):
    organization_id: int
    name: str
    created: datetime
    modified: datetime
    uuid: UUID
    logo_url: Optional[str] = None

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

    def to_dict(self):
        return {
            "organization_id": self.organization_id,
            "name": self.name,
            "created": self.fmt_date(self.created),
            "modified": self.fmt_date(self.modified),
            "logo_url": self.logo_url,
            "uuid": str(self.uuid),
        }


# --------------------------------------------------------------------------------------------------------------------------


class UpdateOrganizationReq(BaseModel):
    name: Optional[str] = None
    logo_url: Optional[str] = None
