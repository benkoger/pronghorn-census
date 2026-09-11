# Class definition for Model objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Optional, Self
from uuid import UUID

from authzed.api.v1 import RelationshipUpdate
from psycopg import Cursor
from psycopg.rows import class_row
from psycopg.types.enum import EnumInfo, register_enum
from pydantic import BaseModel, ConfigDict
import psycopg.sql as sql

from ..base import DBbase, Keyring, create_spice_update

# ---------------------------------------------------------------------------------------------------------------------------


class ModelType(StrEnum):
    DETECTION = "detection"
    REGRESION = "regression"
    DEPTH_ESTIMATION = "depth estimation"


# ---------------------------------------------------------------------------------------------------------------------------


class CreateModelReq(BaseModel):
    name: str
    model_type: ModelType
    project_ids: Keyring
    schema_ids: Keyring


# ---------------------------------------------------------------------------------------------------------------------------


class UpdateModelReq(BaseModel):
    name: str


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class Model(DBbase):
    """Dataclass for representing Models from the database"""

    model_id: int
    schema_id: int
    name: str
    created: datetime
    modified: datetime
    uuid: UUID

    __tablename__: str = "models"
    __schema__: str = "projectmanagement"
    __pk_name__: str = "model_id"

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class Response(BaseModel):
        model_config = ConfigDict(from_attributes=True)
        model_id: int
        schema_id: int
        name: str
        created: datetime
        modified: datetime
        uuid: UUID

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def _create(
        cls, cursor: Cursor[Self], req: CreateModelReq
    ) -> Optional[tuple[Self, list[RelationshipUpdate]]]:

        info = EnumInfo.fetch(cursor.connection, "model_type")

        if not info:
            raise Exception("failed to get enum info")

        register_enum(info, context=cursor, enum=ModelType)

        cursor.row_factory = class_row(cls)
        query = sql.SQL("""
            WITH new_model AS (
                INSERT INTO projectmanagement.models (name, model_type)
                VALUES (%(name)s)
                RETURNING *
            )
            INSERT INTO projectmanagement.projects_models (project_id, model_id)
            VALUES (%(project_id)s, (SELECT model_id FROM new_model));

            SELECT * FROM new_model;
        """)

        cursor.execute(query, {**req.model_dump(), "project_id": req.project_ids.pkey})

        if not (model := cursor.fetchone()):
            return None

        spice_updates = [
            create_spice_update(
                "model", model.uuid, "project", req.project_ids.uuid, "parent"
            )
        ]

        return model, spice_updates

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self):
        return Model.Response.model_validate(self).model_dump(mode="json")
