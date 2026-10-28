# Class definition for Image objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------
"""Image and reviewed area database models and schemas."""

import io
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar, Self
from uuid import UUID

import cv2
import numpy as np
import PIL.Image as PillowImage
import psycopg.sql as sql
from authzed.api.v1 import RelationshipUpdate
from psycopg import Cursor
from psycopg.rows import class_row
from pydantic import BaseModel, ConfigDict, field_validator

from ..base import Box, DBbase, Keyring, create_spice_update
from .activity import ActivityType

# ---------------------------------------------------------------------------------------------------------------------------


class ImageMixin:
    """Mixin class providing image manipulation and encoding helpers."""

    image: np.ndarray | None = None

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def set_image(self, imageData: np.ndarray):
        """Set internal image array from raw bytes or ndarray."""
        if isinstance(imageData, bytes):
            try:
                pilImage = PillowImage.open(io.BytesIO(imageData))
                pilImage = pilImage.convert("RGB")
                self.image = cv2.cvtColor(np.array(pilImage), cv2.COLOR_RGB2BGR)
            except Exception as e:
                print(f"Error converting bytes to image: {e}")
                self.image = None
        elif isinstance(imageData, np.ndarray):
            self.image = imageData

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def get_image(self) -> np.ndarray | None:
        """Get internal image array."""
        if self.image is not None:
            return self.image

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def delete_image(self):
        """Delete internal image array."""
        del self.image

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serve(self, img_format: str):
        """Encode internal image into the specified format and return bytes."""
        if self.image is not None:
            _, img_encoded = cv2.imencode(
                img_format,
                self.get_image(),  # pyright: ignore
                [cv2.IMWRITE_JPEG_QUALITY, 100],  # pyright: ignore
            )
        else:
            raise Exception("no image data")
        return img_encoded.tobytes()

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


# ---------------------------------------------------------------------------------------------------------------------------


class CreateImageReq(BaseModel):
    """Request schema for creating an image."""

    name: str
    herd_unit_ids: Keyring
    survey_ids: Keyring
    img_key: str
    image_length_px: int
    image_width_px: int


# ---------------------------------------------------------------------------------------------------------------------------


class CreatePresignedPutReq(BaseModel):
    """Request schema for creating a presigned PUT URL."""

    image_id: int | UUID
    upload_id: str
    part_number: int
    chunk_size: int
    chunk_md5: str


# ---------------------------------------------------------------------------------------------------------------------------


class PresignedImageGetReq(BaseModel):
    """Request schema for getting a presigned image GET URL."""

    image_id: UUID
    expires_in: int


# ---------------------------------------------------------------------------------------------------------------------------


class CreateImageMultiPartUploadReq(BaseModel):
    """Request schema for initiating multipart upload."""

    image_key: str


# ---------------------------------------------------------------------------------------------------------------------------


class AbortMulitPartUploadReq(BaseModel):
    """Request schema for aborting multipart upload."""

    image_key: str
    upload_id: str


# ---------------------------------------------------------------------------------------------------------------------------


class CompleteMultiPartUploadReq(BaseModel):
    """Request schema for completing multipart upload."""

    image_key: str
    upload_id: str
    parts: list[Any]


# ---------------------------------------------------------------------------------------------------------------------------


class UpdateImageReq(BaseModel):
    """Request schema for updating an image."""

    name: str | None = None
    img_key: str | None = None
    image_length_px: int | None = None
    image_width_px: int | None = None
    opened_by_user_id: int | None = None


# ---------------------------------------------------------------------------------------------------------------------------


class CreatePredictionCropReq(BaseModel):
    """Request schema for creating prediction crops."""

    image_id: UUID
    prediction_id: list[UUID]

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @field_validator("prediction_id")
    @classmethod
    def ensure_list(cls, value):
        """Ensure value is a list of UUIDs."""
        if isinstance(value, list):
            return value
        if value is None or value == "":
            return []
        return [value]


# ---------------------------------------------------------------------------------------------------------------------------


class RAQuery(BaseModel):
    """Query parameters for filtering reviewed areas."""

    herd_unit_id: list[UUID] | None = None
    survey_id: list[UUID] | None = None
    include_reviewed: bool | None = False
    include_opened: bool | None = False
    num: int | None = None
    page: int | None = None
    per_page: int | None = None
    search: str | None = None
    exclude_ids: list[UUID] | None = None

    @field_validator("herd_unit_id", "survey_id", "exclude_ids", mode="before")
    @classmethod
    def ensure_list(cls, value):
        """Ensure value is converted to a list."""
        if isinstance(value, list):
            return value
        if value is None or value == "":
            return []
        return [value]


# ---------------------------------------------------------------------------------------------------------------------------


class CreateReviewedAreaReq(BaseModel, ImageMixin):
    """Request schema for creating a reviewed area."""

    image_ids: Keyring
    name: str
    type: ActivityType = ActivityType.AUTO_CROPPER
    area_tx: int
    area_ty: int
    area_bx: int
    area_by: int
    reviewed_area_length_px: int
    reviewed_area_width_px: int
    reviewed_by_user_id: int = 0
    ra_key: str | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


# ---------------------------------------------------------------------------------------------------------------------------


class UpdateReviewedAreaReq(BaseModel):
    """Request schema for updating a reviewed area."""

    image_id: UUID | None = None
    type: ActivityType | None = None
    name: str | None = None
    area_tx: int | None = None
    area_ty: int | None = None
    area_bx: int | None = None
    area_by: int | None = None
    reviewed_area_length_px: int | None = None
    reviewed_area_width_px: int | None = None
    ra_key: str | None = None
    reviewed_by_user_id: int | None = None


# ---------------------------------------------------------------------------------------------------------------------------


class CrateReviewedAreaPresignedGetReq(BaseModel):
    """Request schema for getting a presigned GET URL for a reviewed area."""

    reviewed_area_id: UUID


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class Image(DBbase, ImageMixin):
    """Database representation of an image."""

    image_id: int
    herd_unit_id: int
    survey_id: int
    name: str
    img_key: str
    in_training: bool
    crops_generated: int
    opened_by_user_id: int
    created: datetime
    modified: datetime
    image_length_px: int
    image_width_px: int
    uuid: UUID

    image: np.ndarray | None = field(default=None, init=False)

    __table__: ClassVar[sql.Identifier] = sql.Identifier("core", "images")
    __pk__: ClassVar[sql.Identifier] = sql.Identifier("image_id")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class Response(BaseModel):
        """Response schema for an image."""

        model_config = ConfigDict(from_attributes=True)

        image_id: int
        herd_unit_id: int
        survey_id: int
        name: str
        img_key: str
        in_training: bool
        crops_generated: int
        created: datetime
        modified: datetime
        image_length_px: int
        image_width_px: int
        uuid: UUID

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def _create(cls, cursor: Cursor[Self], req: CreateImageReq) -> tuple[Self, list[RelationshipUpdate]] | None:
        cursor.row_factory = class_row(cls)
        query = sql.SQL("""
            INSERT INTO core.images (
                herd_unit_id, survey_id, name, img_key, image_length_px,
                image_width_px
            )
            VALUES (
                %(herd_unit_id)s, %(survey_id)s, %(name)s,
                %(img_key)s, %(image_length_px)s,
                %(image_width_px)s
            )
            RETURNING *;
        """)

        cursor.execute(
            query,
            {
                **req.model_dump(),
                "herd_unit_id": req.herd_unit_ids.pkey,
                "survey_id": req.survey_ids.pkey,
            },
        )

        if not (image := cursor.fetchone()):
            return None

        spice_updates = [
            create_spice_update("image", image.uuid, "survey", req.survey_ids.uuid, "parent"),
            create_spice_update("image", image.uuid, "herd_unit", req.herd_unit_ids.uuid, "parent"),
        ]

        return image, spice_updates

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self) -> dict:
        """Serialize image model to a dictionary."""
        return Image.Response.model_validate(self).model_dump(mode="json")


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class ReviewedArea(DBbase, ImageMixin):
    """Database representation of a reviewed area."""

    reviewed_area_id: int
    image_id: int
    type: ActivityType
    name: str
    created: datetime
    modified: datetime
    area_tx: int
    area_ty: int
    area_bx: int
    area_by: int
    reviewed_area_length_px: int
    reviewed_area_width_px: int
    reviewed_by_user_id: int
    uuid: UUID

    ra_key: str | None = None
    dimensions: "Box" = field(init=False)

    __table__: ClassVar[sql.Identifier] = sql.Identifier("core", "reviewed_area")
    __pk__: ClassVar[sql.Identifier] = sql.Identifier("reviewed_area_id")
    __parent_table__: ClassVar[sql.Identifier] = sql.Identifier("core", "images")
    __parent_fk__: ClassVar[sql.Identifier] = sql.Identifier("image_id")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def __post_init__(self):
        """Initialize dimensions box."""
        self.dimensions = Box((self.area_tx, self.area_ty), (self.area_bx, self.area_by))

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class Response(BaseModel):
        """Response schema for a reviewed area."""

        model_config = ConfigDict(from_attributes=True)

        reviewed_area_id: int
        image_id: int
        type: ActivityType
        name: str
        dimensions: dict[str, dict[str, int]]
        created: datetime
        modified: datetime
        reviewed_area_length_px: int
        reviewed_area_width_px: int
        ra_key: str
        uuid: UUID

        @field_validator("dimensions", mode="before")
        @classmethod
        def transform(cls, value):
            """Transform box dimensions into serialized dictionary."""
            if isinstance(value, Box):
                return value.serialize()
            return value

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def _create(cls, cursor: Cursor[Self], req: CreateReviewedAreaReq) -> tuple[Self, list[RelationshipUpdate]] | None:
        cursor.row_factory = class_row(cls)
        query = sql.SQL("""
            INSERT INTO core.reviewed_area (
                image_id, type, name, area_tx, area_ty, area_bx, area_by, reviewed_area_length_px,
                reviewed_area_width_px, reviewed_by_user_id, ra_key
            )
            VALUES (
                %(image_id)s, %(type)s, %(name)s, %(area_tx)s, %(area_ty)s, %(area_bx)s, %(area_by)s,
                %(reviewed_area_length_px)s, %(reviewed_area_width_px)s, %(reviewed_by_user_id)s,
                %(ra_key)s
            )
            RETURNING *;
        """)

        cursor.execute(query, {**req.model_dump(), "image_id": req.image_ids.pkey})

        if not (reviewed_area := cursor.fetchone()):
            return None

        spice_updates = [
            create_spice_update(
                "reviewed_area",
                reviewed_area.uuid,
                "image",
                req.image_ids.uuid,
                "parent",
            )
        ]

        return reviewed_area, spice_updates

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self) -> dict:
        """Serialize reviewed area model to a dictionary."""
        return ReviewedArea.Response.model_validate(self).model_dump(mode="json")


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class PredictionCrop(DBbase, ImageMixin):
    """Representation of a cropped prediction chip."""

    image_id: int
    name: str
    pred_id: int
    score: float
    label: int
    uuid: UUID
    dimensions: "Box"
    boundingBox: "Box"
    url: str | None = None
    approved: bool = field(default=False, init=False)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class Response(BaseModel):
        """Response schema for a prediction crop."""

        model_config = ConfigDict(from_attributes=True)

        image_id: int
        score: float
        pred_id: int
        name: str
        approved: bool
        label: int
        dimensions: dict[str, dict[str, int]]
        boundingBox: dict[str, dict[str, int]]
        uuid: UUID

        @field_validator("dimensions", "boundingBox", mode="before")
        @classmethod
        def transform(cls, value: Any) -> Any:
            """Transform box objects into serialized dictionaries."""
            if isinstance(value, Box):
                return value.serialize()
            return value

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def _create(cls, cursor: Cursor[Self], req: CreatePredictionCropReq) -> tuple[Self, list[RelationshipUpdate]] | None: ...

    ### This method will never be implemented, just proves we need smarter
    ### abstraction in the future

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self) -> dict[str, Any]:
        """Serialize prediction crop model to a dictionary."""
        return PredictionCrop.Response.model_validate(self).model_dump(mode="json")


# ---------------------------------------------------------------------------------------------------------------------------
