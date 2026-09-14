# Class definition for AmUnit objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------


from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, Self
from uuid import UUID

from authzed.api.v1 import RelationshipUpdate
import psycopg.sql as sql
from psycopg import Cursor
from psycopg.rows import class_row
from pydantic import BaseModel, ConfigDict

from database.object_models.base import DBbase, Keyring, create_spice_update

# ---------------------------------------------------------------------------------------------------------------------------


class CreateAmUnitReq(BaseModel):
    previous_unit_id: Optional[int] = None
    next_unit_id: Optional[int] = None
    active_measurement_ids: Keyring
    reviewed_area_ids: Optional[Keyring] = None
    reviwed_area_ids: Optional[Keyring] = None
    reg_model_ids: Keyring
    dect_model_ids: Keyring
    model_count: float
    human_count: int
    current_count: float
    current_ci_lower: Optional[float] = None
    curent_ci_lower: Optional[float] = None
    current_ci_upper: float

    model_config = ConfigDict(arbitrary_types_allowed=True)


# ---------------------------------------------------------------------------------------------------------------------------


class UpdateAmUnitReq(BaseModel):
    next_unit_id: Optional[int] = None
    previous_unit_id: Optional[int] = None
    human_count: Optional[int] = None
    current_count: Optional[float] = None
    current_ci_lower: Optional[float] = None
    current_ci_upper: Optional[float] = None


# ---------------------------------------------------------------------------------------------------------------------------

@dataclass
class AmUnit(DBbase):
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
    next_unit_id: Optional[int] = None
    previous_unit_id: Optional[int] = None

    __schema__: str = "core"
    __tablename__: str = "am_units"
    __pk_name__: str = "am_unit_id"

    # -----------------------------------------------------------------------------------------------------------------------

    class Response(BaseModel):

        am_unit_id: int
        next_unit_id: Optional[int] = None
        previous_unit_id: Optional[int] = None
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
    ) -> Optional[tuple[Self, list[RelationshipUpdate]]]:

        reviewed_area_key = req.reviewed_area_ids or req.reviwed_area_ids
        if not reviewed_area_key:
            raise ValueError("reviewed_area_ids is required")

        ci_lower = req.current_ci_lower if req.current_ci_lower is not None else req.curent_ci_lower
        if ci_lower is None:
            raise ValueError("current_ci_lower is required")

        cursor.row_factory = class_row(cls)
        query = sql.SQL("""
            INSERT INTO core.am_units (
                next_unit_id, previous_unit_id, active_measurement_id,
                reviewed_area_id, reg_model_id, dect_model_id,
                created_by_user_id, model_count, human_count,
                current_count, current_ci_lower, current_ci_upper
            )
            VALUES (
                %(next_unit_id)s, %(previous_unit_id)s,
                %(active_measurement_id)s,
                %(reviewed_area_id)s, %(reg_model_id)s, %(dect_model_id)s,
                %(created_by_user_id)s, %(model_count)s, %(human_count)s,
                %(current_count)s, %(current_ci_lower)s, %(current_ci_upper)s
            )
            RETURNING *;
        """)

        res = cursor.execute(
            query,
            {
                **req.model_dump(),
                "next_unit_id": req.next_unit_id,
                "previous_unit_id": req.previous_unit_id,
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
        return AmUnit.Response.model_validate(self).model_dump(mode="json")
