# Multi table bindings for the projectmanagement schema
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------

from dataclasses import dataclass
from ..base import Relationbase

# ---------------------------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class AnnotationsReviewedArea(Relationbase):
    annotation_id: int
    reviewed_area_id: int

    __tablename__: str = "annotations_reviewed_area"
    __schema__: str = "core"
    __key__: tuple = ("annotation_idi", "reviewed_area_id")
