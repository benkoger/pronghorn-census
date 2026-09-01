# Class definition for Annotation objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Self
from uuid import UUID

from authzed.api.v1 import RelationshipUpdate
from psycopg import Cursor
from pydantic import BaseModel, field_validator, ConfigDict

from ..base import Box, BulkRequestModel, DBbase

# ---------------------------------------------------------------------------------------------------------------------------


class CreateAnnotationReq(BaseModel):
    label_id: int
    image_id: int
    herd_unit_id: int
    box_tx: int
    box_ty: int
    box_bx: int
    box_by: int
    uuid: UUID
    prediction_id: Optional[UUID] = None
    reviewed_area_id: Optional[UUID] = None


# ---------------------------------------------------------------------------------------------------------------------------


class BulkCreateAnnotationReq(BaseModel):
    reviewed_area_id: UUID
    requests: List[CreateAnnotationReq]


# ---------------------------------------------------------------------------------------------------------------------------


class UpdateAnnotationReq(BaseModel):
    annotation_id: UUID
    image_id: Optional[int] = None
    label_id: Optional[int] = None
    box_tx: Optional[int] = None
    box_ty: Optional[int] = None
    box_bx: Optional[int] = None
    box_by: Optional[int] = None
    pred_id: Optional[UUID] = None
    reviewed_area_id: Optional[UUID] = None


# ---------------------------------------------------------------------------------------------------------------------------


class DeleteAnnotationReq(BaseModel):
    annotation_id: UUID


# ---------------------------------------------------------------------------------------------------------------------------


class BulkUpdateAnnotationsReq(BulkRequestModel):
    reviewed_area_id: UUID
    requests: List[UpdateAnnotationReq]


# ---------------------------------------------------------------------------------------------------------------------------


class BulkDeleteAnnotationsReq(BulkRequestModel):
    requests: List[DeleteAnnotationReq]

# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class Annotation(DBbase):
    label_id: int
    image_id: int
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
        herd_unit_id: int
        dimensions: Dict[str, Dict[str, int]]
        created: datetime
        modified: datetime
        uuid: UUID

        @field_validator("dimensions", mode="before")
        @classmethod
        def transform_box(cls, value: Any) -> Dict[str, Dict[str, int]]:
            if isinstance(value, Box):
                return value.serialize()
            return value

     # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def _create(
        cls, cursor: Cursor[Self], req: CreateAnnotationReq
    ) -> Optional[tuple[Self, list[RelationshipUpdate]]]: ...

     # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self) -> Dict[str, Any]:
        return Annotation.Response.model_validate(self).model_dump(mode="json")



