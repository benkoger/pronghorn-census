# Class definition for Schema objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------
"""Schema database models and schemas."""

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


class createSchemaReq(BaseModel):
    """Request schema for creating a schema."""

    name: str
    project_ids: Keyring
    model_ids: Keyring


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class Schema(DBbase):
    """Dataclass for representing schemas from the database."""

    schema_id: int
    name: str
    created: datetime
    modified: datetime
    uuid: UUID

    __table__: ClassVar[sql.Identifier] = sql.Identifier("projectmanagement", "schemas")
    __pk__: ClassVar[sql.Identifier] = sql.Identifier("schema_id")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class Response(BaseModel):
        """Response schema for a schema."""

        model_config = ConfigDict(from_attributes=True)

        schema_id: int
        name: str
        created: datetime
        modified: datetime
        uuid: UUID

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def _create(cls, cursor: Cursor[Self], req: createSchemaReq) -> tuple[Self, list[RelationshipUpdate]] | None:
        cursor.row_factory = class_row(cls)
        query = sql.SQL("""
            WITH new_schema AS (
                INSERT INTO projectmanagement.schemas (name)
                VALUES (%(name)s)
                RETURNING *
            )
            INSERT INTO projectmanagement.projects_schemas (project_id, schema_id)
            VALUES (%(project_id)s, (SELECT schema_id FROM new_schema));

            SELECT * FROM new_schema;
        """)

        cursor.execute(query, {**req.model_dump(), "project_id": req.project_ids.pkey})

        if not (schema := cursor.fetchone()):
            return None

        spice_updates = [create_spice_update("schema", schema.uuid, "model", req.model_ids.uuid, "parent")]

        return schema, spice_updates

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self) -> dict:
        """Serialize schema model to a dictionary."""
        return Schema.Response.model_validate(self).model_dump(mode="json")
