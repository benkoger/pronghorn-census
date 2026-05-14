# Class definition for Model objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------#

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from ..base import DBbase

# ---------------------------------------------------------------------------------------------------------------------------#


@dataclass
class Model(DBbase):
    """Dataclass for representing Models from the database"""

    model_id: int
    schema_id: int
    name: str
    created: datetime
    modified: datetime
    uuid: UUID

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

    def to_dict(self):
        return {
            "model_id": self.model_id,
            "schema_id": self.schema_id,
            "name": self.name,
            "created": self.fmt_date(self.created),
            "modified": self.fmt_date(self.modified),
            "uuid": str(self.uuid),
        }


# ---------------------------------------------------------------------------------------------------------------------------#


class CreateModelReq(BaseModel):
    name: str
    project_id: UUID
    schema_id: UUID

