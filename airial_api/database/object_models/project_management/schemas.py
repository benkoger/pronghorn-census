# Class definition for Schema objects in the database
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Self
from uuid import UUID

from authzed.api.v1 import RelationshipUpdate
from psycopg.rows import class_row
import psycopg.sql as sql
from psycopg import Cursor
from pydantic import BaseModel, ConfigDict

from ..base import DBbase, Keyring, create_spice_update

# ---------------------------------------------------------------------------------------------------------------------------


class createSchemaReq(BaseModel):
    name: str
    project_ids: Keyring
    model_ids: Keyring


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class Schema(DBbase):
    """Dataclass for representing scehmas from the databse"""

    schema_id: int
    name: str
    created: datetime
    modified: datetime
    uuid: UUID

    __tablename__: str = "schemas"
    __schema__: str = "projectmanagement"
    __pk_name__: str = "schema_id"

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class Response(BaseModel):
        model_config = ConfigDict(from_attributes=True)

        schema_id: int
        name: str
        created: datetime
        modified: datetime
        uuid: UUID

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def _create(
        cls, cursor: Cursor[Self], req: createSchemaReq
    ) -> Optional[tuple[Self, list[RelationshipUpdate]]]:
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

        spice_updates = [
            create_spice_update(
                "schema", schema.uuid, "model", req.model_ids.uuid, "parent"
            )
        ]

        return schema, spice_updates

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self) -> dict:
        return Schema.Response.model_validate(self).model_dump(mode="json")
