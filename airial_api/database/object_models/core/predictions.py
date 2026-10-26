# Class definition for Prediction objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar, Optional, Self
from uuid import UUID

from authzed.api.v1 import RelationshipUpdate
import psycopg.sql as sql
from psycopg import Cursor
from pydantic import BaseModel, field_validator, ConfigDict


from ..base import Box, DBbase, Keyring, PrimaryKey, create_spice_update

# ---------------------------------------------------------------------------------------------------------------------------


class PredictionQuery(BaseModel):
    prediction_id: list[PrimaryKey]

    @field_validator("prediction_id")
    @classmethod
    def ensure_list(cls, value):
        if isinstance(value, list):
            return value
        if value is None or value == "":
            return []
        return [value]


# ---------------------------------------------------------------------------------------------------------------------------


class CreatePredictionReq(BaseModel):
    image_ids: Keyring
    model_ids: Keyring
    label: int
    score: float
    box_tx: int
    box_ty: int
    box_bx: int
    box_by: int


# ---------------------------------------------------------------------------------------------------------------------------


class UpdatePredictionReq(BaseModel):
    reviewed_by_user_id: Optional[int] = None
    label: Optional[int] = None
    score: Optional[float] = None
    box_tx: Optional[int] = None
    box_ty: Optional[int] = None
    box_bx: Optional[int] = None
    box_by: Optional[int] = None


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class Prediction(DBbase):
    pred_id: int
    image_id: int
    model_id: int
    label: int
    score: float
    box_tx: int
    box_ty: int
    box_bx: int
    box_by: int
    created: datetime | None
    reviewed_by_user_id: int
    uuid: UUID
    dimensions: "Box" = field(init=False)

    __table__: ClassVar[sql.Identifier] = sql.Identifier("core", "predictions")
    __pk__: ClassVar[sql.Identifier] = sql.Identifier("pred_id")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def __post_init__(self):
        self.dimensions = Box((self.box_tx, self.box_ty), (self.box_bx, self.box_by))

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class Response(BaseModel):
        model_config = ConfigDict(from_attributes=True)

        pred_id: int
        score: float
        label: int
        dimensions: dict[str, dict[str, int]]
        uuid: UUID

        @field_validator("dimensions", mode="before")
        @classmethod
        def transform_box(cls, value: Any) -> dict[str, dict[str, int]]:
            if isinstance(value, Box):
                return value.serialize()
            return value

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def _create(
        cls, cursor: Cursor[Self], req: CreatePredictionReq
    ) -> Optional[tuple[Self, list[RelationshipUpdate]]]:
        query = sql.SQL("""
			INSERT INTO core.predictions (
				image_id, model_id, label, score, box_tx, box_ty, box_bx, box_by
			)
			VALUES (
				%(image_id)s, %(model_id)s, %(label)s, %(score)s, %(box_tx)s, %(box_ty)s, %(box_bx)s, %(box_by)s
			)
			RETURNING *;

			""")

        cursor.execute(
            query,
            {
                **req.model_dump(),
                "image_id": req.image_ids.pkey,
                "model_id": req.model_ids.pkey,
            },
        )

        if not (prediction := cursor.fetchone()):
            return None

        spice_updates = [
            create_spice_update(
                "prediction",
                prediction.uuid,
                "image",
                req.image_ids.uuid,
                "parent",
            )
        ]
        return prediction, spice_updates

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self) -> dict[str, Any]:
        return Prediction.Response.model_validate(self).model_dump(mode="json")
