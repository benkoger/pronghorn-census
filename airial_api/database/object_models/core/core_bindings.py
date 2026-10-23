# Multi table bindings for the projectmanagement schema
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------

from dataclasses import dataclass
from typing import ClassVar

import psycopg.sql as sql

from ..base import Relationbase

# ---------------------------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class AnnotationsReviewedArea(Relationbase):
    annotation_id: int
    reviewed_area_id: int

    __table__: ClassVar[sql.Identifier] = sql.Identifier("core", "annotations_reviewed_area")
    __key__: tuple = ("annotation_idi", "reviewed_area_id")
