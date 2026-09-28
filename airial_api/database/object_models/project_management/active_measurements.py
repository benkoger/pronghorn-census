# Class definition for ActiveMeasurement objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------


from typing import Any, ClassVar, Optional, Self
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from authzed.api.v1 import RelationshipUpdate
from psycopg.rows import class_row
import psycopg.sql as sql
from psycopg import Cursor
from pydantic import BaseModel, ConfigDict

from database.object_models.base import DBbase, Keyring, create_spice_update

# ---------------------------------------------------------------------------------------------------------------------------


class CreateActiveMeasurement(BaseModel):
    survey_ids: Keyring
    label_ids: Keyring
    random_seed: int
    retraining_cadence: int
    target_percentage: Optional[float] = None
    final_count: Optional[float] = None
    final_ci_upper: Optional[float] = None
    final_ci_lower: Optional[float] = None


CreateActiveMeasurment = CreateActiveMeasurement


# ---------------------------------------------------------------------------------------------------------------------------


class UpdateActiveMeasurement(BaseModel):
    retraining_cadence: Optional[int] = None
    target_percentage: Optional[float] = None
    final_count: Optional[float] = None
    final_ci_upper: Optional[float] = None
    final_ci_lower: Optional[float] = None


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class ActiveMeasurement(DBbase):
    active_measurement_id: int
    survey_id: int
    label_id: int
    random_seed: int
    retraining_cadence: int
    created: datetime
    modified: datetime
    uuid: UUID
    target_percentage: Optional[float] = None
    final_count: Optional[float] = None
    final_ci_upper: Optional[float] = None
    final_ci_lower: Optional[float] = None

    __table__: ClassVar[sql.Identifier] = sql.Identifier("projectmanagement", "active_measurements")
    __pk__: ClassVar[sql.Identifier] = sql.Identifier("active_measurement_id")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class Response(BaseModel):
        model_config = ConfigDict(from_attributes=True)
        active_measurement_id: int
        survey_id: int
        label_id: int
        random_seed: int
        retraining_cadence: int
        target_percentage: Optional[float] = None
        final_count: Optional[float] = None
        final_ci_upper: Optional[float] = None
        final_ci_lower: Optional[float] = None
        created: datetime
        modified: datetime
        uuid: UUID

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def _create(
        cls, cursor: Cursor[Self], req: CreateActiveMeasurement
    ) -> Optional[tuple[Self, list[RelationshipUpdate]]]:

        cursor.row_factory = class_row(cls)
        query = sql.SQL("""
            INSERT INTO projectmanagement.active_measurements (
                survey_id, label_id, random_seed, retraining_cadence,
                target_percentage, final_count, final_ci_upper, final_ci_lower
            )
            VALUES (
                %(survey_id)s, %(label_id)s, %(random_seed)s,
                %(retraining_cadence)s, %(target_percentage)s, %(final_count)s,
                %(final_ci_upper)s, %(final_ci_lower)s
            )
            RETURNING *;
        """)

        cursor.execute(
            query,
            {
                **req.model_dump(),
                "survey_id": req.survey_ids.pkey,
                "label_id": req.label_ids.pkey,
            },
        )

        if not (active_measurement := cursor.fetchone()):
            return None

        spice_updates = [
            create_spice_update(
                "active_measurement",
                active_measurement.uuid,
                "survey",
                req.survey_ids.uuid,
                "parent",
            )
        ]

        return active_measurement, spice_updates

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self) -> dict[str, Any]:
        return ActiveMeasurement.Response.model_validate(self).model_dump(mode="json")
