# Class definition for Prediction objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------
"""Prediction database models and schemas."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar, Self
from uuid import UUID

import psycopg.sql as sql
from authzed.api.v1 import RelationshipUpdate
from psycopg import Cursor
from pydantic import BaseModel, ConfigDict, field_validator

from ..base import Box, DBbase, Keyring, PrimaryKey, create_spice_update

# ---------------------------------------------------------------------------------------------------------------------------


class PredictionQuery(BaseModel):
    """Query parameters for predictions."""

    prediction_id: list[PrimaryKey]

    @field_validator("prediction_id")
    @classmethod
    def ensure_list(cls, value):
        """Ensure prediction IDs are a list."""
        if isinstance(value, list):
            return value
        if value is None or value == "":
            return []
        return [value]


# ---------------------------------------------------------------------------------------------------------------------------


class CreatePredictionReq(BaseModel):
    """Request schema for creating a prediction."""

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
    """Request schema for updating a prediction."""

    reviewed_by_user_id: int | None = None
    label: int | None = None
    score: float | None = None
    box_tx: int | None = None
    box_ty: int | None = None
    box_bx: int | None = None
    box_by: int | None = None


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class Prediction(DBbase):
    """Database representation of a prediction."""

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
    __parent_table__: ClassVar[sql.Identifier] = sql.Identifier("core", "images")
    __parent_fk__: ClassVar[sql.Identifier] = sql.Identifier("image_id")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def __post_init__(self):
        """Initialize dimensions box."""
        self.dimensions = Box((self.box_tx, self.box_ty), (self.box_bx, self.box_by))

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class Response(BaseModel):
        """Response schema for a prediction."""

        model_config = ConfigDict(from_attributes=True)

        pred_id: int
        score: float
        label: int
        dimensions: dict[str, dict[str, int]]
        uuid: UUID

        @field_validator("dimensions", mode="before")
        @classmethod
        def transform_box(cls, value: Any) -> dict[str, dict[str, int]]:
            """Transform box object into serialized dictionary."""
            if isinstance(value, Box):
                return value.serialize()
            return value

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def _create(cls, cursor: Cursor[Self], req: CreatePredictionReq) -> tuple[Self, list[RelationshipUpdate]] | None:
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
        """Serialize prediction model to a dictionary."""
        return Prediction.Response.model_validate(self).model_dump(mode="json")
