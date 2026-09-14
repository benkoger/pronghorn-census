# Class definition for Label objects in the database
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
from pydantic import BaseModel, ConfigDict, field_validator

from ..base import DBbase, Keyring, PrimaryKey, create_spice_update

# ---------------------------------------------------------------------------------------------------------------------------


class LabelQuery(BaseModel):
    label_id: list[PrimaryKey]

    @field_validator("label_id", mode="before")
    @classmethod
    def ensure_list(cls, value):
        if isinstance(value, list):
            return value
        return [value]


# ---------------------------------------------------------------------------------------------------------------------------


class CreateLabelReq(BaseModel):
    name: str
    schema_ids: Keyring
    label: int
    image_link: str
    color: str


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class Label(DBbase):
    """Dataclass for representing labels from the databse"""

    label_id: int
    schema_id: int
    label: int
    name: str
    image_link: str | None
    created: datetime
    modified: datetime
    color: str
    uuid: UUID

    __tablename__: str = "labels"
    __schema__: str = "projectmanagement"
    __pk_name__: str = "label_id"

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class Response(BaseModel):
        model_config = ConfigDict(from_attributes=True)

        label_id: int
        schema_id: int
        label: int
        name: str
        image_link: str | None
        created: datetime
        modified: datetime
        color: str
        uuid: UUID

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def _create(
        cls, cursor: Cursor[Self], req: CreateLabelReq
    ) -> Optional[tuple[Self, list[RelationshipUpdate]]]:
        cursor.row_factory = class_row(cls)
        query = sql.SQL(""" 
            INSERT INTO projectmanagement.labels (name, schema_id, label, image_link, color)
            VALUES (%(name)s, %(schema_id)s, %(label)s, %(image_link)s, %(color)s)
            RETURNING *;
        """)

        cursor.execute(query, {**req.model_dump(), "schema_id": req.schema_ids.pkey})

        if not (label := cursor.fetchone()):
            return None

        spice_updates = [
            create_spice_update(
                "label", label.uuid, "schema", req.schema_ids.uuid, "parent"
            )
        ]

        return label, spice_updates

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self):
        return Label.Response.model_validate(self).model_dump(mode="json")
