# Class definition for Herd Unit objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from ..base import DBbase

# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class HerdUnit(DBbase):
    """Dataclass for representing Herd Units from the database"""

    herd_unit_id: int
    name: str
    created: datetime
    modified: datetime
    uuid: UUID

    __tablename__: str = "herd_units"
    __schema__: str = "projectmanagement"
    __pk_name__: str = "herd_unit_id"

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class Response(BaseModel):
        model_config = ConfigDict(from_attributes=True)

        herd_unit_id: int
        name: str
        created: datetime
        modified: datetime
        uuid: UUID

    def serialize(self):
        return HerdUnit.Response.model_validate(self).model_dump(mode="json")


# ---------------------------------------------------------------------------------------------------------------------------


class CreateHerdUnitReq(BaseModel):
    name: str
    project_id: UUID
