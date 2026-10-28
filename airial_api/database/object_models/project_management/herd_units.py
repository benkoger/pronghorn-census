# Class definition for Herd Unit objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------
"""Herd unit database models and schemas."""

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Self
from uuid import UUID

import psycopg.sql as sql
from authzed.api.v1 import RelationshipUpdate
from psycopg import Cursor
from psycopg.rows import class_row
from pydantic import BaseModel, ConfigDict

from ..base import DBbase, Keyring, create_spice_update

# ---------------------------------------------------------------------------------------------------------------------------


class CreateHerdUnitReq(BaseModel):
    """Request schema for creating a herd unit."""

    name: str
    project_ids: Keyring
    habitable_area: float | None = None


# ---------------------------------------------------------------------------------------------------------------------------


class UpdateHerdUnitReq(BaseModel):
    """Request schema for updating a herd unit."""

    name: str | None = None
    habitable_area: float | None = None


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class HerdUnit(DBbase):
    """Dataclass for representing Herd Units from the database."""

    herd_unit_id: int
    name: str
    created: datetime
    modified: datetime
    uuid: UUID
    habitable_area: float | None = None

    __table__: ClassVar[sql.Identifier] = sql.Identifier("projectmanagement", "herd_units")
    __pk__: ClassVar[sql.Identifier] = sql.Identifier("herd_unit_id")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class Response(BaseModel):
        """Response schema for a herd unit."""

        model_config = ConfigDict(from_attributes=True)

        herd_unit_id: int
        name: str
        habitable_area: float | None = None
        created: datetime
        modified: datetime
        uuid: UUID

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def _create(cls, cursor: Cursor[Self], req: CreateHerdUnitReq) -> tuple[Self, list[RelationshipUpdate]] | None:
        cursor.row_factory = class_row(cls)
        query = sql.SQL("""
            WITH new_herd_unit AS (
                INSERT INTO projectmanagement.herd_units (name, habitable_area)
                VALUES (%(name)s, %(habitable_area)s)
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
        """Serialize herd unit model to a dictionary."""
        return HerdUnit.Response.model_validate(self).model_dump(mode="json")
