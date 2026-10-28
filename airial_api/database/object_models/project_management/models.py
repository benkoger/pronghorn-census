# Class definition for Model objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------
"""Model database models and schemas."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import ClassVar, Self
from uuid import UUID

import psycopg.sql as sql
from authzed.api.v1 import RelationshipUpdate
from psycopg import Cursor
from psycopg.rows import class_row
from pydantic import BaseModel, ConfigDict

from ..base import DBbase, Keyring, create_spice_update

# ---------------------------------------------------------------------------------------------------------------------------


class ModelType(StrEnum):
    """Enumeration of model types."""

    DETECTION = "detection"
    REGRESSION = "regression"
    DEPTH_ESTIMATION = "depth estimation"
    REGRESION = "regression"


# ---------------------------------------------------------------------------------------------------------------------------


class CreateModelReq(BaseModel):
    """Request schema for creating a model."""

    name: str
    model_type: ModelType
    project_ids: Keyring
    schema_ids: Keyring


# ---------------------------------------------------------------------------------------------------------------------------


class UpdateModelReq(BaseModel):
    """Request schema for updating a model."""

    name: str


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class Model(DBbase):
    """Dataclass for representing models from the database."""

    model_id: int
    schema_id: int
    name: str
    model_type: ModelType
    created: datetime
    modified: datetime
    uuid: UUID

    __table__: ClassVar[sql.Identifier] = sql.Identifier("projectmanagement", "models")
    __pk__: ClassVar[sql.Identifier] = sql.Identifier("model_id")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class Response(BaseModel):
        """Response schema for a model."""

        model_config = ConfigDict(from_attributes=True)
        model_id: int
        schema_id: int
        name: str
        model_type: ModelType
        created: datetime
        modified: datetime
        uuid: UUID

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def _create(cls, cursor: Cursor[Self], req: CreateModelReq) -> tuple[Self, list[RelationshipUpdate]] | None:

        cursor.row_factory = class_row(cls)
        query = sql.SQL("""
            WITH new_model AS (
                INSERT INTO projectmanagement.models (name, model_type)
                VALUES (%(name)s, %(model_type)s)
                RETURNING *
            )
            INSERT INTO projectmanagement.projects_models (project_id, model_id)
            VALUES (%(project_id)s, (SELECT model_id FROM new_model));

            SELECT * FROM new_model;
        """)

        cursor.execute(query, {**req.model_dump(), "project_id": req.project_ids.pkey})

        if not (model := cursor.fetchone()):
            return None

        spice_updates = [create_spice_update("model", model.uuid, "project", req.project_ids.uuid, "parent")]

        return model, spice_updates

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self):
        """Serialize model to a dictionary."""
        return Model.Response.model_validate(self).model_dump(mode="json")
