# Class definition for ActiveMeasurement objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------


from typing import Any, Optional, Self
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


CreateActiveMeasurment = CreateActiveMeasurement


# ---------------------------------------------------------------------------------------------------------------------------


class UpdateActiveMeasurement(BaseModel):
    retraining_cadence: Optional[int] = None


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

    __schema__: str = "projectmanagement"
    __tablename__: str = "active_measurements"
    __pk_name__: str = "active_measurement_id"

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class Response(BaseModel):
        model_config = ConfigDict(from_attributes=True)
        active_measurement_id: int
        survey_id: int
        label_id: int
        random_seed: int
        retraining_cadence: int
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
                survey_id, label_id, random_seed, retraining_cadence
            )
            VALUES (
                %(survey_id)s, %(label_id)s, %(random_seed)s,
                %(retraining_cadence)s
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
