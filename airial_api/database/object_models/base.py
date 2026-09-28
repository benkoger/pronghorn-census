from abc import ABC, abstractmethod
from msgpack import packb
from datetime import datetime
from typing import Any, ClassVar, Type, TypeVar, NamedTuple, Optional
from pydantic import BaseModel, field_validator
from psycopg import Cursor
import numpy as np
from uuid import UUID
import psycopg.sql as sql
from authzed.api.v1 import (
    RelationshipUpdate,
    Relationship,
    ObjectReference,
    SubjectReference,
)

# ---------------------------------------------------------------------------------------------------------------------------

T = TypeVar("T", bound="DBbase")

PrimaryKey = int | UUID

# ---------------------------------------------------------------------------------------------------------------------------


def create_spice_update(
    object_type: str,
    object_id: UUID,
    subject_type: str,
    subject_id: UUID,
    relation: str,
) -> RelationshipUpdate:
    """ """
    return RelationshipUpdate(
        operation=RelationshipUpdate.Operation.OPERATION_CREATE,
        relationship=Relationship(
            resource=ObjectReference(object_type=object_type, object_id=str(object_id)),
            relation=relation,
            subject=SubjectReference(
                object=ObjectReference(
                    object_type=subject_type,
                    object_id=str(subject_id),
                )
            ),
        ),
    )


# ---------------------------------------------------------------------------------------------------------------------------


class Keyring(NamedTuple):
    pkey: int
    uuid: UUID


# ---------------------------------------------------------------------------------------------------------------------------
# TODO: Rework these request containers to be less weird


class BulkRequest(BaseModel):
    object_ids: list[PrimaryKey]

    @field_validator("object_ids", mode="before")
    @classmethod
    def ensure_list(cls, value):
        if isinstance(value, list):
            return value
        if value is None or value == "":
            return []
        return [value]


class BulkRequestModel(BaseModel):
    requests: list[Any]


# ---------------------------------------------------------------------------------------------------------------------------


class DBbase(ABC):
    __table__: ClassVar[sql.Identifier]
    __pk__: ClassVar[sql.Identifier]
    __parent_table__: ClassVar[Optional[sql.Identifier]] = None
    __parent_fk__: ClassVar[Optional[sql.Identifier]] = None

    Response: ClassVar[Type[BaseModel]]

    @abstractmethod
    def serialize(self) -> dict: ...

    @classmethod
    @abstractmethod
    def _create(
        cls, cursor: Cursor[T], *args: Any, **kwargs: Any
    ) -> Optional[tuple[T, list[RelationshipUpdate]]]: ...

    def to_cache(self):
        return packb(self.serialize())

    def fmt_date(self, dt: datetime | None):
        """Convert datetime object to a string for serialization"""
        return dt.strftime("%Y-%m-%d %H:%M:%S%z") if isinstance(dt, datetime) else None


# ---------------------------------------------------------------------------------------------------------------------------


class Relationbase(ABC):
    __table__: ClassVar[sql.Identifier]
    __key__: tuple[str, ...]
    """Pure interface for junction models"""

    def to_lookup_dict(self) -> dict[str, Any]:
        """Convert key attributes into query params for base.where()."""
        return {key: getattr(self, key) for key in self.__key__}


# ---------------------------------------------------------------------------------------------------------------------------


class Box:
    """A Box contains dimensional data for crops and predictions"""

    def __init__(self, top_left: tuple[int, int], bottom_right: tuple[int, int]):
        self.top_left = top_left
        self.bottom_right = bottom_right

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def getCenter(self) -> tuple:
        x = np.mean([self.top_left[0], self.bottom_right[0]])
        y = np.mean([self.top_left[1], self.bottom_right[1]])

        return (abs(x), abs(y))

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def getPoints(self) -> list[int]:
        return [
            self.top_left[0],
            self.top_left[1],
            self.bottom_right[0],
            self.bottom_right[1],
        ]

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def calcIou(self, box_2) -> float:
        # Slightly modified from https://machinelearningspace.com/intersection-over-union-iou-a-comprehensive-guide/
        # Extract bounding boxes coordinates
        x0_A, y0_A, x1_A, y1_A = self.getPoints()
        x0_B, y0_B, x1_B, y1_B = box_2.getPoints()

        # Get the coordinates of the intersection rectangle
        x0_I = max(x0_A, x0_B)
        y0_I = max(y0_A, y0_B)
        x1_I = min(x1_A, x1_B)
        y1_I = min(y1_A, y1_B)
        # Calculate width and height of the intersection area.
        width_I = x1_I - x0_I
        height_I = y1_I - y0_I

        # Handle the negative value width or height of the intersection area
        width_I = 0 if width_I < 0 else width_I
        height_I = 0 if height_I < 0 else height_I
        # Calculate the intersection area:
        intersection = width_I * height_I
        # Calculate the union area:
        width_A, height_A = x1_A - x0_A, y1_A - y0_A
        width_B, height_B = x1_B - x0_B, y1_B - y0_B
        union = (width_A * height_A) + (width_B * height_B) - intersection
        # Calculate the IoU:
        return intersection / union

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self) -> dict[str, dict[str, int]]:
        return {
            "top_left": {"x": self.top_left[0], "y": self.top_left[1]},
            "bottom_right": {"x": self.bottom_right[0], "y": self.bottom_right[1]},
        }


# ---------------------------------------------------------------------------------------------------------------------------


class JunctionRelation(NamedTuple):
    table_name: str
