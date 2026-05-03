# Class definition for Annotation objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

from ..base import Box, DBbase

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

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def __post_init__(self):
        self.dimensions = Box((self.box_tx, self.box_ty), (self.box_bx, self.box_by))

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def to_dict(self) -> dict:
        return {
            "annotation_id": self.annotation_id,
            "label_id": self.label_id,
            "image_id": self.image_id,
            "herd_unit_id": self.herd_unit_id,
            "dimensions": self.dimensions.to_dict(),
            "created": self.fmt_date(self.created),
            "modified": self.fmt_date(self.modified),
            "uuid": str(self.uuid),
        }


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


class BulkCreateAnnotationReq(BaseModel):
    reviewed_area_id: UUID
    requests: List[CreateAnnotationReq]


class UpdateAnnotationReq(BaseModel):
    image_id: Optional[int] = None
    label_id: Optional[int] = None
    box_tx: Optional[int] = None
    box_ty: Optional[int] = None
    box_bx: Optional[int] = None
    box_by: Optional[int] = None
    pred_id: Optional[UUID] = None
    reviewed_area_id: Optional[UUID] = None


class BulkUpdateAnnotationsReq(BaseModel):
    reviewed_area_id: UUID
    ids: List[UUID]
    requests: List[UpdateAnnotationReq]


class BulkDeleteAnnotationsReq(BaseModel):
    ids: List[UUID]
