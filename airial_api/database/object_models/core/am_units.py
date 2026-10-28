# Class definition for AmUnit objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------

"""Database model and request schemas for active measurement units (AmUnit)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar, Self
from uuid import UUID

import psycopg.sql as sql
from authzed.api.v1 import RelationshipUpdate
from psycopg import Cursor
from psycopg.rows import class_row
from pydantic import BaseModel, ConfigDict

from database.object_models.base import DBbase, Keyring, create_spice_update

# ---------------------------------------------------------------------------------------------------------------------------


class CreateAmUnitReq(BaseModel):
    """Request schema for creating an active measurement unit."""

    previous_unit_id: int | None = None
    next_unit_id: int | None = None
    relative_position: int | None = None
    active_measurement_ids: Keyring
    reviewed_area_ids: Keyring | None = None
    reviwed_area_ids: Keyring | None = None
    reg_model_ids: Keyring
    dect_model_ids: Keyring
    model_count: float
    human_count: int
    current_count: float
    current_ci_lower: float | None = None
    curent_ci_lower: float | None = None
    current_ci_upper: float

    model_config = ConfigDict(arbitrary_types_allowed=True)


# ---------------------------------------------------------------------------------------------------------------------------


class UpdateAmUnitReq(BaseModel):
    """Request schema for updating an active measurement unit."""

    next_unit_id: int | None = None
    previous_unit_id: int | None = None
    relative_position: int | None = None
    human_count: int | None = None
    current_count: float | None = None
    current_ci_lower: float | None = None
    current_ci_upper: float | None = None


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class AmUnit(DBbase):
    """Database entity representing an active measurement unit."""

    am_unit_id: int
    active_measurement_id: int
    reviewed_area_id: int
    reg_model_id: int
    dect_model_id: int
    created_by_user_id: int
    model_count: float
    human_count: int
    current_count: float
    current_ci_lower: float
    current_ci_upper: float
    created: datetime
    modified: datetime
    uuid: UUID
    next_unit_id: int | None = None
    previous_unit_id: int | None = None
    relative_position: int | None = None

    __table__: ClassVar[sql.Identifier] = sql.Identifier("core", "am_units")
    __pk__: ClassVar[sql.Identifier] = sql.Identifier("am_unit_id")

    # -----------------------------------------------------------------------------------------------------------------------

    class Response(BaseModel):
        """Pydantic response model for serialized AmUnit entities."""

        am_unit_id: int
        next_unit_id: int | None = None
        previous_unit_id: int | None = None
        relative_position: int | None = None
        active_measurement_id: int
        reviewed_area_id: int
        reg_model_id: int
        dect_model_id: int
        created_by_user_id: int
        model_count: float
        human_count: int
        current_count: float
        current_ci_lower: float
        current_ci_upper: float
        created: datetime
        modified: datetime
        uuid: UUID

    # -----------------------------------------------------------------------------------------------------------------------

    @classmethod
    def _create(
        cls,
        cursor: Cursor[Self],
        req: CreateAmUnitReq,
        user_key: Keyring,
    ) -> tuple[Self, list[RelationshipUpdate]] | None:

        reviewed_area_key = req.reviewed_area_ids or req.reviwed_area_ids
        if not reviewed_area_key:
            raise ValueError("reviewed_area_ids is required")

        ci_lower = req.current_ci_lower if req.current_ci_lower is not None else req.curent_ci_lower
        if ci_lower is None:
            raise ValueError("current_ci_lower is required")

        cursor.row_factory = class_row(cls)
        query = sql.SQL("""
            INSERT INTO core.am_units (
                next_unit_id, previous_unit_id, relative_position, active_measurement_id,
                reviewed_area_id, reg_model_id, dect_model_id,
                created_by_user_id, model_count, human_count,
                current_count, current_ci_lower, current_ci_upper
            )
            VALUES (
                %(next_unit_id)s, %(previous_unit_id)s, %(relative_position)s,
                %(active_measurement_id)s,
                %(reviewed_area_id)s, %(reg_model_id)s, %(dect_model_id)s,
                %(created_by_user_id)s, %(model_count)s, %(human_count)s,
                %(current_count)s, %(current_ci_lower)s, %(current_ci_upper)s
            )
            RETURNING *;
        """)

        cursor.execute(
            query,
            {
                **req.model_dump(),
                "next_unit_id": req.next_unit_id,
                "previous_unit_id": req.previous_unit_id,
                "relative_position": req.relative_position,
                "active_measurement_id": req.active_measurement_ids.pkey,
                "reviewed_area_id": reviewed_area_key.pkey,
                "reg_model_id": req.reg_model_ids.pkey,
                "dect_model_id": req.dect_model_ids.pkey,
                "created_by_user_id": user_key.pkey,
                "current_ci_lower": ci_lower,
            },
        )

        if not (am_unit := cursor.fetchone()):
            return None

        spice_updates = [
            create_spice_update(
                "am_unit",
                am_unit.uuid,
                "active_measurement",
                req.active_measurement_ids.uuid,
                "parent",
            )
        ]

        return am_unit, spice_updates

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self) -> dict[str, Any]:
        """Serialize AmUnit instance to JSON-compatible dictionary."""
        return AmUnit.Response.model_validate(self).model_dump(mode="json")
