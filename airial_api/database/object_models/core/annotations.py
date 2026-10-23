# Class definition for Annotation objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional, Self
from uuid import UUID

from authzed.api.v1 import RelationshipUpdate
import psycopg.sql as sql
from psycopg import Cursor
from psycopg.rows import class_row
from pydantic import BaseModel, field_validator, ConfigDict

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
    label_id: int
    image_ids: Keyring
    herd_unit_id: int
    box_tx: int
    box_ty: int
    box_bx: int
    box_by: int
    uuid: UUID
    type: ActivityType = ActivityType.AUTO_CROPPER
    prediction_ids: Optional[Keyring] = None
    reviewed_area_ids: Optional[Keyring] = None


# ---------------------------------------------------------------------------------------------------------------------------


class BulkCreateAnnotationReq(BaseModel):
    reviewed_area_id: UUID
    requests: List[CreateAnnotationReq]


# ---------------------------------------------------------------------------------------------------------------------------


class UpdateAnnotationReq(BaseModel):
    image_id: Optional[Keyring] = None
    label_id: Optional[Keyring] = None
    type: Optional[ActivityType] = None
    box_tx: Optional[int] = None
    box_ty: Optional[int] = None
    box_bx: Optional[int] = None
    box_by: Optional[int] = None


class BulkUpdateAnnotationsReq(BulkRequestModel):
    reviewed_area_id: UUID
    requests: List[UpdateAnnotationReq]


# ---------------------------------------------------------------------------------------------------------------------------


class DeleteAnnotationReq(BaseModel):
    annotation_id: UUID


# ---------------------------------------------------------------------------------------------------------------------------


class BulkDeleteAnnotationsReq(BulkRequestModel):
    requests: List[DeleteAnnotationReq]


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class Annotation(DBbase):
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

    __schema__: str = "core"
    __tablename__: str = "annotations"
    __pk_name__: str = "annotation_id"

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def __post_init__(self):
        self.dimensions = Box((self.box_tx, self.box_ty), (self.box_bx, self.box_by))

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class Response(BaseModel):
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
    ) -> Optional[tuple[Self, list[RelationshipUpdate]]]:

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

        spice_updates = [
            create_spice_update(
                "annotation", annotation.uuid, "image", req.image_ids.uuid, "parent"
            )
        ]

        return annotation, spice_updates

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self) -> dict[str, Any]:
        return Annotation.Response.model_validate(self).model_dump(mode="json")
