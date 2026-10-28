# Class definition for Annotation objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------

"""Database model and request schemas for annotations."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar, Self
from uuid import UUID

import psycopg.sql as sql
from authzed.api.v1 import RelationshipUpdate
from psycopg import Cursor
from psycopg.rows import class_row
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..base import (
    Box,
    BulkRequestModel,
    DBbase,
    Keyring,
    create_spice_update,
)
from .activity import ActivityType

# ---------------------------------------------------------------------------------------------------------------------------


class CreateAnnotationReq(BaseModel):
    """Request schema for creating a single annotation."""

    label_id: int
    image_ids: Keyring
    herd_unit_id: int
    box_tx: int
    box_ty: int
    box_bx: int
    box_by: int
    uuid: UUID
    type: ActivityType = ActivityType.AUTO_CROPPER
    prediction_ids: Keyring | None = None
    reviewed_area_ids: Keyring | None = None


# ---------------------------------------------------------------------------------------------------------------------------


class BulkCreateAnnotationReq(BaseModel):
    """Request schema for bulk creating annotations for a reviewed area."""

    reviewed_area_id: UUID
    requests: list[CreateAnnotationReq]


# ---------------------------------------------------------------------------------------------------------------------------


class UpdateAnnotationReq(BaseModel):
    """Request schema for updating an existing annotation."""

    annotation_id: UUID | None = Field(default=None, exclude=True)
    image_id: Keyring | None = None
    label_id: int | Keyring | None = None
    type: ActivityType | None = None
    box_tx: int | None = None
    box_ty: int | None = None
    box_bx: int | None = None
    box_by: int | None = None

    @field_validator("label_id", mode="before")
    @classmethod
    def resolve_label_id(cls, value: Any) -> int | None:
        """Normalize label ID from integer, dict, or Keyring representation."""
        if value is None:
            return None
        if isinstance(value, dict) and "pkey" in value:
            return value["pkey"]
        if hasattr(value, "pkey"):
            return value.pkey
        return int(value)


class BulkUpdateAnnotationsReq(BulkRequestModel):
    """Request schema for bulk updating annotations for a reviewed area."""

    reviewed_area_id: UUID
    requests: list[UpdateAnnotationReq]


# ---------------------------------------------------------------------------------------------------------------------------


class DeleteAnnotationReq(BaseModel):
    """Request schema for deleting a single annotation."""

    annotation_id: UUID


# ---------------------------------------------------------------------------------------------------------------------------


class BulkDeleteAnnotationsReq(BulkRequestModel):
    """Request schema for bulk deleting annotations."""

    requests: list[DeleteAnnotationReq]


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class Annotation(DBbase):
    """Database entity representing an image annotation."""

    label_id: int
    image_id: int
    type: ActivityType
    pred_id: int
    herd_unit_id: int
    box_tx: int
    box_ty: int
    box_bx: int
    box_by: int
    annotation_id: int
    created_by_user_id: int
    created: datetime
    modified: datetime
    uuid: UUID
    dimensions: "Box" = field(init=False)

    __table__: ClassVar[sql.Identifier] = sql.Identifier("core", "annotations")
    __pk__: ClassVar[sql.Identifier] = sql.Identifier("annotation_id")
    __parent_table__: ClassVar[sql.Identifier] = sql.Identifier("core", "images")
    __parent_fk__: ClassVar[sql.Identifier] = sql.Identifier("image_id")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def __post_init__(self):
        """Construct Box dimensions from coordinates."""
        self.dimensions = Box((self.box_tx, self.box_ty), (self.box_bx, self.box_by))

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class Response(BaseModel):
        """Pydantic response model for serialized Annotation entities."""

        model_config = ConfigDict(from_attributes=True)

        annotation_id: int
        label_id: int
        image_id: int
        type: ActivityType
        herd_unit_id: int
        dimensions: dict[str, dict[str, int]]
        created: datetime
        modified: datetime
        uuid: UUID

        @field_validator("dimensions", mode="before")
        @classmethod
        def transform_box(cls, value: Any) -> dict[str, dict[str, int]]:
            """Serialize Box instance into nested dictionary."""
            if isinstance(value, Box):
                return value.serialize()
            return value

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def _create(
        cls,
        cursor: Cursor[Self],
        req: CreateAnnotationReq,
        user_key: Keyring,
        herd_unit_key: Keyring,
    ) -> tuple[Self, list[RelationshipUpdate]] | None:

        cursor.row_factory = class_row(cls)
        query = sql.SQL("""
            WITH new_annotation AS (
                INSERT INTO core.annotations (
                    label_id, image_id, type, herd_unit_id, box_tx, box_ty, box_bx,
                    box_by, created_by_user_id, pred_id, uuid
                )
                VALUES (
                    %(label_id)s, %(image_id)s, %(type)s, %(herd_unit_id)s, %(box_tx)s,
                    %(box_ty)s, %(box_bx)s, %(box_by)s, %(created_by_user_id)s,
                    %(pred_id)s, %(uuid)s
                )
                RETURNING *
            ),
            inserted_link AS (
                INSERT INTO core.annotations_reviewed_area (
                    reviewed_area_id, annotation_id
                )
                SELECT %(reviewed_area_id)s, annotation_id FROM new_annotation
            )
            SELECT * FROM new_annotation;
        """)

        if not req.reviewed_area_ids:
            raise TypeError("Reviewed area ids are required for Annotations!")

        cursor.execute(
            query,
            {
                **req.model_dump(),
                "herd_unit_id": herd_unit_key.pkey,
                "image_id": req.image_ids.pkey,
                "pred_id": req.prediction_ids.pkey if req.prediction_ids else 0,
                "created_by_user_id": user_key.pkey,
                "reviewed_area_id": req.reviewed_area_ids.pkey,
            },
        )

        if not (annotation := cursor.fetchone()):
            return None

        spice_updates = [create_spice_update("annotation", annotation.uuid, "image", req.image_ids.uuid, "parent")]

        return annotation, spice_updates

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self) -> dict[str, Any]:
        """Serialize Annotation entity to dictionary."""
        return Annotation.Response.model_validate(self).model_dump(mode="json")
