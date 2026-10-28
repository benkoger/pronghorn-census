# Class definition for Label objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------
"""Label database models and schemas."""

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Self
from uuid import UUID

import psycopg.sql as sql
from authzed.api.v1 import RelationshipUpdate
from psycopg import Cursor
from psycopg.rows import class_row
from pydantic import BaseModel, ConfigDict, field_validator

from ..base import DBbase, Keyring, PrimaryKey, create_spice_update

# ---------------------------------------------------------------------------------------------------------------------------


class LabelQuery(BaseModel):
    """Query parameters for labels."""

    label_id: list[PrimaryKey]

    @field_validator("label_id", mode="before")
    @classmethod
    def ensure_list(cls, value):
        """Ensure label ID is a list."""
        if isinstance(value, list):
            return value
        return [value]


# ---------------------------------------------------------------------------------------------------------------------------


class CreateLabelReq(BaseModel):
    """Request schema for creating a label."""

    name: str
    schema_ids: Keyring
    label: int
    image_link: str
    color: str


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class Label(DBbase):
    """Dataclass for representing labels from the database."""

    label_id: int
    schema_id: int
    label: int
    name: str
    image_link: str | None
    created: datetime
    modified: datetime
    color: str
    uuid: UUID

    __table__: ClassVar[sql.Identifier] = sql.Identifier("projectmanagement", "labels")
    __pk__: ClassVar[sql.Identifier] = sql.Identifier("label_id")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class Response(BaseModel):
        """Response schema for a label."""

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
    def _create(cls, cursor: Cursor[Self], req: CreateLabelReq) -> tuple[Self, list[RelationshipUpdate]] | None:
        cursor.row_factory = class_row(cls)
        query = sql.SQL("""
            INSERT INTO projectmanagement.labels (name, schema_id, label, image_link, color)
            VALUES (%(name)s, %(schema_id)s, %(label)s, %(image_link)s, %(color)s)
            RETURNING *;
        """)

        cursor.execute(query, {**req.model_dump(), "schema_id": req.schema_ids.pkey})

        if not (label := cursor.fetchone()):
            return None

        spice_updates = [create_spice_update("label", label.uuid, "schema", req.schema_ids.uuid, "parent")]

        return label, spice_updates

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self):
        """Serialize label model to a dictionary."""
        return Label.Response.model_validate(self).model_dump(mode="json")
