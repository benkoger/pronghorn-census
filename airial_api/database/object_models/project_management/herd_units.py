# Class definition for Herd Unit objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Self
from uuid import UUID

from authzed.api.v1 import RelationshipUpdate
import psycopg.sql as sql
from psycopg import Cursor
from psycopg.rows import class_row
from pydantic import BaseModel, ConfigDict

from ..base import DBbase, Keyring, create_spice_update

# ---------------------------------------------------------------------------------------------------------------------------


class CreateHerdUnitReq(BaseModel):
    name: str
    project_ids: Keyring


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

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def _create(
        cls, cursor: Cursor[Self], req: CreateHerdUnitReq
    ) -> Optional[tuple[Self, list[RelationshipUpdate]]]:
        cursor.row_factory = class_row(cls)
        query = sql.SQL("""
            WITH new_herd_unit AS (
                INSERT INTO projectmanagement.herd_units (name)
                VALUES (%(name)s)
                RETURNING *
            ),
            inserted_link AS (
                INSERT INTO projectmanagement.projects_herd_units (
                project_id, herd_unit_id
                )
                SELECT %(project_id)s, herd_unit_id FROM new_herd_unit
            )
            SELECT * FROM new_herd_unit;
        """)

        cursor.execute(query, {**req.model_dump(), "project_id": req.project_ids.pkey})

        if not (herd_unit := cursor.fetchone()):
            return None

        spice_updates = [
            create_spice_update(
                "herd_unit",
                herd_unit.uuid,
                "project",
                req.project_ids.uuid,
                "parent",
            )
        ]

        return herd_unit, spice_updates

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self):
        return HerdUnit.Response.model_validate(self).model_dump(mode="json")
