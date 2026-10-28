# Multi table bindings for the projectmanagement schema
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------

"""Multi-table relation bindings for the core schema."""

from dataclasses import dataclass
from typing import ClassVar

import psycopg.sql as sql

from ..base import Relationbase

# ---------------------------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class AnnotationsReviewedArea(Relationbase):
    """Junction relation linking annotations to reviewed areas."""

    annotation_id: int
    reviewed_area_id: int

    __table__: ClassVar[sql.Identifier] = sql.Identifier("core", "annotations_reviewed_area")
    __key__: tuple = ("annotation_idi", "reviewed_area_id")
